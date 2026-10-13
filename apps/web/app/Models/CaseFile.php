<?php

namespace App\Models;

use App\Tenancy\BelongsToOrganization;
use Database\Factories\CaseFileFactory;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

/** A "sprawa": one renovation project whose documents are checked against each other. */
class CaseFile extends Model
{
    /** @use HasFactory<CaseFileFactory> */
    use BelongsToOrganization, HasFactory, HasUuids;

    public const STATUSES = ['new', 'in_review', 'closed'];

    protected $fillable = ['reference', 'title', 'status', 'created_by'];

    /** @return BelongsTo<User, $this> */
    public function creator(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    /** @return HasMany<Finding, $this> */
    public function findings(): HasMany
    {
        return $this->hasMany(Finding::class);
    }

    /** @return HasMany<CaseEvaluation, $this> */
    public function evaluations(): HasMany
    {
        return $this->hasMany(CaseEvaluation::class);
    }

    /** @return HasMany<Document, $this> */
    public function documents(): HasMany
    {
        return $this->hasMany(Document::class);
    }
}
