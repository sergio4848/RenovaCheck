<?php

namespace App\Models;

use App\Enums\DocType;
use App\Tenancy\BelongsToOrganization;
use Database\Factories\DocumentFactory;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Document extends Model
{
    /** @use HasFactory<DocumentFactory> */
    use BelongsToOrganization, HasFactory, HasUuids;

    public const STATUSES = ['uploaded', 'processing', 'processed', 'failed'];

    protected $fillable = [
        'case_file_id', 'original_name', 'mime', 'size_bytes', 'sha256', 'storage_key', 'status',
        'scan_status', 'uploaded_by',
    ];

    protected function casts(): array
    {
        return [
            'doc_type' => DocType::class,
            'doc_type_confidence' => 'float',
            'classification' => 'array',
            'processed_at' => 'immutable_datetime',
            'size_bytes' => 'integer',
            'page_count' => 'integer',
        ];
    }

    /** @return BelongsTo<CaseFile, $this> */
    public function caseFile(): BelongsTo
    {
        return $this->belongsTo(CaseFile::class);
    }

    /** @return HasMany<DocumentPage, $this> */
    public function pages(): HasMany
    {
        return $this->hasMany(DocumentPage::class)->orderBy('page_no');
    }

    /** Prefix under which the extraction service writes derived files (page images). */
    public function storagePrefix(): string
    {
        return sprintf('org/%s/cases/%s/documents/%s/', $this->organization_id, $this->case_file_id, $this->id);
    }
}
