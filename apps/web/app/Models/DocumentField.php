<?php

namespace App\Models;

use App\Tenancy\BelongsToOrganization;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Support\Str;

/** A field read from a document, with its provenance (page, box, method, confidence). */
class DocumentField extends Model
{
    use BelongsToOrganization, HasUuids;

    protected $fillable = ['document_id', 'name', 'value', 'raw_text', 'page_no', 'bbox', 'method', 'confidence', 'status'];

    protected function casts(): array
    {
        return ['bbox' => 'array', 'confidence' => 'float', 'page_no' => 'integer'];
    }

    /** @return BelongsTo<Document, $this> */
    public function document(): BelongsTo
    {
        return $this->belongsTo(Document::class);
    }

    public function label(): string
    {
        return __('field.'.$this->name);
    }

    /** Whether the comparison form says more than the printed text (not just case or accents). */
    public function showsNormalized(): bool
    {
        $plain = fn (string $text) => Str::lower(Str::ascii(rtrim($text, '.,;: ')));

        return $this->value !== null && $plain($this->value) !== $plain($this->raw_text);
    }

    /** CSS position of the box on its page image, in percent. */
    public function boxStyle(): string
    {
        $b = $this->bbox;

        return sprintf(
            'left:%.3f%%;top:%.3f%%;width:%.3f%%;height:%.3f%%',
            $b['x0'] * 100, $b['y0'] * 100, ($b['x1'] - $b['x0']) * 100, ($b['y1'] - $b['y0']) * 100,
        );
    }
}
