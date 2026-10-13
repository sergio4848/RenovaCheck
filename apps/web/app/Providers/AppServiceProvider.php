<?php

namespace App\Providers;

use App\Auth\TenantAwareUserProvider;
use App\Enums\Permission;
use App\Models\User;
use App\Services\Antivirus\ClamdScanner;
use App\Services\Antivirus\Scanner;
use App\Services\Antivirus\SkippingScanner;
use App\Tenancy\TenantContext;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Pagination\Paginator;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        // Scoped: reset between requests and between queued jobs.
        $this->app->scoped(TenantContext::class);
        $this->app->bind(Scanner::class, fn () => config('services.clamav.enabled')
            ? ClamdScanner::tcp((string) config('services.clamav.host'), (int) config('services.clamav.port'))
            : new SkippingScanner);
    }

    public function boot(): void
    {
        Model::shouldBeStrict(! $this->app->isProduction());
        Paginator::useBootstrapFive();

        Auth::provider('tenant-eloquent', fn ($app, array $config) => new TenantAwareUserProvider($app['hash'], $config['model']));

        foreach (Permission::cases() as $permission) {
            Gate::define($permission->value, fn (User $user) => app(TenantContext::class)->allows($permission));
        }
    }
}
