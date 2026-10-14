<?php

namespace App\Http\Controllers;

use App\Models\Membership;
use App\Tenancy\TenantContext;
use Illuminate\View\View;

class MemberController extends Controller
{
    public function index(TenantContext $tenant): View
    {
        $members = Membership::query()
            ->with('user:id,name,email')
            ->where('organization_id', $tenant->requireOrganizationId())
            ->orderBy('role')
            ->get();

        return view('members.index', ['members' => $members]);
    }
}
