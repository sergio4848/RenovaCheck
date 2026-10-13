<?php

namespace App\Documents;

use App\Jobs\ProcessDocument;
use App\Models\CaseFile;
use App\Models\Document;
use App\Models\User;
use App\Services\Antivirus\InfectedFile;
use App\Services\Antivirus\Scanner;
use App\Services\AuditLog;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

/**
 * Accepts one uploaded file into a case: content-type check, virus scan, de-duplication, private
 * storage, database row and audit event, then queues analysis after the transaction commits.
 */
final class DocumentIntake
{
    public function __construct(private readonly Scanner $scanner, private readonly AuditLog $audit) {}

    public function accept(CaseFile $case, UploadedFile $file, User $user): IntakeResult
    {
        $path = $file->getRealPath();
        $mime = $path === false ? null : FileSniffer::mime($path);
        if ($mime === null) {
            return IntakeResult::rejected($file, 'unsupported_type');
        }
        $sha256 = hash_file('sha256', $path);
        $existing = $case->documents()->where('sha256', $sha256)->first();
        if ($existing !== null) {
            return IntakeResult::duplicate($file, $existing);
        }
        try {
            $scanStatus = $this->scanner->scan($path);
        } catch (InfectedFile) {
            $this->audit->record('document.rejected_infected', $case, ['size_bytes' => $file->getSize()]);

            return IntakeResult::rejected($file, 'infected');
        }

        $document = new Document([
            'case_file_id' => $case->id,
            'original_name' => self::safeName($file->getClientOriginalName()),
            'mime' => $mime,
            'size_bytes' => $file->getSize(),
            'sha256' => $sha256,
            'status' => 'uploaded',
            'scan_status' => $scanStatus,
            'uploaded_by' => $user->getKey(),
        ]);
        $document->id = (string) Str::uuid();
        $document->organization_id = $case->organization_id;
        $document->storage_key = $document->storagePrefix().'original.'.FileSniffer::EXTENSIONS[$mime];

        Storage::disk(config('documents.disk'))->putFileAs(
            dirname($document->storage_key), $file, basename($document->storage_key), ['visibility' => 'private'],
        );

        try {
            $this->persist($document);
        } catch (UniqueConstraintViolationException) {
            // A concurrent upload of the same file won the race: keep its row, drop our copy.
            Storage::disk(config('documents.disk'))->delete($document->storage_key);

            return IntakeResult::duplicate($file, $case->documents()->where('sha256', $sha256)->firstOrFail());
        }

        return IntakeResult::accepted($file, $document);
    }

    private function persist(Document $document): void
    {
        DB::transaction(function () use ($document) {
            $document->save();
            $this->audit->record('document.uploaded', $document, [
                'mime' => $document->mime,
                'size_bytes' => $document->size_bytes,
                'sha256' => $document->sha256,
                'scan_status' => $document->scan_status,
            ]);
            ProcessDocument::dispatch($document->organization_id, $document->id)->afterCommit();
        });
    }

    /** Display name only: path parts and control characters removed, length capped. */
    public static function safeName(string $name): string
    {
        $base = basename(str_replace('\\', '/', $name));
        $clean = preg_replace('/[\x00-\x1F\x7F]+/u', '', $base) ?? '';

        return Str::limit($clean === '' ? 'dokument' : $clean, 200, '');
    }
}
