<?php

namespace App\Http\Controllers;

use App\Http\Middleware\ResolveTenant;
use App\Services\AuditLog;
use App\Tenancy\TenantContext;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

class OrganizationSwitchController extends Controller
{
    public function __invoke(Request $request, TenantContext $tenant, AuditLog $audit): RedirectResponse
    {
        $validated = $request->validate(['organization_id' => ['required', 'uuid']]);

        // Resolved through the user's own memberships: an organization they do not belong to is a 404.
        $membership = $tenant->membershipFor($request->user(), $validated['organization_id']);
        abort_if($membership === null, 404);

        $tenant->activate($membership);
        $request->session()->put(ResolveTenant::SESSION_KEY, $membership->organization_id);
        $audit->record('organization.switched_in');

        return redirect()->route('cases.index');
    }
}
