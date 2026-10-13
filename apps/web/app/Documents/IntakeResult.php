<?php

namespace App\Documents;

use App\Models\Document;
use Illuminate\Http\UploadedFile;

final class IntakeResult
{
    private function __construct(
        public readonly string $outcome,
        public readonly string $fileName,
        public readonly ?Document $document = null,
        public readonly ?string $reason = null,
    ) {}

    public static function accepted(UploadedFile $file, Document $document): self
    {
        return new self('accepted', DocumentIntake::safeName($file->getClientOriginalName()), $document);
    }

    public static function duplicate(UploadedFile $file, Document $existing): self
    {
        return new self('duplicate', DocumentIntake::safeName($file->getClientOriginalName()), $existing);
    }

    public static function rejected(UploadedFile $file, string $reason): self
    {
        return new self('rejected', DocumentIntake::safeName($file->getClientOriginalName()), null, $reason);
    }
}
