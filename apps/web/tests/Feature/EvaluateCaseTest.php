<?php

namespace Tests\Feature;

use App\Documents\ExtractClient;
use App\Jobs\EvaluateCase;
use App\Models\AuditEvent;
use App\Models\CaseEvaluation;
use App\Models\CaseFile;
use App\Models\Document;
use App\Models\Finding;
use App\Models\Membership;
use App\Services\AuditLog;
use App\Tenancy\TenantContext;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class EvaluateCaseTest extends TestCase
{
    private Membership $owner;

    private CaseFile $case;

    private Document $invoice;

    private Document $contract;

    protected function setUp(): void
    {
        parent::setUp();
        Queue::fake();
        config(['services.extract.url' => 'http://extract:8000', 'services.extract.token' => 'secret-token']);
        $this->owner = $this->member();
        $this->case = $this->caseFor($this->owner);
        [$this->contract, $this->invoice] = app(TenantContext::class)->run($this->owner, function () {
            $make = fn (string $type, string $building) => tap(Document::factory()->create([
                'case_file_id' => $this->case->id, 'uploaded_by' => $this->owner->user_id, 'status' => 'processed',
            ])->forceFill(['doc_type' => $type, 'doc_type_source' => 'classifier']), function (Document $d) use ($building) {
                $d->save();
                $d->pages()->create([
                    'page_no' => 1, 'width_pt' => 595, 'height_pt' => 842, 'image_key' => $d->storagePrefix().'pages/001.png',
                    'image_width_px' => 1240, 'image_height_px' => 1754, 'text_source' => 'text_layer', 'word_count' => 100,
                ]);
                $d->fields()->create([
                    'name' => 'address_building_no', 'value' => $building, 'raw_text' => $building, 'page_no' => 1,
                    'bbox' => ['x0' => 0.1, 'y0' => 0.2, 'x1' => 0.15, 'y1' => 0.21], 'method' => 'address',
                    'confidence' => 0.95, 'status' => 'ok',
                ]);
            });

            return [$make('umowa', '25'), $make('faktura', '52')];
        });
        app(TenantContext::class)->clear();
    }

    /** @return array<string, mixed> */
    private function finding(?string $fingerprint = null, string $value = '52'): array
    {
        return [
            'rule_id' => 'ADR-01', 'rule_version' => 1, 'family' => 'address', 'outcome' => 'discrepancy',
            'severity' => 'critical', 'title_pl' => 'Adres budynku zgodny we wszystkich dokumentach',
            'reason_pl' => "Numer budynku „{$value}” w dokumencie faktura VAT różni się od wartości „25”.",
            'subject_doc_ids' => [$this->invoice->id], 'context_doc_ids' => [$this->contract->id],
            'fields' => ['address_building_no'],
            'evidence' => [
                ['doc_id' => $this->invoice->id, 'field' => 'address_building_no', 'value' => $value, 'text' => $value],
                ['doc_id' => $this->contract->id, 'field' => 'address_building_no', 'value' => '25', 'text' => '25'],
            ],
            'fingerprint' => $fingerprint ?? str_repeat('a', 64),
            'evidence_hash' => hash('sha256', $value),
            'source_url' => 'https://czystepowietrze.gov.pl/',
            'status' => 'do_sprawdzenia',
        ];
    }

    /** @param  list<array<string, mixed>>  $findings */
    private function response(array $findings): array
    {
        return [
            'case_id' => $this->case->id, 'reference_date' => '2026-03-02', 'reference_source' => 'application_date',
            'ruleset' => [['id' => 'ADR-01', 'version' => 1], ['id' => 'CMP-01', 'version' => 1]],
            'findings' => $findings,
        ];
    }

    private function evaluate(bool $force = false, ?string $organizationId = null): void
    {
        (new EvaluateCase($organizationId ?? $this->owner->organization_id, $this->case->id, $force))
            ->handle(app(TenantContext::class), app(ExtractClient::class), app(AuditLog::class));
    }

    /** @return Collection<int, Finding> */
    private function findings()
    {
        return app(TenantContext::class)->run($this->owner, fn () => Finding::query()->orderBy('created_at')->get());
    }

    public function test_sends_the_stored_fields_and_stores_findings(): void
    {
        Http::fake(['extract:8000/v1/cases/evaluate' => Http::response($this->response([$this->finding()]))]);

        $this->evaluate();

        Http::assertSent(function ($request) {
            $docs = collect($request['documents'])->keyBy('doc_id');

            return $request->hasHeader('Authorization', 'Bearer secret-token')
                && $request['case_id'] === $this->case->id
                && $docs[$this->invoice->id]['doc_type'] === 'faktura'
                && $docs[$this->invoice->id]['text_source'] === 'text_layer'
                && $docs[$this->invoice->id]['fields'][0] === [
                    'name' => 'address_building_no', 'value' => '52', 'raw_text' => '52', 'status' => 'ok', 'confidence' => 0.95,
                ];
        });
        $finding = $this->findings()->sole();
        $this->assertSame('do_sprawdzenia', $finding->review_status);
        $this->assertTrue($finding->is_current);
        $this->assertSame([$this->invoice->id], $finding->subject_doc_ids);
        $this->assertSame('critical', $finding->severity);
        $evaluation = app(TenantContext::class)->run($this->owner, fn () => CaseEvaluation::query()->sole());
        $this->assertSame('2026-03-02', $evaluation->reference_date->toDateString());
        $event = app(TenantContext::class)->run($this->owner, fn () => AuditEvent::query()->where('event_type', 'case.evaluated')->sole());
        $this->assertSame(1, $event->payload['new']);
        $this->assertSame(['ADR-01@1', 'CMP-01@1'], $event->payload['ruleset']);
    }

    public function test_re_evaluation_keeps_one_row_per_fingerprint_and_tracks_whether_it_is_current(): void
    {
        Http::fake(['extract:8000/*' => Http::sequence()
            ->push($this->response([$this->finding()]))
            ->push($this->response([$this->finding(value: '53')]))
            ->push($this->response([]))
            ->push($this->response([$this->finding()]))]);

        $this->evaluate();
        $first = $this->findings()->sole();
        $this->evaluate(force: true);
        $updated = $this->findings()->sole();
        $this->assertSame($first->id, $updated->id);
        $this->assertNotSame($first->evidence_hash, $updated->evidence_hash);

        $this->evaluate(force: true);
        $this->assertFalse($this->findings()->sole()->is_current);

        $this->evaluate(force: true);
        $again = $this->findings()->sole();
        $this->assertSame($first->id, $again->id);
        $this->assertTrue($again->is_current);
    }

    public function test_unchanged_input_is_not_evaluated_twice_unless_forced(): void
    {
        Http::fake(['extract:8000/*' => Http::response($this->response([]))]);

        $this->evaluate();
        $this->evaluate();
        Http::assertSentCount(1);

        $this->evaluate(force: true);
        Http::assertSentCount(2);
    }

    public function test_cases_with_documents_still_processing_wait(): void
    {
        app(TenantContext::class)->run($this->owner, fn () => Document::factory()->create([
            'case_file_id' => $this->case->id, 'uploaded_by' => $this->owner->user_id, 'status' => 'processing',
        ]));
        app(TenantContext::class)->clear();
        Http::fake();

        $this->evaluate(force: true);

        Http::assertNothingSent();
    }

    /** @return array<string, array{0: callable}> */
    public static function invalidResponses(): array
    {
        return [
            'document of another case' => [fn ($f) => array_replace($f, ['subject_doc_ids' => ['00000000-0000-0000-0000-000000000000']])],
            'unknown field' => [fn ($f) => array_replace($f, ['fields' => ['iban']])],
            'evidence from elsewhere' => [fn ($f) => array_replace($f, ['evidence' => [['doc_id' => 'x', 'field' => 'address_building_no', 'value' => '1', 'text' => '1']]])],
            'bad fingerprint' => [fn ($f) => array_replace($f, ['fingerprint' => 'abc'])],
            'decided by the engine' => [fn ($f) => array_replace($f, ['status' => 'zgodne'])],
            'unknown severity' => [fn ($f) => array_replace($f, ['severity' => 'fatal'])],
            'script as source' => [fn ($f) => array_replace($f, ['source_url' => 'javascript:alert(1)'])],
        ];
    }

    #[DataProvider('invalidResponses')]
    public function test_responses_outside_the_contract_store_nothing(callable $change): void
    {
        Http::fake(['extract:8000/*' => Http::response($this->response([$change($this->finding())]))]);

        $this->evaluate();

        $this->assertCount(0, $this->findings());
        $events = app(TenantContext::class)->run($this->owner, fn () => AuditEvent::query()->pluck('event_type')->all());
        $this->assertContains('case.evaluation_failed', $events);
        $this->assertNotContains('case.evaluated', $events);
    }

    public function test_job_for_another_organization_sees_nothing(): void
    {
        $other = $this->member();
        Http::fake();

        $this->evaluate(organizationId: $other->organization_id);

        Http::assertNothingSent();
        $this->assertCount(0, $this->findings());
    }

    public function test_case_page_lists_current_findings_and_the_check_again_button(): void
    {
        Http::fake(['extract:8000/*' => Http::response($this->response([$this->finding()]))]);
        $this->evaluate();

        $this->actingAs($this->owner->user)->get("/cases/{$this->case->id}")
            ->assertOk()
            ->assertSee('Ustalenia')
            ->assertSee('krytyczne')
            ->assertSee('Adres budynku zgodny we wszystkich dokumentach')
            ->assertSee('do sprawdzenia')
            ->assertSee("/documents/{$this->invoice->id}#field-address_building_no", false)
            ->assertSee('Sprawdź ponownie');

        $this->actingAs($this->owner->user)->post("/cases/{$this->case->id}/evaluate")
            ->assertRedirect("/cases/{$this->case->id}");
        Queue::assertPushed(EvaluateCase::class, fn ($job) => $job->force && $job->caseFileId === $this->case->id);
    }

    public function test_findings_of_another_organization_are_invisible(): void
    {
        Http::fake(['extract:8000/*' => Http::response($this->response([$this->finding()]))]);
        $this->evaluate();
        $other = $this->member();

        $this->assertSame(0, app(TenantContext::class)->run($other, fn () => Finding::query()->count()));
        $this->actingAs($other->user)->post("/cases/{$this->case->id}/evaluate")->assertNotFound();
    }

    public function test_changed_values_send_a_decided_finding_back_for_a_second_look(): void
    {
        Http::fake(['extract:8000/*' => Http::sequence()
            ->push($this->response([$this->finding()]))
            ->push($this->response([$this->finding()]))
            ->push($this->response([$this->finding(value: '53')]))]);
        $this->evaluate();
        $finding = $this->findings()->sole();
        $this->actingAs($this->owner->user)->post("/cases/{$this->case->id}/findings/{$finding->id}/decisions", [
            'decision' => 'rozbieznosc', 'comment' => 'Numer 52 na fakturze jest błędny.',
        ])->assertSessionHasNoErrors();

        $this->evaluate(force: true);
        $this->assertSame('rozstrzygniete', $this->findings()->sole()->review_status);

        $this->evaluate(force: true);
        $again = $this->findings()->sole();
        $this->assertSame('do_ponownej_weryfikacji', $again->review_status);
        $this->assertSame('rozbieznosc', $again->decision);
        $event = app(TenantContext::class)->run($this->owner, fn () => AuditEvent::query()
            ->where('event_type', 'case.evaluated')->orderByDesc('id')->first());
        $this->assertSame(1, $event->payload['needs_second_look']);
    }

    public function test_first_evaluation_puts_the_case_in_review(): void
    {
        Http::fake(['extract:8000/*' => Http::response($this->response([]))]);

        $this->evaluate();

        $this->assertSame('in_review', app(TenantContext::class)->run($this->owner, fn () => $this->case->refresh()->status));
    }
}
