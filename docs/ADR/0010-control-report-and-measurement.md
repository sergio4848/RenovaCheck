# ADR-0010: Control report export and reproducible measurement

* Status: Accepted · 2026-10-14

## Context

A reviewed case must leave the system as a document that someone else (the firm's quality lead, an
auditor of the grant file) can read without access to RenovaCheck: what was checked, what was
found, who decided what and when, and what is still open. Separately, the quality of the prototype
must be measurable with one command so that every change to extraction, rules or OCR shows its
effect, and the choice between local and cloud OCR rests on numbers, including cost.

## Decision

### Control report (PDF and CSV)

* `GET /cases/{case}/report.pdf` and `/report.csv`, permission `cases.view`, tenant-scoped like
  every case route (RLS + route binding; another organisation's case is a 404), rate limited
  (`reports`: 10/min per user, 30/min per organisation) and audited as `case.report_exported`
  with the format, counts and the state fingerprint.
* `App\Reports\CaseReport` reads one consistent snapshot: it takes a shared lock on the case row,
  which decisions, evaluations and closing lock for update, so a report never mixes the state
  before and after one of them.
* Current findings are split into three sections: **niezatwierdzone** (critical and not decided,
  or decided on values that changed since), **rozstrzygnięte** and **pozostałe otwarte**
  (warning/info without a decision). The full append-only decision history follows (who, when,
  decision, comment, evidence hash), including decisions on findings no longer reported.
* The report states whether the latest evaluation is current (same input hash as the documents
  now, see ADR-0009); an outdated or failed evaluation is flagged at the top, not hidden.
* A **state fingerprint** (SHA-256 of findings, their review state, decision ids and the
  evaluation) is printed and audited: two reports with the same fingerprint describe the same
  review regardless of when or by whom they were generated.
* CSV is written for Polish spreadsheets (UTF-8 BOM, `;`, CRLF). All cells are case data
  (file names, comments), so cells starting with `= + - @ TAB CR` get a leading apostrophe
  (CSV/formula injection).
* PDF is rendered with dompdf (`barryvdh/laravel-dompdf`, LGPL-2.1) from a Blade view that only
  contains escaped text: remote resources, PHP and JavaScript are disabled and the chroot is the
  report view directory. The view's inline stylesheet never reaches a browser, so the CSP of
  ADR-0009 is unaffected. Times are shown in Europe/Warsaw.

### Measurement (`make eval` → `docs/EVAL_REPORT.md`)

* The eval tasks keep writing raw results to `data/eval/*.json`, now with per-document latency
  (p50/p95/max per quality) and rule-engine time per case, plus `summary.json` (dataset, ruleset
  digest, thresholds and their result, task wall times).
* `renova_extract.eval.report.render` turns those files into Markdown; `make eval` runs the
  evaluation and the OCR benchmark and writes `docs/EVAL_REPORT.md` in one command. The report is
  committed, so a diff shows how a change moved the numbers. It is written even when a threshold
  fails (the command still exits non-zero).

### OCR benchmark

* Same pixels for every provider: 200 pages of whole documents from a separate synthetic set
  (40 cases, seed 7300), rendered as in production (150 dpi), also pages that have a text layer.
* Metrics: field-text hit rate (clean/scan), CER/WER against the text layer of clean pages (both
  in line order, so reading-order differences of a provider do not count as errors), field F1 of
  the production extractor on the provider's words, time per page, cost per page.
* Cost: list prices per 1000 pages for Azure (prebuilt-read) and Google (Enterprise Document OCR),
  recorded with source and date in the code; for Tesseract measured CPU time × an assumed vCPU-hour
  price (ASSUMPTIONS I).
* Cloud providers run only with credentials in the environment; otherwise their column says
  „uruchomienie pominięte". Only synthetic pages are sent.
* The benchmark lives in the extract service (`renova_extract.eval.ocr_bench`), not as a separate
  package in `tools/ocr_bench`, because it must use the service's own adapters, rendering and
  extractor; `tools/ocr_bench/README.md` documents the method.

## Consequences

* Reports are generated on request and not stored; the audit event with the fingerprint records
  that a given state was exported. Storing signed report files is left for TRL 4.
* dompdf adds a PDF renderer with its own parser to the web image. Its input is a template we
  control with escaped data only, and every loading feature is off.
* `docs/EVAL_REPORT.md` contains timings and a date, so regenerating it always changes the file;
  the measured values only change when the system does.
* Cloud OCR numbers in the committed report are absent until someone runs the benchmark with
  credentials; the cost table still shows list prices for comparison.
