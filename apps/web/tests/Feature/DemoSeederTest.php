<?php

namespace Tests\Feature;

use App\Models\User;
use Database\Seeders\DatabaseSeeder;
use Illuminate\Database\Eloquent\Model;
use Tests\TestCase;

class DemoSeederTest extends TestCase
{
    public function test_demo_accounts_are_seeded_outside_production_only(): void
    {
        $seed = fn () => $this->asOwner(fn () => Model::unguarded(fn () => $this->app->make(DatabaseSeeder::class)->run()));
        $demoUsers = fn () => $this->asOwner(fn () => User::query()->where('email', 'like', '%@alfa.test')->count());

        $this->app['env'] = 'production';
        $seed();
        $this->assertSame(0, $demoUsers());

        $this->app['env'] = 'testing';
        $seed();
        $this->assertSame(2, $demoUsers());
    }
}
