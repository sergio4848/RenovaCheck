<?php

namespace App\Documents;

use App\Enums\DocType;
use App\Models\Document;
use Illuminate\Support\Facades\Validator;

/**
 * Parses the extraction service's response at the boundary. Anything unexpected is rejected as a
 * whole, so the job never stores a partially valid result.
 */
final class AnalysisResult
{
    /**
     * @return array<string, mixed>
     *
     * @throws ExtractFailed
     */
    public static function parse(mixed $body, Document $document): array
    {
        $prefix = preg_quote($document->storagePrefix(), '/');
        $validator = Validator::make(is_array($body) ? $body : [], [
            'document_id' => ['required', 'in:'.$document->id],
            'mime' => ['required', 'in:'.$document->mime],
            'page_count' => ['required', 'integer', 'min:1', 'max:500'],
            'pages' => ['required', 'array', 'size:'.(is_array($body) ? (int) ($body['page_count'] ?? -1) : -1)],
            'pages.*.page_no' => ['required', 'integer', 'min:1', 'distinct'],
            'pages.*.width_pt' => ['required', 'numeric', 'min:1', 'max:20000'],
            'pages.*.height_pt' => ['required', 'numeric', 'min:1', 'max:20000'],
            'pages.*.image_key' => ['required', 'string', 'max:255', "regex:/^{$prefix}pages\/\d{3}\.png$/"],
            'pages.*.image_width_px' => ['required', 'integer', 'min:1'],
            'pages.*.image_height_px' => ['required', 'integer', 'min:1'],
            'pages.*.text_source' => ['required', 'in:text_layer,ocr,none'],
            'pages.*.word_count' => ['required', 'integer', 'min:0'],
            'classification' => ['required', 'array'],
            'classification.doc_type' => ['nullable', 'in:'.implode(',', array_column(DocType::cases(), 'value'))],
            'classification.confidence' => ['required', 'numeric', 'between:0,1'],
            'classification.scores' => ['present', 'array'],
            'classification.evidence' => ['present', 'array'],
            'ocr_provider' => ['required', 'string', 'max:32'],
            'fields' => ['present', 'array', 'max:200'],
            'fields.*.name' => ['required', 'string', 'distinct', 'in:'.implode(',', config('documents.fields'))],
            'fields.*.value' => ['nullable', self::scalarValue(...)],
            'fields.*.text' => ['present', 'nullable', 'string', 'max:500'],
            'fields.*.doc_id' => ['required', 'in:'.$document->id],
            'fields.*.page' => ['required', 'integer', 'min:1', 'max:'.(is_array($body) ? (int) ($body['page_count'] ?? 0) : 0)],
            'fields.*.bbox' => ['required', 'array:x0,y0,x1,y1'],
            'fields.*.bbox.*' => ['required', 'numeric', 'between:0,1'],
            'fields.*.method' => ['required', 'in:'.implode(',', config('documents.field_methods'))],
            'fields.*.confidence' => ['required', 'numeric', 'between:0,1'],
            'fields.*.status' => ['required', 'in:ok,unreadable'],
            'extraction' => ['required', 'array'],
            'extraction.dictionary_version' => ['required', 'integer', 'min:1'],
            'extraction.doc_type' => ['nullable', 'in:'.implode(',', array_column(DocType::cases(), 'value'))],
            'extraction.llm_provider' => ['nullable', 'string', 'max:32'],
        ]);
        if ($validator->fails()) {
            throw new ExtractFailed('invalid_extract_response', retryable: false);
        }

        $validated = $validator->validated();
        foreach ($validated['fields'] as $field) {
            // A readable field has a value; an unreadable one has none.
            if (($field['status'] === 'ok') === (($field['value'] ?? null) === null)) {
                throw new ExtractFailed('invalid_extract_response', retryable: false);
            }
        }

        return $validated;
    }

    /** Field values are strings (normalized form) or booleans (signatures). */
    private static function scalarValue(string $attribute, mixed $value, \Closure $fail): void
    {
        if (! is_bool($value) && ! (is_string($value) && mb_strlen($value) <= 500)) {
            $fail('invalid');
        }
    }
}
