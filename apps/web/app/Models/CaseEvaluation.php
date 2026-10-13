<?php

namespace App\Models;

use App\Tenancy\BelongsToOrganization;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Model;

/** One rule evaluation run of a case. */
class CaseEvaluation extends Model
{
    use BelongsToOrganization, HasUuids;

    protected $fillable = ['case_file_id', 'input_hash', 'reference_date', 'reference_source', 'ruleset', 'findings_count'];

    protected function casts(): array
    {
        return ['ruleset' => 'array', 'reference_date' => 'immutable_date', 'findings_count' => 'integer'];
    }
}
