<?php

namespace Tests;

use App\Enums\Role;
use App\Models\CaseFile;
use App\Models\Membership;
use App\Models\Organization;
use App\Models\User;
use App\Tenancy\TenantContext;
use Closure;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\DB;

abstract class TestCase extends BaseTestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        // RefreshDatabase has opened the per-test transaction; the role switch is rolled back with it.
        $this->actAsAppRole();
    }

    protected function actAsAppRole(): void
    {
        DB::statement('SET ROLE '.config('database.app_role'));
    }

    /**
     * Run fixture setup as the schema owner (bypasses RLS), then return to the runtime role.
     *
     * @template T
     *
     * @param  Closure(): T  $callback
     * @return T
     */
    protected function asOwner(Closure $callback): mixed
    {
        DB::statement('RESET ROLE');
        try {
            return $callback();
        } finally {
            $this->actAsAppRole();
        }
    }

    protected function caseFor(Membership $membership, string $reference = 'CP/1'): CaseFile
    {
        return app(TenantContext::class)->run($membership, fn () => CaseFile::create([
            'reference' => $reference, 'title' => 'Dom', 'created_by' => $membership->user_id,
        ]));
    }

    protected function member(Role $role = Role::Owner, ?Organization $organization = null, ?User $user = null): Membership
    {
        return $this->asOwner(fn () => Membership::factory()
            ->for($organization ?? Organization::factory()->create())
            ->for($user ?? User::factory()->create())
            ->create(['role' => $role])
            ->load('organization', 'user'));
    }
}
