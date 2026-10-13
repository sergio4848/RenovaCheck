<?php

namespace App\Tenancy;

use App\Models\Organization;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * Application-level tenant filter. Row-level security already restricts rows in PostgreSQL;
 * this scope keeps queries explicit and fails closed when no organization is active.
 */
trait BelongsToOrganization
{
    public static function bootBelongsToOrganization(): void
    {
        static::addGlobalScope('organization', function (Builder $query) {
            $query->where($query->qualifyColumn('organization_id'), app(TenantContext::class)->requireOrganizationId());
        });

        static::creating(function ($model) {
            $model->organization_id ??= app(TenantContext::class)->requireOrganizationId();
        });
    }

    /** @return BelongsTo<Organization, $this> */
    public function organization(): BelongsTo
    {
        return $this->belongsTo(Organization::class);
    }
}
