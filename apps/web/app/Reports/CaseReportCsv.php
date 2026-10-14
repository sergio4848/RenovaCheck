<?php

namespace App\Reports;

use App\Models\Finding;
use App\Models\FindingDecision;

/**
 * CSV for spreadsheets set to Polish: UTF-8 with BOM, ";" separators, CRLF. Every cell is text
 * from the case (names, comments, reasons), so cells that a spreadsheet would run as a formula are
 * prefixed with an apostrophe.
 */
final class CaseReportCsv
{
    private const FORMULA_START = ['=', '+', '-', '@', "\t", "\r"];

    /** @return iterable<string> */
    public static function lines(CaseReport $report): iterable
    {
        yield "\u{FEFF}".self::row([__('report.title'), $report->case->reference, $report->case->title]);
        yield self::row([__('report.generated'), CaseReport::local($report->generatedAt), $report->generatedBy->name]);
        yield self::row([__('report.evaluation'), self::evaluationNote($report)]);
        yield self::row([__('report.fingerprint'), $report->fingerprint()]);
        yield self::row([]);

        yield self::row([
            __('report.col.section'), __('report.col.rule'), __('report.col.severity'), __('report.col.family'),
            __('report.col.title'), __('report.col.reason'), __('report.col.documents'), __('report.col.review_status'),
            __('report.col.decision'), __('report.col.decided_by'), __('report.col.decided_at'), __('report.col.first_seen'),
        ]);
        foreach ($report->sections as $section => $findings) {
            foreach ($findings as $finding) {
                /** @var Finding $finding */
                yield self::row([
                    __('report.section.'.$section),
                    $finding->rule_id.' v'.$finding->rule_version,
                    __('severity.'.$finding->severity),
                    __('family.'.$finding->family),
                    $finding->title_pl,
                    $finding->reason_pl,
                    $report->documentNames([...($finding->subject_doc_ids ?? []), ...($finding->context_doc_ids ?? [])]),
                    __('review_status.'.$finding->review_status),
                    $finding->decision ? __('decision.'.$finding->decision) : '',
                    $finding->decider?->name ?? '',
                    CaseReport::local($finding->decided_at),
                    CaseReport::local($finding->first_seen_at),
                ]);
            }
        }
        yield self::row([]);

        yield self::row([__('report.history')]);
        yield self::row([
            __('report.col.decided_at'), __('report.col.decided_by'), __('report.col.rule'), __('report.col.title'),
            __('report.col.decision'), __('report.col.comment'), __('report.col.evidence'),
        ]);
        foreach ($report->decisions as $decision) {
            /** @var FindingDecision $decision */
            yield self::row([
                CaseReport::local($decision->created_at),
                $decision->decider?->name ?? '',
                $decision->rule_id.' v'.$decision->rule_version,
                $decision->finding_title,
                __('decision.'.$decision->decision),
                (string) $decision->comment,
                substr((string) $decision->evidence_hash, 0, 12),
            ]);
        }
    }

    public static function evaluationNote(CaseReport $report): string
    {
        $evaluation = $report->evaluation;
        if ($evaluation === null) {
            return __('report.evaluation_none');
        }
        if ($evaluation->status !== 'ok') {
            return __('report.evaluation_failed', ['when' => CaseReport::local($evaluation->created_at)]);
        }
        $note = __('report.evaluation_ok', [
            'when' => CaseReport::local($evaluation->created_at),
            'date' => $evaluation->reference_date?->format('d.m.Y') ?? '',
            'ruleset' => implode(', ', array_map(fn ($r) => $r['id'].'@'.$r['version'], $evaluation->ruleset ?? [])),
        ]);

        return $report->evaluationCurrent ? $note : __('report.evaluation_outdated').' '.$note;
    }

    /** @param  list<string|null>  $cells */
    public static function row(array $cells): string
    {
        return implode(';', array_map(fn ($cell) => self::cell((string) $cell), $cells))."\r\n";
    }

    public static function cell(string $value): string
    {
        if ($value !== '' && in_array($value[0], self::FORMULA_START, true)) {
            $value = "'".$value;
        }
        if (strpbrk($value, ";\"\r\n") !== false) {
            $value = '"'.str_replace('"', '""', $value).'"';
        }

        return $value;
    }
}
