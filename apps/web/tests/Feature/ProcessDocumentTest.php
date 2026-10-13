<?php

namespace Tests\Feature;

use App\Documents\ExtractClient;
use App\Enums\DocType;
use App\Jobs\ProcessDocument;
use App\Models\AuditEvent;
use App\Models\CaseFile;
use App\Models\Document;
use App\Models\Membership;
use App\Services\AuditLog;
use App\Tenancy\TenantContext;
use Illuminate\Queue\Middleware\WithoutOverlapping;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class ProcessDocumentTest extends TestCase
{
    private Membership $owner;

    private CaseFile $case;

    private Document $document;

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.extract.url' => 'http://extract:8000', 'services.extract.token' => 'secret-token']);
        Storage::fake('s3');
        Storage::disk('s3')->buildTemporaryUrlsUsing(fn (string $path) => "http://minio:9000/renova-documents/{$path}?sig=1");
        $this->owner = $this->member();
        $this->case = $this->caseFor($this->owner);
        $this->document = app(TenantContext::class)->run($this->owner, fn () => Document::factory()->create([
            'case_file_id' => $this->case->id, 'uploaded_by' => $this->owner->user_id,
        ]));
        app(TenantContext::class)->clear();
    }

    /** @return array<string, mixed> */
    private function response(array $overrides = []): array
    {
        return array_replace_recursive([
            'document_id' => $this->document->id,
            'mime' => 'application/pdf',
            'page_count' => 1,
            'pages' => [[
                'page_no' => 1, 'width_pt' => 595.28, 'height_pt' => 841.89,
                'image_key' => $this->document->storagePrefix().'pages/001.png',
                'image_width_px' => 1240, 'image_height_px' => 1754, 'text_source' => 'text_layer', 'word_count' => 210,
            ]],
            'classification' => ['doc_type' => 'faktura', 'confidence' => 0.92, 'scores' => ['faktura' => 11], 'evidence' => ['faktura vat nr']],
            'ocr_provider' => 'tesseract',
        ], $overrides);
    }

    private function runJob(?string $documentId = null, ?string $organizationId = null): void
    {
        (new ProcessDocument($organizationId ?? $this->owner->organization_id, $documentId ?? $this->document->id))
            ->handle(app(TenantContext::class), app(ExtractClient::class), app(AuditLog::class));
    }

    private function fresh(): Document
    {
        return app(TenantContext::class)->run($this->owner, fn () => Document::query()->with('pages')->findOrFail($this->document->id));
    }

    public function test_successful_analysis_stores_pages_and_classifier_type(): void
    {
        Http::fake(['extract:8000/*' => Http::response($this->response())]);

        $this->runJob();

        $document = $this->fresh();
        $this->assertSame('processed', $document->status);
        $this->assertSame(DocType::Faktura, $document->doc_type);
        $this->assertSame('classifier', $document->doc_type_source);
        $this->assertEqualsWithDelta(0.92, $document->doc_type_confidence, 0.0001);
        $this->assertSame(1, $document->pages->count());
        $this->assertSame('tesseract', $document->classification['ocr_provider']);
        Http::assertSent(fn ($request) => $request->hasHeader('Authorization', 'Bearer secret-token')
            && $request['output_prefix'] === $this->document->storagePrefix()
            && str_starts_with($request['source_url'], 'http://minio:9000/renova-documents/'));
        $this->assertSame(1, app(TenantContext::class)->run($this->owner,
            fn () => AuditEvent::query()->where('event_type', 'document.processed')->count()));
    }

    public function test_a_manual_type_survives_reprocessing(): void
    {
        app(TenantContext::class)->run($this->owner, fn () => $this->document->forceFill([
            'doc_type' => DocType::Umowa, 'doc_type_source' => 'user',
        ])->save());
        Http::fake(['extract:8000/*' => Http::response($this->response())]);

        $this->runJob();

        $this->assertSame(DocType::Umowa, $this->fresh()->doc_type);
    }

    public function test_rejected_documents_fail_without_retry(): void
    {
        Http::fake(['extract:8000/*' => Http::response(['error' => ['code' => 'unsupported_document']], 422)]);

        $this->runJob();

        $document = $this->fresh();
        $this->assertSame('failed', $document->status);
        $this->assertSame('unsupported_document', $document->error_code);
    }

    public function test_server_errors_are_retried(): void
    {
        Http::fake(['extract:8000/*' => Http::response(['error' => ['code' => 'internal_error']], 503)]);

        $this->runJob();

        $this->assertSame('uploaded', $this->fresh()->status);
    }

    public function test_responses_outside_the_contract_are_not_stored(): void
    {
        $evil = $this->response(['pages' => [['image_key' => 'org/other/secret.png']]]);
        Http::fake(['extract:8000/*' => Http::response($evil)]);

        $this->runJob();

        $document = $this->fresh();
        $this->assertSame('failed', $document->status);
        $this->assertSame('invalid_extract_response', $document->error_code);
        $this->assertSame(0, $document->pages->count());
    }

    public function test_job_for_another_organization_sees_nothing_and_leaves_no_context(): void
    {
        $other = $this->member();
        Http::fake();

        $this->runJob($this->document->id, $other->organization_id);

        Http::assertNothingSent();
        $this->assertSame('uploaded', $this->fresh()->status);
        $setting = DB::selectOne("SELECT current_setting('app.organization_id', true) AS v")->v;
        $this->assertSame('', (string) $setting);
    }

    public function test_one_analysis_per_document_at_a_time(): void
    {
        $job = new ProcessDocument($this->owner->organization_id, $this->document->id);
        [$middleware] = $job->middleware();

        $this->assertInstanceOf(WithoutOverlapping::class, $middleware);
        $this->assertSame($this->document->id, $middleware->key);
        $this->assertNull($middleware->releaseAfter);
        $this->assertLessThan((int) config('queue.connections.redis.retry_after'), $job->timeout);
        $this->assertGreaterThan((int) config('services.extract.timeout'), $job->timeout);
    }
}
