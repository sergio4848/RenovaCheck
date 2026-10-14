<?php

namespace Tests\Feature;

use App\Jobs\EvaluateCase;
use App\Models\AuditEvent;
use App\Models\CaseEvaluation;
use App\Models\CaseFile;
use App\Models\Document;
use App\Models\Finding;
use App\Models\FindingDecision;
use App\Models\Membership;
use App\Tenancy\TenantContext;
use Illuminate\Database\QueryException;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Illuminate\Testing\TestResponse;
use Tests\TestCase;

class FindingReviewTest extends TestCase
{
    private Membership $owner;

    private CaseFile $case;

    private Document $invoice;

    private Document $contract;

    protected function setUp(): void
    {
        parent::setUp();
        Queue::fake();
        Storage::fake('s3-public');
        $this->owner = $this->member();
        $this->case = $this->caseFor($this->owner);
        [$this->contract, $this->invoice] = $this->asTenant(fn () => [$this->document('umowa', '25'), $this->document('faktura', '52')]);
    }

    private function asTenant(callable $callback, ?Membership $membership = null): mixed
    {
        $result = app(TenantContext::class)->run($membership ?? $this->owner, $callback);
        app(TenantContext::class)->clear();

        return $result;
    }

    private function document(string $type, string $building): Document
    {
        $document = Document::factory()->create([
            'case_file_id' => $this->case->id, 'uploaded_by' => $this->owner->user_id, 'status' => 'processed',
        ]);
        $document->forceFill(['doc_type' => $type, 'doc_type_source' => 'classifier'])->save();
        $document->pages()->create([
            'page_no' => 1, 'width_pt' => 595, 'height_pt' => 842, 'image_key' => $document->storagePrefix().'pages/001.png',
            'image_width_px' => 1240, 'image_height_px' => 1754, 'text_source' => 'text_layer', 'word_count' => 100,
        ]);
        $document->fields()->create([
            'name' => 'address_building_no', 'value' => $building, 'raw_text' => $building, 'page_no' => 1,
            'bbox' => ['x0' => 0.1, 'y0' => 0.2, 'x1' => 0.15, 'y1' => 0.21], 'method' => 'address', 'confidence' => 0.95, 'status' => 'ok',
        ]);

        return $document;
    }

    private function finding(string $severity = 'critical', array $overrides = []): Finding
    {
        return $this->asTenant(fn () => $this->case->findings()->create([
            'fingerprint' => hash('sha256', $severity.json_encode($overrides)),
            'rule_id' => 'ADR-01', 'rule_version' => 1, 'family' => 'address', 'outcome' => 'discrepancy',
            'severity' => $severity, 'title_pl' => 'Adres budynku zgodny we wszystkich dokumentach',
            'reason_pl' => 'Numer budynku „52” w dokumencie faktura VAT różni się od wartości „25”.',
            'subject_doc_ids' => [$this->invoice->id], 'context_doc_ids' => [$this->contract->id],
            'fields' => ['address_building_no'],
            'evidence' => [
                ['doc_id' => $this->invoice->id, 'field' => 'address_building_no', 'value' => '52', 'text' => '52'],
                ['doc_id' => $this->contract->id, 'field' => 'address_building_no', 'value' => '25', 'text' => '25'],
            ],
            'evidence_hash' => str_repeat('e', 64), 'rule_source_url' => 'https://czystepowietrze.gov.pl/',
            'first_seen_at' => now(), 'last_evaluated_at' => now(),
        ] + $overrides));
    }

    private function decide(Finding $finding, array $data, ?Membership $as = null): TestResponse
    {
        return $this->actingAs(($as ?? $this->owner)->user)
            ->post("/cases/{$this->case->id}/findings/{$finding->id}/decisions", $data + ['evidence_hash' => $finding->evidence_hash]);
    }

