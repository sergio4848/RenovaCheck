<?php

namespace App\Jobs;

use App\Documents\ExtractClient;
use App\Documents\ExtractFailed;
use App\Models\CaseEvaluation;
use App\Models\CaseFile;
use App\Models\Document;
use App\Rules\EvaluationResult;
use App\Services\AuditLog;
use App\Tenancy\TenantContext;
use DateTimeInterface;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\Middleware\WithoutOverlapping;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\DB;

/**
 * Runs the rules on a case's stored fields and keeps its findings in step: findings are matched by
 * fingerprint, updated in place, marked not current when no longer reported and never deleted.
 */
class EvaluateCase implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable;

    public int $timeout = 60;

    /** @var list<int> */
    public array $backoff = [5, 30, 60];

    public function __construct(
        public readonly string $organizationId,
        public readonly string $caseFileId,
        public readonly bool $force = false,
    ) {}

    /** @return list<object> */
    public function middleware(): array
    {
        // One evaluation per case at a time; a concurrent request waits and then sees the latest data.
        return [(new WithoutOverlapping('case-evaluation:'.$this->caseFileId))->releaseAfter(5)->expireAfter(120)];
    }

    public function retryUntil(): DateTimeInterface
    {
        return now()->addMinutes(10);
    }

    public function handle(TenantContext $tenant, ExtractClient $extract, AuditLog $audit): void
    {
        $tenant->runForOrganization($this->organizationId, function () use ($extract, $audit) {
            $case = CaseFile::query()->find($this->caseFileId);
            if ($case === null || $case->documents()->whereIn('status', ['uploaded', 'processing'])->exists()) {
                return; // the last document to finish processing dispatches the evaluation again
            }
            $documents = $case->documents()->with(['pages', 'fields'])->whereIn('status', ['processed', 'failed'])->get();
            $input = self::input($case, $documents);
            $inputHash = hash('sha256', json_encode($input, JSON_THROW_ON_ERROR));
            $latest = $case->evaluations()->latest('created_at')->first();
            if (! $this->force && $latest?->input_hash === $inputHash) {
                return; // nothing changed since the last evaluation
            }

            try {
                $result = EvaluationResult::parse($extract->evaluate($input), $case, $documents->pluck('id')->all());
            } catch (ExtractFailed $e) {
                if ($e->retryable) {
                    throw $e; // retried with backoff until retryUntil()
                }
                $audit->record('case.evaluation_failed', $case, ['error_code' => $e->errorCode]);

                return;
            }

            DB::transaction(fn () => $this->store($case, $result, $inputHash, $audit));
        });
    }

    /**
     * @param  Collection<int, Document>  $documents
     * @return array<string, mixed>
     */
    public static function input(CaseFile $case, Collection $documents): array
    {
        return [
            'case_id' => $case->id,
            'fallback_reference_date' => $case->created_at->toDateString(),
            'documents' => $documents->sortBy('id')->values()->map(fn (Document $d) => [
                'doc_id' => $d->id,
                'doc_type' => $d->doc_type?->value,
                'status' => $d->status === 'failed' ? 'failed' : 'processed',
                'text_source' => self::textSource($d),
                'fields' => $d->fields->sortBy('name')->values()->map(fn ($f) => [
                    'name' => $f->name,
                    'value' => $f->value,
                    'raw_text' => $f->raw_text,
                    'status' => $f->status,
                    'confidence' => $f->confidence,
                ])->all(),
            ])->all(),
        ];
    }

    private static function textSource(Document $document): string
    {
        $sources = $document->pages->pluck('text_source')->unique()->values();
        if ($sources->isEmpty()) {
            return 'none';
        }

        return $sources->count() > 1 ? 'mixed' : (string) $sources->first();
    }

    /** @param  array<string, mixed>  $result */
    private function store(CaseFile $case, array $result, string $inputHash, AuditLog $audit): void
    {
        $now = now();
        $existing = $case->findings()->get()->keyBy('fingerprint');
        $reported = [];
        $new = 0;
        $reopened = 0;
        foreach ($result['findings'] as $item) {
            $reported[] = $item['fingerprint'];
            $attributes = [
                'rule_id' => $item['rule_id'],
                'rule_version' => $item['rule_version'],
                'family' => $item['family'],
                'outcome' => $item['outcome'],
                'severity' => $item['severity'],
                'title_pl' => $item['title_pl'],
                'reason_pl' => $item['reason_pl'],
                'subject_doc_ids' => $item['subject_doc_ids'],
                'context_doc_ids' => $item['context_doc_ids'],
                'fields' => $item['fields'],
                'evidence' => $item['evidence'],
                'evidence_hash' => $item['evidence_hash'],
                'rule_source_url' => $item['source_url'] ?: null,
                'is_current' => true,
                'last_evaluated_at' => $now,
            ];
            $finding = $existing->get($item['fingerprint']);
            if ($finding === null) {
                $case->findings()->create($attributes + ['fingerprint' => $item['fingerprint'], 'first_seen_at' => $now]);
                $new++;
            } else {
                if ($finding->decision !== null) {
                    // A decision holds for the values it was made on; changed values need a second look.
                    $changed = $finding->decided_evidence_hash !== $item['evidence_hash'];
                    $attributes['review_status'] = $changed ? 'do_ponownej_weryfikacji' : 'rozstrzygniete';
                    $reopened += (int) ($changed && $finding->review_status === 'rozstrzygniete');
                }
                $finding->fill($attributes)->save();
            }
        }
        $resolved = $case->findings()->current()->whereNotIn('fingerprint', $reported)->update([
            'is_current' => false,
            'last_evaluated_at' => $now,
            'updated_at' => $now,
        ]);
        if ($case->status === 'new') {
            $case->forceFill(['status' => 'in_review'])->save();
            $audit->record('case.status_changed', $case, ['from' => 'new', 'to' => 'in_review']);
        }
        CaseEvaluation::query()->create([
            'case_file_id' => $case->id,
            'input_hash' => $inputHash,
            'reference_date' => $result['reference_date'],
            'reference_source' => $result['reference_source'],
            'ruleset' => $result['ruleset'],
            'findings_count' => count($result['findings']),
        ]);
        $audit->record('case.evaluated', $case, [
            'findings' => count($result['findings']),
            'new' => $new,
            'no_longer_reported' => $resolved,
            'needs_second_look' => $reopened,
            'reference_date' => $result['reference_date'],
            'ruleset' => array_map(fn ($r) => $r['id'].'@'.$r['version'], $result['ruleset']),
        ]);
    }
}
