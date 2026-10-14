<?php

namespace App\Providers;

use App\Auth\TenantAwareUserProvider;
use App\Enums\Permission;
use App\Models\User;
use App\Services\Antivirus\ClamdScanner;
use App\Services\Antivirus\Scanner;
use App\Services\Antivirus\SkippingScanner;
use App\Tenancy\TenantContext;
use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Http\Request;
use Illuminate\Pagination\Paginator;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Facades\RateLimiter;
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

        // Uploads, re-typing and re-checking start OCR (possibly paid) and rule runs: bound them
        // per user and per organization so one account cannot keep the analysis busy for everyone.
        $limit = fn (string $name, int $perUser, int $perOrganization) => RateLimiter::for($name, fn (Request $request) => [
            Limit::perMinute($perUser)->by($name.':user:'.$request->user()?->getAuthIdentifier()),
            Limit::perMinute($perOrganization)->by($name.':org:'.app(TenantContext::class)->organizationId()),
        ]);
        $limit('uploads', 10, 30);
        $limit('reprocess', 20, 60);
        $limit('evaluate', 6, 20);
        $limit('decisions', 60, 300);
        // Reports read the whole case and render a PDF in the request.
        $limit('reports', 10, 30);
    }
}
