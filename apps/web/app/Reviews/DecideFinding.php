<?php

namespace App\Reviews;

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

    /** @throws ValidationException */
    public function __invoke(Finding $finding, string $decision, ?string $comment, User $user): FindingDecision
    {
        $comment = $comment !== null ? trim($comment) : null;
        $comment = $comment === '' ? null : $comment;
        if (! $finding->is_current) {
            throw ValidationException::withMessages(['decision' => __('This finding is no longer reported; check the case again.')]);
        }
        if ($finding->caseFile->status === 'closed') {
            throw ValidationException::withMessages(['decision' => __('The case is closed. Reopen it to change decisions.')]);
        }
        if ($finding->severity === 'critical' && $comment === null) {
            throw ValidationException::withMessages(['comment' => __('A comment is required for critical findings.')]);
        }

        return DB::transaction(function () use ($finding, $decision, $comment, $user) {
            $row = $finding->decisions()->create([
                'decision' => $decision,
                'comment' => $comment,
                'decided_by' => $user->getKey(),
                'evidence_hash' => $finding->evidence_hash,
                'rule_version' => $finding->rule_version,
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
