<?php

use App\Http\Middleware\ResolveTenant;
use App\Http\Middleware\SetLocale;
use App\Tenancy\MissingTenantContext;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Routing\Middleware\SubstituteBindings;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware) {
        $middleware->web(append: [SetLocale::class]);
        $middleware->alias(['tenant' => ResolveTenant::class]);
        // Route model binding must run inside the tenant context so RLS scopes the lookup.
        $middleware->prependToPriorityList(SubstituteBindings::class, ResolveTenant::class);
        $middleware->redirectUsersTo('/cases');
    })
    ->withExceptions(function (Exceptions $exceptions) {
        // Fail closed: a query on tenant data without an active organization is a bug, not a 500 leak.
        $exceptions->render(fn (MissingTenantContext $e) => abort(403));
    })->create();
