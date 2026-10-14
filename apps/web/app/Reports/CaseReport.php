<?php

namespace App\Reports;

use App\Jobs\EvaluateCase;
use App\Models\CaseEvaluation;
use App\Models\CaseFile;
use App\Models\Document;
use App\Models\Finding;
use App\Models\FindingDecision;
use App\Models\User;
use Carbon\CarbonImmutable;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\DB;

/**
 * Snapshot of a case's review for export: current findings split into unapproved critical ones,
 * decided ones and other open ones, plus every decision ever made (who, when, what, why).
 */
final class CaseReport
{
    public const TIMEZONE = 'Europe/Warsaw';

    public const SECTIONS = ['niezatwierdzone', 'rozstrzygniete', 'pozostale_otwarte'];

    /**
     * @param  Collection<int, Document>  $documents
     * @param  array<string, Collection<int, Finding>>  $sections
     * @param  Collection<int, FindingDecision>  $decisions
     */
    private function __construct(
        public readonly CaseFile $case,
        public readonly ?CaseEvaluation $evaluation,
        public readonly bool $evaluationCurrent,
        public readonly Collection $documents,
        public readonly array $sections,
        public readonly Collection $decisions,
        public readonly User $generatedBy,
        public readonly CarbonImmutable $generatedAt,
    ) {}

    public static function build(CaseFile $case, User $generatedBy): self
    {
        // Decisions, evaluations and closing lock the case row for update; a shared lock keeps them
        // out while the report reads, so it never mixes the state before and after one of them.
        return DB::transaction(function () use ($case, $generatedBy) {
            $case = CaseFile::query()->with('creator:id,name')->sharedLock()->findOrFail($case->id);
            $evaluation = $case->evaluations()->latest('created_at')->first();
            $documents = $case->documents()->withCount('pages')->orderBy('created_at')->orderBy('original_name')->get();
            $findings = $case->findings()->current()->with('decider:id,name')->get()
                ->sortBy(fn (Finding $f) => [Finding::SEVERITY_ORDER[$f->severity], $f->rule_id, $f->first_seen_at])
                ->values();
            $decisions = FindingDecision::query()
                ->with(['decider:id,name'])
                ->join('findings', 'findings.id', '=', 'finding_decisions.finding_id')
                ->where('findings.case_file_id', $case->id)
                ->orderBy('finding_decisions.created_at')->orderBy('finding_decisions.id')
                ->select('finding_decisions.*', 'findings.rule_id', 'findings.title_pl as finding_title', 'findings.is_current as finding_is_current')
                ->get();

            return new self(
                $case,
                $evaluation,
                EvaluateCase::isCurrent($case, $evaluation),
                $documents,
                self::split($findings),
                $decisions,
                $generatedBy,
                CarbonImmutable::now(),
            );
        });
    }

    /**
     * @param  Collection<int, Finding>  $findings
     * @return array<string, Collection<int, Finding>>
     */
    private static function split(Collection $findings): array
    {
        $sections = array_map(fn () => collect(), array_flip(self::SECTIONS));
        foreach ($findings as $finding) {
            $section = match (true) {
                ! $finding->isOpen() => 'rozstrzygniete',
                $finding->severity === 'critical' => 'niezatwierdzone',
                default => 'pozostale_otwarte',
            };
            $sections[$section]->push($finding);
        }

        return $sections;
    }

    public function unapprovedCount(): int
    {
        return $this->sections['niezatwierdzone']->count();
    }

    public function findingsCount(): int
    {
        return array_sum(array_map(fn (Collection $c) => $c->count(), $this->sections));
    }

    public function documentName(string $id): string
    {
        return $this->documents->firstWhere('id', $id)?->original_name ?? $id;
    }

    /** @param  list<string>|null  $ids */
    public function documentNames(?array $ids): string
    {
        return implode(', ', array_map(fn (string $id) => $this->documentName($id), $ids ?? []));
    }

    public static function local(?\DateTimeInterface $time): string
    {
        return $time === null ? '' : CarbonImmutable::instance($time)->setTimezone(self::TIMEZONE)->format('Y-m-d H:i');
    }

    /**
     * Hash of the reviewed state (findings, decisions, evaluation), independent of when and by whom
     * the report was generated: two reports with the same fingerprint describe the same review.
     */
    public function fingerprint(): string
    {
        $state = [
            'case' => [$this->case->id, $this->case->status],
            'evaluation' => [$this->evaluation?->id, $this->evaluationCurrent],
            'findings' => array_map(
                fn (Collection $c) => $c->map(fn (Finding $f) => [$f->id, $f->evidence_hash, $f->review_status, $f->decision])->all(),
                $this->sections,
            ),
            'decisions' => $this->decisions->pluck('id')->all(),
        ];

        return hash('sha256', json_encode($state, JSON_THROW_ON_ERROR));
    }

    /** ASCII file name: the case reference is user input. */
    public function fileName(string $extension): string
    {
        $reference = preg_replace('/[^A-Za-z0-9]+/', '-', (string) $this->case->reference) ?? '';
        $reference = trim(substr($reference, 0, 60), '-');

        return 'raport-'.($reference !== '' ? $reference : 'sprawa').'-'.$this->generatedAt->setTimezone(self::TIMEZONE)->format('Ymd').'.'.$extension;
    }
}
