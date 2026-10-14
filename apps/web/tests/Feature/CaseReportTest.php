<?php

namespace Tests\Feature;

use App\Jobs\EvaluateCase;
use App\Models\AuditEvent;
use App\Models\CaseEvaluation;
use App\Models\CaseFile;
use App\Models\Document;
use App\Models\Finding;
use App\Models\Membership;
use App\Reports\CaseReport;
use App\Reports\CaseReportCsv;
use App\Tenancy\TenantContext;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class CaseReportTest extends TestCase
{
    private Membership $owner;

    private CaseFile $case;

    private Document $invoice;

    protected function setUp(): void
    {
        parent::setUp();
        Queue::fake();
        Storage::fake('s3-public');
        $this->owner = $this->member();
        $this->case = $this->caseFor($this->owner, 'CP/2026/7;1');
        $this->invoice = $this->asTenant(function () {
            $document = Document::factory()->create([
                'case_file_id' => $this->case->id, 'uploaded_by' => $this->owner->user_id, 'status' => 'processed',
                'original_name' => '=HYPERLINK("http://x")faktura.pdf',
            ]);
            $document->forceFill(['doc_type' => 'faktura', 'doc_type_source' => 'classifier'])->save();

            return $document;
        });
    }

    private function asTenant(callable $callback): mixed
    {
        $result = app(TenantContext::class)->run($this->owner, $callback);
        app(TenantContext::class)->clear();

        return $result;
    }

    private function finding(string $severity, string $rule, array $overrides = []): Finding
    {
        return $this->asTenant(fn () => $this->case->findings()->create([
            'fingerprint' => hash('sha256', $rule.$severity),
            'rule_id' => $rule, 'rule_version' => 1, 'family' => 'amount', 'outcome' => 'discrepancy',
            'severity' => $severity, 'title_pl' => "Tytuł {$rule}", 'reason_pl' => "Uzasadnienie {$rule}; „cytat”",
            'subject_doc_ids' => [$this->invoice->id], 'context_doc_ids' => [], 'fields' => ['amount_gross'],
            'evidence' => [], 'evidence_hash' => str_repeat('a', 64),
            'first_seen_at' => now(), 'last_evaluated_at' => now(),
        ] + $overrides));
    }

    private function decide(Finding $finding, string $decision, string $comment): void
    {
        $this->actingAs($this->owner->user)
            ->post("/cases/{$this->case->id}/findings/{$finding->id}/decisions", [
                'decision' => $decision, 'comment' => $comment, 'evidence_hash' => $finding->evidence_hash,
            ])->assertSessionHasNoErrors();
    }

    private function markEvaluated(): void
    {
        $this->asTenant(fn () => CaseEvaluation::query()->create([
            'case_file_id' => $this->case->id, 'status' => 'ok', 'input_hash' => EvaluateCase::currentInputHash($this->case),
            'reference_date' => '2026-03-02', 'reference_source' => 'application_date',
            'ruleset' => [['id' => 'AMT-01', 'version' => 1]], 'findings_count' => 3,
        ]));
    }

    /** @return list<list<string>> */
    private function csvRows(string $body): array
    {
        $this->assertStringStartsWith("\u{FEFF}", $body);
        $handle = fopen('php://memory', 'r+');
        fwrite($handle, substr($body, 3));
        rewind($handle);
        $rows = [];
        while (($row = fgetcsv($handle, null, ';', '"', '')) !== false) {
            $rows[] = $row;
        }

        return $rows;
    }

    public function test_csv_lists_unapproved_critical_findings_first_and_every_decision(): void
    {
        $unapproved = $this->finding('critical', 'AMT-01');
        $decided = $this->finding('critical', 'AMT-02');
        $this->finding('info', 'QLT-01');
        $this->decide($decided, 'zgodne', 'Sprawdzono z oryginałem');
        $this->markEvaluated();

        $response = $this->actingAs($this->owner->user)->get("/cases/{$this->case->id}/report.csv")->assertOk();

        $this->assertStringStartsWith('text/csv', $response->headers->get('Content-Type'));
        $this->assertMatchesRegularExpression('/filename=raport-CP-2026-7-1-\d{8}\.csv/', $response->headers->get('Content-Disposition'));
        $body = $response->streamedContent();
        $this->assertStringContainsString("\r\n", $body);
        $rows = $this->csvRows($body);
        $sections = array_values(array_filter(array_map(fn ($r) => $r[1] ?? null, $rows), fn ($v) => in_array($v, ['AMT-01 v1', 'AMT-02 v1', 'QLT-01 v1'], true)));
        $this->assertSame(['AMT-01 v1', 'AMT-02 v1', 'QLT-01 v1'], array_slice($sections, 0, 3));
        $byRule = collect($rows)->keyBy(fn ($r) => $r[1] ?? '');
        $this->assertSame('Niezatwierdzone ustalenia krytyczne', $byRule['AMT-01 v1'][0]);
        $this->assertSame('Rozstrzygnięte', $byRule['AMT-02 v1'][0]);
        $this->assertSame('Zgodne', $byRule['AMT-02 v1'][8]);
        $this->assertSame($this->owner->user->name, $byRule['AMT-02 v1'][9]);
        $this->assertSame('Pozostałe otwarte', $byRule['QLT-01 v1'][0]);
        $this->assertSame('Uzasadnienie AMT-01; „cytat”', $byRule['AMT-01 v1'][5]);
        // A spreadsheet must not run a document name as a formula.
        $this->assertSame('\'=HYPERLINK("http://x")faktura.pdf', $byRule['AMT-01 v1'][6]);

        $history = collect($rows)->first(fn ($r) => ($r[5] ?? null) === 'Sprawdzono z oryginałem');
        $this->assertNotNull($history);
        $this->assertSame([$this->owner->user->name, 'AMT-02 v1', 'Tytuł AMT-02', 'Zgodne'], array_slice($history, 1, 4));
        $this->assertSame(str_repeat('a', 12), $history[6]);

        $this->asTenant(function () use ($unapproved) {
            $event = AuditEvent::query()->where('event_type', 'case.report_exported')->sole();
            $this->assertSame(['format' => 'csv', 'findings' => 3, 'unapproved' => 1], array_intersect_key($event->payload, array_flip(['format', 'findings', 'unapproved'])));
            $this->assertSame($this->case->id, $event->subject_id);
            $this->assertNotNull($unapproved->id);
        });
    }

    public function test_pdf_is_a_pdf_and_its_view_shows_the_sections(): void
    {
        $this->finding('critical', 'AMT-01');
        $decided = $this->finding('warning', 'AMT-03');
        $this->decide($decided, 'rozbieznosc', 'Kwota z korekty');
        $this->markEvaluated();

        $response = $this->actingAs($this->owner->user)->get("/cases/{$this->case->id}/report.pdf")->assertOk();
        $this->assertSame('application/pdf', $response->headers->get('Content-Type'));
        $this->assertStringStartsWith('%PDF-', $response->getContent());

        $html = $this->asTenant(fn () => view('reports.case', ['report' => CaseReport::build($this->case, $this->owner->user)])->render());
        $this->assertStringContainsString('Niezatwierdzone ustalenia krytyczne (1)', $html);
        $this->assertStringContainsString('Rozstrzygnięte (1)', $html);
        $this->assertStringContainsString('Kwota z korekty', $html);
        $this->assertStringContainsString('Raport pomocniczy', $html);
        $this->assertStringNotContainsString('Ocena nieaktualna', $html);
        $this->assertStringNotContainsString('<script', $html);
        // The web image has no GD extension: dompdf can only place vector (SVG) images there.
        $this->assertMatchesRegularExpression('#<img src="[^"]+/reports/assets/logo-horizontal\.svg"#', $html);
        $this->assertDoesNotMatchRegularExpression('#<img src="[^"]+\.(png|jpe?g|gif)"#i', $html);
    }

    public function test_outdated_evaluation_is_flagged(): void
    {
        $this->finding('critical', 'AMT-01');

        $html = $this->asTenant(fn () => view('reports.case', ['report' => CaseReport::build($this->case, $this->owner->user)])->render());

        $this->assertStringContainsString('Ocena nieaktualna', $html);
        $this->assertStringContainsString('Sprawa nie została jeszcze sprawdzona.', $html);
    }

    public function test_fingerprint_changes_with_decisions_only(): void
    {
        $finding = $this->finding('critical', 'AMT-01');
        $first = $this->asTenant(fn () => CaseReport::build($this->case, $this->owner->user)->fingerprint());
        $again = $this->asTenant(fn () => CaseReport::build($this->case, $this->owner->user)->fingerprint());
        $this->decide($finding, 'zgodne', 'ok');
        $after = $this->asTenant(fn () => CaseReport::build($this->case, $this->owner->user)->fingerprint());

        $this->assertSame($first, $again);
        $this->assertNotSame($first, $after);
    }

    public function test_reports_of_another_organization_are_not_found(): void
    {
        $stranger = $this->member();

        $this->actingAs($stranger->user)->get("/cases/{$this->case->id}/report.csv")->assertNotFound();
        $this->actingAs($stranger->user)->get("/cases/{$this->case->id}/report.pdf")->assertNotFound();
        auth()->forgetGuards();
        $this->get("/cases/{$this->case->id}/report.csv")->assertRedirect('/login');
    }

    public function test_reports_are_rate_limited(): void
    {
        for ($i = 0; $i < 10; $i++) {
            $this->actingAs($this->owner->user)->get("/cases/{$this->case->id}/report.csv")->assertOk();
        }
        $this->actingAs($this->owner->user)->get("/cases/{$this->case->id}/report.csv")->assertTooManyRequests();
    }

    public function test_cells_that_start_a_formula_are_neutralised(): void
    {
        foreach (['=1+1', '+48 600', '-2', '@SUM(A1)', "\tx"] as $value) {
            $this->assertStringStartsWith("'", trim(CaseReportCsv::cell($value), '"'));
        }
        $this->assertSame('"a;b"', CaseReportCsv::cell('a;b'));
        $this->assertSame('"say ""hi"""', CaseReportCsv::cell('say "hi"'));
        $this->assertSame('zwykły tekst', CaseReportCsv::cell('zwykły tekst'));
    }

    public function test_case_page_links_both_reports(): void
    {
        $this->actingAs($this->owner->user)->get("/cases/{$this->case->id}")
            ->assertOk()
            ->assertSee("/cases/{$this->case->id}/report.pdf", false)
            ->assertSee("/cases/{$this->case->id}/report.csv", false);
    }

    public function test_pages_carry_the_logo_and_favicon(): void
    {
        $this->get('/login')->assertOk()
            ->assertSee('favicon.svg', false)
            ->assertSee('images/logo-horizontal.svg', false);

        $this->actingAs($this->owner->user)->get("/cases/{$this->case->id}")->assertOk()
            ->assertSee('images/logo-horizontal.svg', false)
            ->assertSee('images/logo-inverse.svg', false);
    }
}