    /** A successful evaluation of the case's current documents (closing requires one). */
    private function markEvaluated(): void
    {
        $this->asTenant(fn () => CaseEvaluation::query()->create([
            'case_file_id' => $this->case->id, 'status' => 'ok', 'input_hash' => EvaluateCase::currentInputHash($this->case),
            'reference_date' => '2026-03-02', 'reference_source' => 'application_date', 'ruleset' => [], 'findings_count' => 2,
        ]));
    }

    public function test_review_screen_shows_evidence_boxes_on_signed_page_images(): void
    {
        $finding = $this->finding();

        $this->actingAs($this->owner->user)->get("/cases/{$this->case->id}/findings/{$finding->id}")
            ->assertOk()
            ->assertSee('Numer budynku „52”', false)
            ->assertSee('data-box="0.10000,0.20000,0.15000,0.21000"', false)
            ->assertSee("/cases/{$this->case->id}/documents/{$this->invoice->id}/pages/1", false)
            ->assertSee("/cases/{$this->case->id}/documents/{$this->contract->id}/pages/1", false)
            ->assertSee('field-box is-context', false)
            ->assertSee('Źródło reguły')
            ->assertSee('Wymagany przy ustaleniach krytycznych')
            ->assertSee('Zapisz decyzję');
    }

    public function test_decision_is_recorded_append_only_with_summary_and_audit(): void
    {
        $finding = $this->finding();

        $this->decide($finding, ['decision' => 'rozbieznosc', 'comment' => 'Numer 52 na fakturze — błąd wystawcy.'])->assertRedirect();

        $this->asTenant(function () use ($finding) {
            $finding->refresh();
            $this->assertSame('rozstrzygniete', $finding->review_status);
            $this->assertSame('rozbieznosc', $finding->decision);
            $this->assertSame($this->owner->user_id, $finding->decided_by);
            $row = FindingDecision::query()->sole();
            $this->assertSame('Numer 52 na fakturze — błąd wystawcy.', $row->comment);
            $this->assertSame($finding->reason_pl, $row->reason_pl);
            $this->assertSame('52', $row->evidence[0]['value']);
            $this->assertSame(str_repeat('e', 64), $row->evidence_hash);
            $event = AuditEvent::query()->where('event_type', 'finding.decided')->sole();
            $this->assertSame('rozbieznosc', $event->payload['decision']);
            $this->assertArrayNotHasKey('comment', $event->payload);
        });
    }

    public function test_critical_findings_need_a_comment(): void
    {
        $finding = $this->finding();

        $this->decide($finding, ['decision' => 'zgodne', 'comment' => '  '])->assertSessionHasErrors('comment');

        $this->assertSame(0, $this->asTenant(fn () => FindingDecision::query()->count()));
    }

    public function test_other_findings_can_be_decided_without_a_comment(): void
    {
        $finding = $this->finding('info');

        $this->decide($finding, ['decision' => 'zgodne'])->assertSessionHasNoErrors();

        $this->assertSame('zgodne', $this->asTenant(fn () => $finding->refresh()->decision));
    }

    public function test_unknown_decision_is_rejected(): void
    {
        $this->decide($this->finding(), ['decision' => 'approved', 'comment' => 'x'])->assertSessionHasErrors('decision');
    }

    public function test_a_new_decision_keeps_the_history(): void
    {
        $finding = $this->finding();
        $this->decide($finding, ['decision' => 'zgodne', 'comment' => 'pierwsza']);
        $this->decide($finding, ['decision' => 'rozbieznosc', 'comment' => 'druga']);

        $this->asTenant(function () use ($finding) {
            $this->assertSame(['druga', 'pierwsza'], $finding->decisions()->pluck('comment')->all());
            $this->assertSame('rozbieznosc', $finding->refresh()->decision);
        });
    }

    public function test_findings_no_longer_reported_or_in_closed_cases_cannot_be_decided(): void
    {
        $stale = $this->finding('info', ['is_current' => false]);
        $this->decide($stale, ['decision' => 'zgodne'])->assertSessionHasErrors('decision');

        $current = $this->finding('warning');
        $this->asTenant(fn () => $this->case->forceFill(['status' => 'closed'])->save());
        $this->decide($current, ['decision' => 'zgodne'])->assertSessionHasErrors('decision');
    }

