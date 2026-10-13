<?php

namespace App\Http\Middleware;

use App\Tenancy\TenantContext;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\View;
use Symfony\Component\HttpFoundation\Response;

/**
 * Activates the organization stored in the session (or the user's first membership) for the
 * rest of the request. A user without any membership is signed out.
 */
class ResolveTenant
{
    public const SESSION_KEY = 'organization_id';

    public function __construct(private readonly TenantContext $tenant) {}

    public function handle(Request $request, Closure $next): Response
    {
        $user = $request->user();
        $membership = $this->tenant->membershipFor($user, $request->session()->get(self::SESSION_KEY))
            ?? $this->tenant->membershipFor($user, null);

        if ($membership === null) {
            Auth::guard('web')->logout();
            $request->session()->invalidate();

            return redirect()->route('login')->withErrors(['email' => __('auth.no_membership')]);
        }

        $this->tenant->activate($membership);
        $request->session()->put(self::SESSION_KEY, $membership->organization_id);
        View::share('tenant', $this->tenant);

        return $next($request);
    }

    public function terminate(Request $request, Response $response): void
    {
        $this->tenant->clear();
    }
}
