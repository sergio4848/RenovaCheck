<?php

namespace App\Http\Controllers;

use App\Documents\DocumentIntake;
use App\Documents\FileSniffer;
use App\Enums\DocType;
use App\Http\Requests\StoreDocumentsRequest;
use App\Models\CaseFile;
use App\Models\Document;
use App\Services\AuditLog;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

class DocumentController extends Controller
{
    public function store(StoreDocumentsRequest $request, CaseFile $caseFile, DocumentIntake $intake): RedirectResponse
    {
        $results = [];
        foreach ($request->file('files') as $file) {
            $results[] = $intake->accept($caseFile, $file, $request->user());
        }
        $messages = array_map(fn ($r) => __('upload.'.$r->outcome.($r->reason ? '.'.$r->reason : ''), [
            'name' => $r->fileName,
        ]), $results);

        return redirect()->route('cases.show', $caseFile)->with('upload_results', $messages);
    }

    public function updateType(Request $request, CaseFile $caseFile, Document $document, AuditLog $audit): RedirectResponse
    {
        $validated = $request->validate(['doc_type' => ['required', Rule::enum(DocType::class)]]);
        $previous = $document->doc_type?->value;

        DB::transaction(function () use ($document, $validated, $previous, $audit) {
            $document->forceFill([
                'doc_type' => DocType::from($validated['doc_type']),
                'doc_type_source' => 'user',
                'doc_type_confidence' => null,
            ])->save();
            $audit->record('document.type_corrected', $document, [
                'from' => $previous,
                'to' => $validated['doc_type'],
                'classifier' => $document->classification['doc_type'] ?? null,
            ]);
        });

        return redirect()->route('cases.show', $caseFile)->with('status', __('Document type updated.'));
    }

    public function page(CaseFile $caseFile, Document $document, int $pageNo): RedirectResponse
    {
        $page = $document->pages()->where('page_no', $pageNo)->firstOrFail();

        return redirect()->away($this->signedUrl($page->image_key, ['ResponseContentType' => 'image/png']));
    }

    public function download(CaseFile $caseFile, Document $document, AuditLog $audit): RedirectResponse
    {
        $audit->record('document.downloaded', $document);

        return redirect()->away($this->signedUrl($document->storage_key, [
            'ResponseContentType' => $document->mime,
            'ResponseContentDisposition' => 'attachment; filename="'.self::downloadName($document).'"',
        ]));
    }

    /**
     * The client-supplied name is untrusted: keep a plain ASCII stem and take the extension from
     * the sniffed type, so the header cannot be broken and the saved file opens as what it is.
     */
    public static function downloadName(Document $document): string
    {
        $stem = Str::of(pathinfo($document->original_name, PATHINFO_FILENAME))
            ->ascii()
            ->replaceMatches('/[^A-Za-z0-9._ -]+/', '_')
            ->trim(' ._-')
            ->limit(100, '')
            ->toString();

        return ($stem !== '' ? $stem : 'document').'.'.FileSniffer::EXTENSIONS[$document->mime];
    }

    /** @param  array<string, string>  $options */
    private function signedUrl(string $key, array $options): string
    {
        return Storage::disk(config('documents.public_disk'))
            ->temporaryUrl($key, now()->addMinutes(config('documents.browser_url_minutes')), $options);
    }
}
