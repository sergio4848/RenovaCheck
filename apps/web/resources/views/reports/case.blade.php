{{-- Rendered by dompdf only (never served to a browser), so the stylesheet is inline. --}}
@php($fmt = fn ($t) => \App\Reports\CaseReport::local($t))
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="utf-8">
    <title>{{ __('report.title') }} {{ $report->case->reference }}</title>
    <style>
        @page { margin: 22mm 14mm 18mm 14mm; }
        body { font-family: "DejaVu Sans", sans-serif; font-size: 8.5pt; color: #1d273b; }
        h1 { font-size: 15pt; margin: 0 0 2mm; }
        h2 { font-size: 11pt; margin: 6mm 0 2mm; padding-bottom: 1mm; border-bottom: 0.4pt solid #9aa0ac; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; vertical-align: top; padding: 1.2mm 1.5mm; border-bottom: 0.3pt solid #dadfe5; }
        th { background: #f1f3f6; font-size: 7.5pt; }
        .meta td { border: none; padding: 0.6mm 1.5mm 0.6mm 0; }
        .meta td.k { width: 32mm; color: #667382; }
        .muted { color: #667382; }
        .alert { border: 0.6pt solid #d63939; background: #fbebeb; padding: 2mm; margin: 3mm 0; }
        .alert-ok { border-color: #2fb344; background: #eaf7ec; }
        .sev { font-weight: bold; }
        .sev-critical { color: #d63939; }
        .sev-warning { color: #c27a00; }
        .sev-info { color: #4263eb; }
        .section-unapproved h2 { color: #d63939; border-bottom-color: #d63939; }
        .reason { margin-top: 0.8mm; }
        .nowrap { white-space: nowrap; }
        footer { position: fixed; bottom: -12mm; left: 0; right: 0; font-size: 7pt; color: #667382; }
        footer .pages:after { content: counter(page) " / " counter(pages); }
    </style>
</head>
<body>
<footer>
    <table><tr>
        <td style="border:none">{{ __('report.disclaimer') }}<br>{{ __('report.fingerprint') }}: {{ $report->fingerprint() }}</td>
        <td style="border:none; text-align:right" class="nowrap pages"></td>
    </tr></table>
</footer>

<h1>{{ __('report.title') }}</h1>
<table class="meta">
    <tr><td class="k">{{ __('Reference') }}</td><td>{{ $report->case->reference }}</td></tr>
    <tr><td class="k">{{ __('Title') }}</td><td>{{ $report->case->title }}</td></tr>
    <tr><td class="k">{{ __('Status') }}</td><td>{{ __('status.'.$report->case->status) }}</td></tr>
    <tr><td class="k">{{ __('Created by') }}</td><td>{{ $report->case->creator?->name ?? '—' }}, {{ $fmt($report->case->created_at) }}</td></tr>
    <tr><td class="k">{{ __('report.generated') }}</td><td>{{ $fmt($report->generatedAt) }} · {{ $report->generatedBy->name }}</td></tr>
    <tr><td class="k">{{ __('report.evaluation') }}</td><td>{{ \App\Reports\CaseReportCsv::evaluationNote($report) }}</td></tr>
</table>

@if (! $report->evaluationCurrent)
    <div class="alert">{{ __('report.outdated_warning') }}</div>
@endif
<div class="alert {{ $report->unapprovedCount() === 0 ? 'alert-ok' : '' }}">
    {{ trans_choice('report.summary', $report->findingsCount(), ['count' => $report->findingsCount(), 'unapproved' => $report->unapprovedCount(), 'decided' => $report->sections['rozstrzygniete']->count(), 'open' => $report->sections['pozostale_otwarte']->count()]) }}
</div>

@foreach ($report->sections as $section => $findings)
    <div class="{{ $section === 'niezatwierdzone' ? 'section-unapproved' : '' }}">
        <h2>{{ __('report.section.'.$section) }} ({{ $findings->count() }})</h2>
        @if ($findings->isEmpty())
            <p class="muted">{{ __('report.section_empty') }}</p>
        @else
            <table>
                <thead><tr>
                    <th style="width:18mm">{{ __('report.col.rule') }}</th>
                    <th>{{ __('report.col.title') }} / {{ __('report.col.reason') }}</th>
                    <th style="width:34mm">{{ __('report.col.documents') }}</th>
                    <th style="width:40mm">{{ __('report.col.decision') }}</th>
                </tr></thead>
                <tbody>
                @foreach ($findings as $finding)
                    <tr>
                        <td class="nowrap">{{ $finding->rule_id }} v{{ $finding->rule_version }}<br>
                            <span class="sev sev-{{ $finding->severity }}">{{ __('severity.'.$finding->severity) }}</span></td>
                        <td><strong>{{ $finding->title_pl }}</strong><div class="reason">{{ $finding->reason_pl }}</div></td>
                        <td>{{ $report->documentNames([...($finding->subject_doc_ids ?? []), ...($finding->context_doc_ids ?? [])]) }}</td>
                        <td>
                            @if ($finding->decision)
                                {{ __('decision.'.$finding->decision) }}<br>
                                <span class="muted">{{ $finding->decider?->name ?? '—' }}, {{ $fmt($finding->decided_at) }}</span>
                            @endif
                            <div class="muted">{{ __('review_status.'.$finding->review_status) }}</div>
                        </td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        @endif
    </div>
@endforeach

<h2>{{ __('report.history') }} ({{ $report->decisions->count() }})</h2>
@if ($report->decisions->isEmpty())
    <p class="muted">{{ __('report.history_empty') }}</p>
@else
    <table>
        <thead><tr>
            <th style="width:24mm">{{ __('report.col.decided_at') }}</th>
            <th style="width:28mm">{{ __('report.col.decided_by') }}</th>
            <th>{{ __('report.col.rule') }} · {{ __('report.col.title') }}</th>
            <th style="width:26mm">{{ __('report.col.decision') }}</th>
            <th>{{ __('report.col.comment') }}</th>
        </tr></thead>
        <tbody>
        @foreach ($report->decisions as $decision)
            <tr>
                <td class="nowrap">{{ $fmt($decision->created_at) }}</td>
                <td>{{ $decision->decider?->name ?? '—' }}</td>
                <td>{{ $decision->rule_id }} v{{ $decision->rule_version }} · {{ $decision->finding_title }}@if (! $decision->finding_is_current) <span class="muted">({{ __('report.no_longer_reported') }})</span>@endif</td>
                <td>{{ __('decision.'.$decision->decision) }}</td>
                <td>{{ $decision->comment }}</td>
            </tr>
        @endforeach
        </tbody>
    </table>
@endif

<h2>{{ __('Documents') }} ({{ $report->documents->count() }})</h2>
<table>
    <thead><tr><th>{{ __('report.col.file') }}</th><th style="width:40mm">{{ __('report.col.type') }}</th><th style="width:22mm">{{ __('Status') }}</th><th style="width:14mm">{{ __('report.col.pages') }}</th></tr></thead>
    <tbody>
    @foreach ($report->documents as $document)
        <tr>
            <td>{{ $document->original_name }}</td>
            <td>{{ $document->doc_type?->label() ?? '—' }}</td>
            <td>{{ __('doc_status.'.$document->status) }}</td>
            <td>{{ $document->pages_count }}</td>
        </tr>
    @endforeach
    </tbody>
</table>
</body>
</html>