    public function test_decisions_cannot_be_changed_or_deleted_even_by_the_schema_owner(): void
    {
        $finding = $this->finding();
        $this->decide($finding, ['decision' => 'zgodne', 'comment' => 'ok']);

        foreach (['app' => fn () => null, 'owner' => fn () => DB::statement('RESET ROLE')] as $who => $become) {
            $this->asTenant(function () use ($become, $who) {
                $become();
                foreach (["UPDATE finding_decisions SET decision = 'rozbieznosc'", 'DELETE FROM finding_decisions'] as $sql) {
                    DB::beginTransaction();
                    try {
                        DB::statement($sql);
                        $this->fail("{$who} could run: {$sql}");
                    } catch (QueryException $e) {
                        // The app role has no UPDATE/DELETE grant; the owner is stopped by the trigger.
                        $this->assertMatchesRegularExpression('/append-only|permission denied/', $e->getMessage());
                    } finally {
                        DB::rollBack();
                    }
                }
            });
            $this->actAsAppRole();
        }
        $this->assertSame('zgodne', $this->asTenant(fn () => FindingDecision::query()->sole()->decision));
    }

    public function test_findings_of_another_organization_are_not_found(): void
    {
        $finding = $this->finding();
        $other = $this->member();

        $this->actingAs($other->user)->get("/cases/{$this->case->id}/findings/{$finding->id}")->assertNotFound();
        $this->decide($finding, ['decision' => 'zgodne', 'comment' => 'x'], $other)->assertNotFound();
        $this->assertSame(0, $this->asTenant(fn () => Finding::query()->count(), $other));
    }

    public function test_a_finding_resolves_only_through_its_own_case(): void
    {
        $finding = $this->finding();
        $otherCase = $this->caseFor($this->owner, 'CP/2');

        $this->actingAs($this->owner->user)->get("/cases/{$otherCase->id}/findings/{$finding->id}")->assertNotFound();
    }

    public function test_closing_requires_decisions_on_every_critical_finding(): void
    {
        $critical = $this->finding();
        $this->finding('info');

        $this->actingAs($this->owner->user)->post("/cases/{$this->case->id}/close")
            ->assertSessionHasErrors(['case' => 'Nie można zamknąć: sprawa nie została sprawdzona dla obecnych dokumentów. Użyj „Sprawdź ponownie”.']);
        $this->markEvaluated();
        $this->actingAs($this->owner->user)->post("/cases/{$this->case->id}/close")
            ->assertSessionHasErrors(['case' => 'Nie można zamknąć: 1 ustalenie krytyczne czeka na decyzję.']);
        $this->assertNotSame('closed', $this->asTenant(fn () => $this->case->refresh()->status));

        $this->decide($critical, ['decision' => 'rozbieznosc', 'comment' => 'potwierdzone']);
        $this->actingAs($this->owner->user)->post("/cases/{$this->case->id}/close")->assertSessionHasNoErrors();
        $this->assertSame('closed', $this->asTenant(fn () => $this->case->refresh()->status));

        $this->actingAs($this->owner->user)->post("/cases/{$this->case->id}/reopen");
        $this->assertSame('in_review', $this->asTenant(fn () => $this->case->refresh()->status));
        $events = $this->asTenant(fn () => AuditEvent::query()->where('event_type', 'case.status_changed')->orderBy('id')->pluck('payload')->all());
        $this->assertSame(['closed', 'in_review'], array_column($events, 'to'));
    }

    public function test_closed_cases_do_not_accept_documents(): void
    {
        $this->asTenant(fn () => $this->case->forceFill(['status' => 'closed'])->save());

        $this->actingAs($this->owner->user)
            ->post("/cases/{$this->case->id}/documents", ['files' => [UploadedFile::fake()->createWithContent('a.pdf', '%PDF-1.4 x')]])
            ->assertSessionHasErrors('case');
    }

