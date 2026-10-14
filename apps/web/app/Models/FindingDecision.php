<?php

namespace App\Models;

use App\Tenancy\BelongsToOrganization;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/** One review decision on a finding. Rows are append-only (database triggers reject changes). */
class FindingDecision extends Model
{
    use BelongsToOrganization, HasUuids;

    public const DECISIONS = ['zgodne', 'rozbieznosc', 'uzgodniona_zmiana', 'nie_dotyczy'];

    public const UPDATED_AT = null;

    protected $fillable = ['finding_id', 'decision', 'comment', 'decided_by', 'evidence_hash', 'rule_version'];

    protected function casts(): array
    {
        return ['created_at' => 'immutable_datetime', 'rule_version' => 'integer'];
    }

    /** @return BelongsTo<User, $this> */
    public function decider(): BelongsTo
    {
        return $this->belongsTo(User::class, 'decided_by');
    }
}
