<?php

namespace App\Documents;

use App\Models\Document;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;

/** Calls the extraction service; the service reads the file through a short-lived signed URL. */
final class ExtractClient
{
    /**
     * @return array<string, mixed>
     *
     * @throws ExtractFailed
     */
    public function analyze(Document $document): array
    {
        $sourceUrl = Storage::disk(config('documents.disk'))
            ->temporaryUrl($document->storage_key, now()->addMinutes(config('documents.extract_url_minutes')));

        try {
            $response = Http::baseUrl((string) config('services.extract.url'))
                ->withToken((string) config('services.extract.token'))
                ->acceptJson()
                ->timeout((int) config('services.extract.timeout'))
                ->post('/v1/documents/analyze', [
                    'document_id' => $document->id,
                    'source_url' => $sourceUrl,
                    'output_prefix' => $document->storagePrefix(),
                    // A type set by a person decides which fields are read.
                    'doc_type' => $document->doc_type_source === 'user' ? $document->doc_type?->value : null,
                ]);
        } catch (ConnectionException $e) {
            throw new ExtractFailed('extract_unreachable', retryable: true, previous: $e);
        }

        if ($response->successful()) {
            return AnalysisResult::parse($response->json(), $document);
        }
        $code = (string) ($response->json('error.code') ?? 'extract_error');

        // 4xx: the document itself is the problem; retrying will not help.
        throw new ExtractFailed($code, retryable: $response->serverError());
    }
}
