<?php

namespace App\Http\Controllers;

use App\Models\CaseFile;
use App\Reports\CaseReport;
use App\Reports\CaseReportCsv;
use App\Services\AuditLog;
use Barryvdh\DomPDF\Facade\Pdf;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\StreamedResponse;

class CaseReportController extends Controller
{
    public function csv(Request $request, CaseFile $caseFile, AuditLog $audit): StreamedResponse
    {
        $report = $this->build($request, $caseFile, 'csv', $audit);

        return response()->streamDownload(function () use ($report) {
            foreach (CaseReportCsv::lines($report) as $line) {
                echo $line;
            }
        }, $report->fileName('csv'), ['Content-Type' => 'text/csv; charset=UTF-8']);
    }

    public function pdf(Request $request, CaseFile $caseFile, AuditLog $audit): Response
    {
        $report = $this->build($request, $caseFile, 'pdf', $audit);
        $pdf = Pdf::loadView('reports.case', ['report' => $report])->setPaper('a4');
        $pdf->render();
        // Page numbers are drawn on the canvas: dompdf's CSS has no total page counter.
        $dompdf = $pdf->getDomPDF();
        $canvas = $dompdf->getCanvas();
        $font = $dompdf->getFontMetrics()->getFont('DejaVu Sans');
        $canvas->page_text($canvas->get_width() - 70, $canvas->get_height() - 34, '{PAGE_NUM} / {PAGE_COUNT}', $font, 7, [0.4, 0.45, 0.51]);

        return $pdf->download($report->fileName('pdf'));
    }

    private function build(Request $request, CaseFile $caseFile, string $format, AuditLog $audit): CaseReport
    {
        $report = CaseReport::build($caseFile, $request->user());
        $audit->record('case.report_exported', $report->case, [
            'format' => $format,
            'findings' => $report->findingsCount(),
            'unapproved' => $report->unapprovedCount(),
            'fingerprint' => $report->fingerprint(),
        ]);

        return $report;
    }
}
