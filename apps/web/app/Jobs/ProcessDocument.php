<?php

namespace App\Jobs;

use App\Documents\ExtractClient;
use App\Documents\ExtractFailed;
use App\Enums\DocType;
use App\Models\Document;
use App\Services\AuditLog;
use App\Tenancy\TenantContext;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\Middleware\WithoutOverlapping;
use Illuminate\Support\Facades\DB;
use Throwable;

/** Renders, reads and classifies one uploaded document via the extraction service. */
class ProcessDocument implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable;

    public int $tries = 3;

    // Longer than the HTTP timeout to the extraction service (services.extract.timeout, 180 s) and
    // shorter than the queue's retry_after (300 s), so a slow analysis is never delivered twice.
    public int $timeout = 240;

    public bool $failOnTimeout = true;

    /** @var list<int> */
    public array $backoff = [10, 60];

    public function __construct(public readonly string $organizationId, public readonly string $documentId) {}

    /** @return list<object> */
    public function middleware(): array
    {
        // At most one analysis per document at a time: a duplicate delivery while another worker
        // holds the lock is dropped, the running job finishes the document.
        return [(new WithoutOverlapping($this->documentId))->dontRelease()->expireAfter(300)];
    }

    public function handle(TenantContext $tenant, ExtractClient $extract, AuditLog $audit): void
    {
        $tenant->runForOrganization($this->organizationId, function () use ($extract, $audit) {
            $document = Document::query()->find($this->documentId);
            if ($document === null || $document->status === 'processed') {
                return; // deleted meanwhile, or a duplicate delivery of an already finished job
            }
            $document->forceFill(['status' => 'processing', 'error_code' => null])->save();

            try {
                $result = $extract->analyze($document);
            } catch (ExtractFailed $e) {
                if ($e->retryable && $this->attempts() < $this->tries) {
                    $document->forceFill(['status' => 'uploaded'])->save();
                    $this->release($this->backoff[$this->attempts() - 1] ?? 60);

                    return;
                }
                $this->markFailed($document, $e->errorCode, $audit);

                return;
            }

            DB::transaction(function () use ($document, $result, $audit) {
                $document->pages()->delete();
                foreach ($result['pages'] as $page) {
                    $document->pages()->create($page);
                }
                $classification = $result['classification'];
                if ($document->doc_type_source !== 'user') {
                    $type = $classification['doc_type'] === null ? null : DocType::from($classification['doc_type']);
                    $document->forceFill([
                        'doc_type' => $type,
                        'doc_type_source' => $type === null ? null : 'classifier',
                        'doc_type_confidence' => $type === null ? null : $classification['confidence'],
                    ]);
                }
                $document->forceFill([
                    'classification' => $classification + ['ocr_provider' => $result['ocr_provider']],
                    'page_count' => $result['page_count'],
                    'status' => 'processed',
                    'processed_at' => now(),
                ])->save();
                $audit->record('document.processed', $document, [
                    'doc_type' => $classification['doc_type'],
                    'confidence' => $classification['confidence'],
                    'pages' => $result['page_count'],
                    'ocr_provider' => $result['ocr_provider'],
                ]);
            });
        });
    }

    public function failed(?Throwable $exception): void
    {
        app(TenantContext::class)->runForOrganization($this->organizationId, function () {
            $document = Document::query()->find($this->documentId);
            if ($document !== null && $document->status !== 'processed') {
                $this->markFailed($document, 'processing_error', app(AuditLog::class));
            }
        });
    }

    private function markFailed(Document $document, string $code, AuditLog $audit): void
    {
        DB::transaction(function () use ($document, $code, $audit) {
            $document->forceFill(['status' => 'failed', 'error_code' => substr($code, 0, 64)])->save();
            $audit->record('document.processing_failed', $document, ['error_code' => $code]);
        });
    }
}