    public function test_case_list_counts_and_filters_open_findings_by_severity(): void
    {
        $this->finding();
        $this->finding('info');
        $quiet = $this->caseFor($this->owner, 'CP/QUIET');

        $this->actingAs($this->owner->user)->get('/cases')->assertOk()->assertSee('krytyczne 1')->assertSee('CP/QUIET');
        $this->actingAs($this->owner->user)->get('/cases?severity=critical')
            ->assertOk()->assertSee($this->case->reference)->assertDontSee('CP/QUIET');
        $this->assertNotNull($quiet);
    }

    public function test_pages_send_a_strict_content_security_policy_and_no_inline_code(): void
    {
        $finding = $this->finding();

        foreach (['/cases', "/cases/{$this->case->id}", "/cases/{$this->case->id}/findings/{$finding->id}", "/cases/{$this->case->id}/documents/{$this->invoice->id}"] as $url) {
            $response = $this->actingAs($this->owner->user)->get($url)->assertOk();
            $csp = (string) $response->headers->get('Content-Security-Policy');
            $this->assertStringContainsString("script-src 'self'", $csp);
            $this->assertStringContainsString("style-src 'self'", $csp);
            $this->assertStringContainsString("frame-ancestors 'none'", $csp);
            $html = (string) $response->getContent();
            $this->assertDoesNotMatchRegularExpression('/<script(?![^>]*\bsrc=)[^>]*>/i', $html, "inline script on {$url}");
            $this->assertDoesNotMatchRegularExpression('/\sstyle\s*=/i', $html, "inline style on {$url}");
            $this->assertDoesNotMatchRegularExpression('/\son[a-z]+\s*=/i', $html, "inline handler on {$url}");
        }
    }

    public function test_a_decision_on_values_the_reviewer_did_not_see_is_rejected(): void
    {
        $finding = $this->finding();

        $this->actingAs($this->owner->user)->post("/cases/{$this->case->id}/findings/{$finding->id}/decisions", [
            'decision' => 'zgodne', 'comment' => 'ok', 'evidence_hash' => str_repeat('a', 64),
        ])->assertSessionHasErrors('decision');

        $this->assertSame(0, $this->asTenant(fn () => FindingDecision::query()->count()));
    }

    public function test_closing_is_refused_while_documents_are_processing_or_the_last_check_failed(): void
    {
        $this->markEvaluated();
        $this->asTenant(fn () => CaseEvaluation::query()->create([
            'case_file_id' => $this->case->id, 'status' => 'failed', 'error_code' => 'invalid_rules_response',
            'input_hash' => EvaluateCase::currentInputHash($this->case), 'findings_count' => 0,
        ]));
        $this->actingAs($this->owner->user)->post("/cases/{$this->case->id}/close")->assertSessionHasErrors('case');
        $this->actingAs($this->owner->user)->get("/cases/{$this->case->id}")->assertSee('Ostatnie sprawdzenie nie powiodło się');

        $this->markEvaluated();
        $this->asTenant(fn () => $this->invoice->forceFill(['status' => 'processing'])->save());
        $this->actingAs($this->owner->user)->post("/cases/{$this->case->id}/close")
            ->assertSessionHasErrors(['case' => 'Nie można zamknąć: dokumenty są jeszcze przetwarzane.']);
    }

    public function test_type_changes_wait_until_the_document_is_processed(): void
    {
        $this->asTenant(fn () => $this->invoice->forceFill(['status' => 'processing'])->save());

        $this->actingAs($this->owner->user)
            ->patch("/cases/{$this->case->id}/documents/{$this->invoice->id}/type", ['doc_type' => 'umowa'])
            ->assertSessionHasErrors('case');
        $this->assertSame('classifier', $this->asTenant(fn () => $this->invoice->refresh()->doc_type_source));
    }

    public function test_decisions_are_rate_limited(): void
    {
        $finding = $this->finding('info');
        for ($i = 0; $i < 60; $i++) {
            $this->decide($finding, ['decision' => 'zgodne']);
        }

        $this->decide($finding, ['decision' => 'zgodne'])->assertStatus(429);
    }
}
