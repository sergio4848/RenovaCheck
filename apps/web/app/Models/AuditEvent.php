<?php

namespace App\Models;

use App\Tenancy\BelongsToOrganization;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use LogicException;

/**
 * Read model for the append-only event log. Rows are written only through
 * App\Services\AuditLog; the database rejects updates and deletes.
 */
class AuditEvent extends Model
{
    use BelongsToOrganization;

    public const UPDATED_AT = null;

    protected $guarded = ['*'];

    protected function casts(): array
    {
        return [
            'payload' => 'array',
            'created_at' => 'immutable_datetime',
        ];
    }

    /** @return BelongsTo<User, $this> */
    public function actor(): BelongsTo
    {
        return $this->belongsTo(User::class, 'actor_user_id');
    }

    public function save(array $options = []): bool
    {
        throw new LogicException('Audit events are written through App\Services\AuditLog.');
    }

    public function delete(): ?bool
    {
        throw new LogicException('Audit events are append-only.');
    }
}
