<?php

namespace App\Rules;

use App\Documents\ExtractFailed;
use App\Models\CaseFile;
use Illuminate\Support\Facades\Validator;

/**
 * Parses the rule engine's response at the boundary. Findings may only point at documents and
 * fields of this case; anything unexpected rejects the whole result.
 */
final class EvaluationResult
{
    public const FAMILIES = ['address', 'product', 'amount', 'completeness', 'quality'];

    public const OUTCOMES = [
        'discrepancy', 'match_after_normalization', 'agreed_change', 'explained_by_advance',
        'explained_by_correction', 'missing_document', 'unreadable_source', 'no_rules',
    ];

    /**
     * @param  list<string>  $documentIds
     * @return array<string, mixed>
     *
     * @throws ExtractFailed
     */
    public static function parse(mixed $body, CaseFile $case, array $documentIds): array
    {
        $docs = 'in:'.implode(',', $documentIds ?: ['-']);
        $fields = 'in:'.implode(',', config('documents.fields'));
        $validator = Validator::make(is_array($body) ? $body : [], [
            'case_id' => ['required', 'in:'.$case->id],
            'reference_date' => ['required', 'date_format:Y-m-d'],
            'reference_source' => ['required', 'in:application_date,contract_date,fallback'],
            'ruleset' => ['present', 'array', 'max:200'],
            'ruleset.*.id' => ['required', 'string', 'regex:/^[A-Z]{3}-\d{2}$/'],
            'ruleset.*.version' => ['required', 'integer', 'min:1'],
            'findings' => ['present', 'array', 'max:500'],
            'findings.*.rule_id' => ['required', 'string', 'regex:/^([A-Z]{3}-\d{2}|SYS-00)$/'],
            'findings.*.rule_version' => ['required', 'integer', 'min:0'],
            'findings.*.family' => ['required', 'in:'.implode(',', self::FAMILIES)],
            'findings.*.outcome' => ['required', 'in:'.implode(',', self::OUTCOMES)],
            'findings.*.severity' => ['required', 'in:critical,warning,info'],
            'findings.*.title_pl' => ['required', 'string', 'max:200'],
            'findings.*.reason_pl' => ['required', 'string', 'max:2000'],
            'findings.*.subject_doc_ids' => ['present', 'array', 'max:50'],
            'findings.*.subject_doc_ids.*' => ['string', $docs],
            'findings.*.context_doc_ids' => ['present', 'array', 'max:50'],
            'findings.*.context_doc_ids.*' => ['string', $docs],
            'findings.*.fields' => ['present', 'array', 'max:30'],
            'findings.*.fields.*' => ['string', $fields],
            'findings.*.evidence' => ['present', 'array', 'max:300'],
            'findings.*.evidence.*.doc_id' => ['required', 'string', $docs],
            'findings.*.evidence.*.field' => ['required', 'string', $fields],
            'findings.*.evidence.*.value' => ['present', 'nullable', 'string', 'max:500'],
            'findings.*.evidence.*.text' => ['present', 'nullable', 'string', 'max:500'],
            'findings.*.fingerprint' => ['required', 'string', 'distinct', 'regex:/^[0-9a-f]{64}$/'],
            'findings.*.evidence_hash' => ['required', 'string', 'regex:/^[0-9a-f]{64}$/'],
            'findings.*.status' => ['required', 'in:do_sprawdzenia'],
        ]);
        if ($validator->fails()) {
            throw new ExtractFailed('invalid_rules_response', retryable: false);
        }

        return $validator->validated();
    }
}
