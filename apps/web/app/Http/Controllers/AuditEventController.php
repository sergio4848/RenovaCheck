<?php

namespace App\Http\Controllers;

use App\Models\AuditEvent;
use App\Services\AuditLog;
use Illuminate\View\View;

class AuditEventController extends Controller
{
    public function index(AuditLog $audit): View
    {
        return view('audit.index', [
            'events' => AuditEvent::query()->with('actor:id,name')->orderByDesc('id')->paginate(50),
            'brokenAt' => $audit->firstBrokenEventId(),
        ]);
    }
}
