<?php

namespace App\Http\Controllers;

use App\Models\CaseFile;
use App\Models\Document;
use App\Models\Finding;
use App\Models\FindingDecision;
use App\Reviews\DecideFinding;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Collection;
use Illuminate\Validation\Rule;
use Illuminate\View\View;

class FindingController extends Controller
{
    public function show(CaseFile $caseFile, Finding $finding): View
    {
        $docIds = collect([...$finding->subject_doc_ids, ...$finding->context_doc_ids, ...array_column($finding->evidence, 'doc_id')])
            ->unique()->values();
        $documents = $caseFile->documents()->with(['pages', 'fields'])->whereIn('id', $docIds)->get()
            ->sortBy(fn (Document $d) => $docIds->search($d->id))->values();

        $sequence = self::reviewOrder($caseFile);
        $position = $sequence->search(fn (Finding $f) => $f->id === $finding->id);

        return view('findings.show', [
            'case' => $caseFile,
            'finding' => $finding,
            'documents' => $documents,
            'evidence' => self::evidence($finding, $documents),
            'decisions' => $finding->decisions()->with('decider:id,name')->get(),
            'previous' => $position !== false && $position > 0 ? $sequence[$position - 1] : null,
            'next' => $position !== false ? $sequence->get($position + 1) : null,
            'position' => $position === false ? null : $position + 1,
            'total' => $sequence->count(),
        ]);
    }

    public function decide(Request $request, CaseFile $caseFile, Finding $finding, DecideFinding $decide): RedirectResponse
    {
        $validated = $request->validate([
            'decision' => ['required', Rule::in(FindingDecision::DECISIONS)],
            'comment' => ['nullable', 'string', 'max:2000'],
        ]);
        $decide($finding, $validated['decision'], $validated['comment'] ?? null, $request->user());

        $next = self::reviewOrder($caseFile)->first(fn (Finding $f) => $f->isOpen() && $f->id !== $finding->id);

        return redirect()
            ->route('findings.show', [$caseFile, $next ?? $finding])
            ->with('status', __('Decision saved.'));
    }

    /** Current findings in review order: severity, then rule. */
    public static function reviewOrder(CaseFile $case): Collection
    {
        return $case->findings()->current()->get()
            ->sortBy(fn (Finding $f) => [Finding::SEVERITY_ORDER[$f->severity], $f->rule_id, $f->created_at])
            ->values();
    }

    /**
     * Evidence rows joined with where each value was read (page and box).
     *
     * @param  Collection<int, Document>  $documents
     * @return list<array<string, mixed>>
     */
    private static function evidence(Finding $finding, Collection $documents): array
    {
        $byId = $documents->keyBy('id');
        $rows = [];
        foreach ($finding->evidence as $item) {
            $document = $byId->get($item['doc_id']);
            $field = $document?->fields->firstWhere('name', $item['field']);
            $rows[] = [
                'document' => $document,
                'field' => $item['field'],
                'value' => $item['value'],
                'text' => $item['text'],
                'source' => $field,
                'subject' => in_array($item['doc_id'], $finding->subject_doc_ids, true),
                'key' => substr(md5($item['doc_id'].'|'.$item['field']), 0, 12),
            ];
        }

        return $rows;
    }
}
