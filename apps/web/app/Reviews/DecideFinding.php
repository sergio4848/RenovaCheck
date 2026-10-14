<?php

namespace App\Reviews;

use App\Models\CaseFile;
use App\Models\Finding;
use App\Models\FindingDecision;
use App\Models\User;
use App\Services\AuditLog;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;

/**
 * Records a reviewer's decision on a finding: an append-only decision row, the summary on the
 * finding and an audit event, in one transaction.
 */
final class DecideFinding
{
    public function __construct(private readonly AuditLog $audit) {}

    /**
     * @param  string  $seenEvidenceHash  the evidence hash of the finding as the reviewer saw it
     *
     * @throws ValidationException
     */
    public function __invoke(Finding $finding, string $decision, ?string $comment, string $seenEvidenceHash, User $user): FindingDecision
    {
        $comment = $comment !== null ? trim($comment) : null;
        $comment = $comment === '' ? null : $comment;
        if ($finding->severity === 'critical' && $comment === null) {
            throw ValidationException::withMessages(['comment' => __('A comment is required for critical findings.')]);
        }

        return DB::transaction(function () use ($finding, $decision, $comment, $seenEvidenceHash, $user) {
            // Re-read under lock: an evaluation or a close may have changed things since the page loaded.
            $case = CaseFile::query()->lockForUpdate()->findOrFail($finding->case_file_id);
            $finding = Finding::query()->lockForUpdate()->findOrFail($finding->id);
            if ($case->status === 'closed') {
                throw ValidationException::withMessages(['decision' => __('The case is closed. Reopen it to change decisions.')]);
            }
            if (! $finding->is_current) {
                throw ValidationException::withMessages(['decision' => __('This finding is no longer reported; check the case again.')]);
            }
            if (! hash_equals($finding->evidence_hash, $seenEvidenceHash)) {
                throw ValidationException::withMessages(['decision' => __('The values of this finding changed while you were reviewing it. Check them again.')]);
            }
            $row = $finding->decisions()->create([
                'decision' => $decision,
                'comment' => $comment,
                'decided_by' => $user->getKey(),
                'evidence_hash' => $finding->evidence_hash,
                'rule_version' => $finding->rule_version,
                'reason_pl' => $finding->reason_pl,
                'evidence' => $finding->evidence,
            ]);
            $finding->forceFill([
                'review_status' => 'rozstrzygniete',
                'decision' => $decision,
                'decided_at' => $row->created_at ?? now(),
                'decided_by' => $user->getKey(),
                'decided_evidence_hash' => $finding->evidence_hash,
            ])->save();
            $this->audit->record('finding.decided', $finding, [
                'decision' => $decision,
                'rule_id' => $finding->rule_id,
                'rule_version' => $finding->rule_version,
                'severity' => $finding->severity,
                'comment_length' => mb_strlen((string) $comment),
                'evidence_hash' => $finding->evidence_hash,
            ]);

            return $row;
        });
    }
}
