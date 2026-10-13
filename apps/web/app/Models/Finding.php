<?php

namespace App\Models;

use App\Tenancy\BelongsToOrganization;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/** A rule finding on a case; born "do_sprawdzenia", identified across re-evaluations by its fingerprint. */
class Finding extends Model
{
    use BelongsToOrganization, HasUuids;

    public const SEVERITY_ORDER = ['critical' => 0, 'warning' => 1, 'info' => 2];

    protected $fillable = [
        'case_file_id', 'fingerprint', 'rule_id', 'rule_version', 'family', 'outcome', 'severity', 'title_pl',
        'reason_pl', 'subject_doc_ids', 'context_doc_ids', 'fields', 'evidence', 'evidence_hash', 'is_current',
        'first_seen_at', 'last_evaluated_at',
    ];

    protected function casts(): array
    {
        return [
            'subject_doc_ids' => 'array',
            'context_doc_ids' => 'array',
            'fields' => 'array',
            'evidence' => 'array',
            'is_current' => 'boolean',
            'rule_version' => 'integer',
            'first_seen_at' => 'immutable_datetime',
            'last_evaluated_at' => 'immutable_datetime',
        ];
    }

    /** @return BelongsTo<CaseFile, $this> */
    public function caseFile(): BelongsTo
    {
        return $this->belongsTo(CaseFile::class);
    }

    /** @param  Builder<Finding>  $query */
    public function scopeCurrent(Builder $query): void
    {
        $query->where('is_current', true);
    }
}
