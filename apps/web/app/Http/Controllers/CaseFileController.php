<?php

namespace App\Http\Controllers;

use App\Http\Requests\StoreCaseFileRequest;
use App\Jobs\EvaluateCase;
use App\Models\AuditEvent;
use App\Models\CaseFile;
use App\Models\Finding;
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
        $severity = $request->query('severity');
        $open = fn ($q, string $level) => $q->where('severity', $level)->where('is_current', true)
            ->where('review_status', '!=', 'rozstrzygniete');
        $cases = CaseFile::query()
            ->with('creator:id,name')
            ->withCount([
                'findings as open_critical_count' => fn ($q) => $open($q, 'critical'),
                'findings as open_warning_count' => fn ($q) => $open($q, 'warning'),
                'findings as open_info_count' => fn ($q) => $open($q, 'info'),
            ])
            ->when(in_array($status, CaseFile::STATUSES, true), fn ($q) => $q->where('status', $status))
            ->when(in_array($severity, ['critical', 'warning', 'info'], true),
                fn ($q) => $q->whereHas('findings', fn ($f) => $open($f, $severity)))
            ->latest()
            ->paginate(25)
            ->withQueryString();

        return view('cases.index', ['cases' => $cases, 'status' => $status, 'severity' => $severity]);
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
                    ->whereIn('subject_id', $caseFile->documents()->select('id')))
                ->orWhere(fn ($q) => $q->where('subject_type', 'Finding')
                    ->whereIn('subject_id', $caseFile->findings()->select('id'))))
            ->orderBy('id')
            ->get();

        $documents = $caseFile->documents()->with(['pages', 'fields:id,document_id,name'])->withCount('fields')
            ->orderBy('created_at')->orderBy('original_name')->get();
        $findings = $caseFile->findings()->current()->get()
            ->sortBy(fn (Finding $f) => [Finding::SEVERITY_ORDER[$f->severity], $f->rule_id])->values();

        return view('cases.show', [
            'case' => $caseFile->load('creator:id,name'),
            'events' => $events,
            'documents' => $documents,
            'findings' => $findings,
            'evaluation' => $evaluation = $caseFile->evaluations()->latest('created_at')->first(),
            // Findings describe the current documents only when the latest run succeeded on them.
            'evaluationCurrent' => EvaluateCase::isCurrent($caseFile, $evaluation),
        ]);
    }

    /**
     * Closing confirms the review. It needs an up-to-date, successful evaluation of every
     * processed document and a valid decision on every current critical finding.
     */
    public function close(CaseFile $caseFile, AuditLog $audit): RedirectResponse
    {
        $error = DB::transaction(function () use ($caseFile, $audit) {
            $case = CaseFile::query()->lockForUpdate()->findOrFail($caseFile->id);
            if ($case->status === 'closed') {
                return null;
            }
            if ($case->documents()->whereIn('status', ['uploaded', 'processing'])->exists()) {
                return __('Cannot close: documents are still being processed.');
            }
            $latest = $case->evaluations()->latest('created_at')->first();
            if ($latest === null || $latest->status !== 'ok' || $latest->input_hash !== EvaluateCase::currentInputHash($case)) {
                return __('Cannot close: the case has not been checked against its current documents. Use "Check again".');
            }
            // Decisions and evaluations lock the case row first, so this count cannot change underneath.
            $undecided = $case->findings()->open()->where('severity', 'critical')->count();
            if ($undecided > 0) {
                return trans_choice('Cannot close: :count critical finding still needs a decision.|Cannot close: :count critical findings still need a decision.', $undecided, ['count' => $undecided]);
            }
            $from = $case->status;
            $case->forceFill(['status' => 'closed'])->save();
            $audit->record('case.status_changed', $case, ['from' => $from, 'to' => 'closed']);

            return null;
        });
        if ($error !== null) {
            return redirect()->route('cases.show', $caseFile)->withErrors(['case' => $error]);
        }

        return redirect()->route('cases.show', $caseFile)->with('status', __('Case closed.'));
    }

    public function reopen(CaseFile $caseFile, AuditLog $audit): RedirectResponse
    {
        if ($caseFile->status === 'closed') {
            DB::transaction(function () use ($caseFile, $audit) {
                $caseFile->forceFill(['status' => 'in_review'])->save();
                $audit->record('case.status_changed', $caseFile, ['from' => 'closed', 'to' => 'in_review']);
            });
        }

        return redirect()->route('cases.show', $caseFile)->with('status', __('Case reopened.'));
    }

    /** Runs the rules again on demand (e.g. after rules were updated). */
    public function evaluate(CaseFile $caseFile): RedirectResponse
    {
        if ($caseFile->status === 'closed') {
            return redirect()->route('cases.show', $caseFile)
                ->withErrors(['case' => __('The case is closed. Reopen it to change decisions.')]);
        }
        EvaluateCase::dispatch($caseFile->organization_id, $caseFile->id, force: true);

        return redirect()->route('cases.show', $caseFile)->with('status', __('Checking the case again.'));
    }
}
