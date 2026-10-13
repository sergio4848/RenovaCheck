<?php

namespace App\Http\Controllers;

use App\Http\Requests\StoreCaseFileRequest;
use App\Models\AuditEvent;
use App\Models\CaseFile;
use App\Services\AuditLog;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\View\View;

class CaseFileController extends Controller
{
    public function index(Request $request): View
    {
        $status = $request->query('status');
        $cases = CaseFile::query()
            ->with('creator:id,name')
            ->when(in_array($status, CaseFile::STATUSES, true), fn ($q) => $q->where('status', $status))
            ->latest()
            ->paginate(25)
            ->withQueryString();

        return view('cases.index', ['cases' => $cases, 'status' => $status]);
    }

    public function store(StoreCaseFileRequest $request, AuditLog $audit): RedirectResponse
    {
        $case = DB::transaction(function () use ($request, $audit) {
            $case = CaseFile::create([
                ...$request->validated(),
                'status' => 'new',
                'created_by' => $request->user()->getKey(),
            ]);
            $audit->record('case.created', $case, ['reference' => $case->reference]);

            return $case;
        });

        return redirect()->route('cases.show', $case)->with('status', __('Case created.'));
    }

    public function show(CaseFile $caseFile): View
    {
        $events = AuditEvent::query()
            ->with('actor:id,name')
            ->where(fn ($q) => $q
                ->where(fn ($q) => $q->where('subject_type', 'CaseFile')->where('subject_id', $caseFile->getKey()))
                ->orWhere(fn ($q) => $q->where('subject_type', 'Document')
                    ->whereIn('subject_id', $caseFile->documents()->select('id'))))
            ->orderBy('id')
            ->get();

        $documents = $caseFile->documents()->with('pages')->withCount('fields')->orderBy('created_at')->orderBy('original_name')->get();

        return view('cases.show', [
            'case' => $caseFile->load('creator:id,name'),
            'events' => $events,
            'documents' => $documents,
        ]);
    }
}
