<?php

namespace App\Models;

use App\Tenancy\BelongsToOrganization;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class DocumentPage extends Model
{
    use BelongsToOrganization, HasUuids;

    protected $fillable = [
        'document_id', 'page_no', 'width_pt', 'height_pt', 'image_key', 'image_width_px', 'image_height_px',
        'text_source', 'word_count',
    ];

    protected function casts(): array
    {
        return ['width_pt' => 'float', 'height_pt' => 'float', 'page_no' => 'integer', 'word_count' => 'integer'];
    }

    /** @return BelongsTo<Document, $this> */
    public function document(): BelongsTo
    {
        return $this->belongsTo(Document::class);
    }
}
