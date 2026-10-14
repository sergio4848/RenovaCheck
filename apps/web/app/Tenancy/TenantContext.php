<?php

namespace App\Tenancy;

use App\Enums\Permission;
use App\Enums\Role;
use App\Models\Membership;
use App\Models\Organization;
use App\Models\User;
use Closure;
use Illuminate\Support\Facades\DB;

/**
 * The active organization and role for the current request or job.
 *
 * The organization id is also written to the PostgreSQL session setting app.organization_id,
 * which every row-level security policy reads. Long-lived processes (queue workers) must use
 * run() so the setting is cleared after each unit of work. set_config() is transactional: call
 * run()/clear() outside any transaction that might roll back, or the clearing is undone.
 */
final class TenantContext
{
    private ?Organization $organization = null;

    private ?Role $role = null;

    private ?string $userId = null;

    /** Identify the user to the database so their own memberships become visible. */
    public function identify(User $user): void
    {
        $this->identifyUserId($user->getKey());
    }

    public function identifyUserId(string $userId): void
    {
        $this->userId = $userId;
        $this->write('app.user_id', $userId);
    }

    /** The user's membership in the given organization, or their first one when null. */
    public function membershipFor(User $user, ?string $organizationId): ?Membership
    {
        $this->identify($user);

        return Membership::query()
            ->with('organization')
            ->where('user_id', $user->getKey())
            ->when($organizationId, fn ($q) => $q->where('organization_id', $organizationId))
            ->orderBy('created_at')
            ->first();
    }

    public function activate(Membership $membership): void
    {
        $this->organization = $membership->organization;
        $this->role = $membership->role;
        $this->userId = $membership->user_id;
        $this->write('app.user_id', $membership->user_id);
        $this->write('app.organization_id', $membership->organization_id);
    }

    public function clear(): void
    {
        $this->organization = null;
        $this->role = null;
        $this->userId = null;
        $this->write('app.organization_id', '');
        $this->write('app.user_id', '');
    }

    /**
     * @template T
     *
     * @param  Closure(): T  $callback
     * @return T
     */
    public function run(Membership $membership, Closure $callback): mixed
    {
        $this->activate($membership);
        try {
            return $callback();
        } finally {
            $this->clear();
        }
    }

    /**
     * Run background work for an organization without a signed-in user (queue jobs). Starts and
     * ends with a cleared context, so a long-lived worker never carries a tenant between jobs.
     *
     * @template T
     *
     * @param  Closure(): T  $callback
     * @return T
     */
    public function runForOrganization(string $organizationId, Closure $callback): mixed
    {
        $this->clear();
        $this->write('app.organization_id', $organizationId);
        try {
            $organization = Organization::query()->find($organizationId)
                ?? throw new MissingTenantContext;
            $this->organization = $organization;

            return $callback();
        } finally {
            $this->clear();
        }
    }

    public function organization(): ?Organization
    {
        return $this->organization;
    }

    public function organizationId(): ?string
    {
        return $this->organization?->getKey();
    }

    public function requireOrganizationId(): string
    {
        return $this->organizationId() ?? throw new MissingTenantContext;
    }

    public function role(): ?Role
    {
        return $this->role;
    }

    public function allows(Permission $permission): bool
    {
        return $this->role?->allows($permission) ?? false;
    }

    private function write(string $key, string $value): void
    {
        DB::connection()->selectOne('SELECT set_config(?, ?, false)', [$key, $value]);
    }
}
