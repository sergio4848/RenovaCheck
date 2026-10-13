<?php

namespace Database\Seeders;

use App\Enums\Role;
use App\Models\Membership;
use App\Models\Organization;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

/**
 * Demo tenants and accounts. Idempotent: re-running updates the same rows.
 * Runs as the schema owner (php artisan db:seed --database=migrator), which bypasses RLS.
 * All names are fictitious; the .test domain is reserved and never resolves.
 */
class DatabaseSeeder extends Seeder
{
    private const ORGANIZATIONS = [
        'alfa' => 'Alfa Termo Audyt Sp. z o.o. (DEMO)',
        'beta' => 'Beta Dokumentacja Energetyczna (DEMO)',
    ];

    /** email => [name, [org slug => role]] */
    private const USERS = [
        'wlasciciel@alfa.test' => ['Anna Wiśniewska-Demo', ['alfa' => Role::Owner]],
        'weryfikator@alfa.test' => ['Piotr Zieliński-Demo', ['alfa' => Role::Reviewer, 'beta' => Role::Reviewer]],
        'wlasciciel@beta.test' => ['Ewa Kowalczyk-Demo', ['beta' => Role::Owner]],
    ];

    public function run(): void
    {
        if (app()->isProduction()) {
            $this->command?->warn('Demo accounts are not seeded in production.');

            return;
        }
        $password = (string) env('DEMO_USER_PASSWORD', 'renova-demo');

        $organizations = [];
        foreach (self::ORGANIZATIONS as $slug => $name) {
            $organizations[$slug] = Organization::query()->updateOrCreate(['slug' => $slug], ['name' => $name]);
        }

        foreach (self::USERS as $email => [$name, $roles]) {
            $user = User::query()->updateOrCreate(
                ['email' => $email],
                ['name' => $name, 'password' => Hash::make($password), 'locale' => 'pl', 'email_verified_at' => now()],
            );
            foreach ($roles as $slug => $role) {
                Membership::query()->updateOrCreate(
                    ['organization_id' => $organizations[$slug]->id, 'user_id' => $user->id],
                    ['role' => $role],
                );
            }
        }
    }
}
