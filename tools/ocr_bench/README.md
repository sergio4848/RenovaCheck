# OCR benchmark

Compares the three OCR adapters of the extract service — Tesseract (`pol`, local), Azure AI
Document Intelligence (`prebuilt-read`) and Google Document AI (Enterprise Document OCR) — on the
same 200 synthetic pages.

```sh
make ocr-bench        # page set (if missing) + benchmark + docs/EVAL_REPORT.md
make eval             # everything, the benchmark included
```

The code lives in the extract service (`services/extract/src/renova_extract/eval/ocr_bench.py`,
`python -m renova_extract.eval ocr-bench`) because it measures the service's own adapters, with the
same rendering and field extractor as production, and is covered by the service's tests and type
checks. This directory documents the method and the page set.

## Page set

`make ocr-bench-data` generates 40 cases with `tools/synth` (seed 7300, separate from the
evaluation set, seed 2026, and the holdout, seed 4242) into `data/ocr_bench/synth`. Whole
documents are taken in sorted order until exactly 200 pages are selected (a document that would
overflow the budget is skipped). Both clean (vector) pages and noisy scans are included; the split
is printed in the report.

Every page is rendered as in the analysis (150 dpi, greyscale) and given to every provider as an
image — clean pages too, so all providers read the same pixels.

## Metrics

| metric | meaning |
|---|---|
| field hit rate | share of ground-truth field texts found in the page's OCR text (whitespace and case normalised), per quality |
| CER / WER | character / word edit distance to the PDF text layer of clean pages, both sides in line order |
| field F1 | the deterministic field extractor (`fields.yaml`) run on each provider's words, scored as in `make eval` |
| time per page | wall time of one recognition call (p50 / p95); cloud times include the network round trip and polling |
| cost per page | list price per 1000 pages for the cloud services; CPU time × assumed vCPU-hour price for Tesseract |

Prices are list prices recorded in `ocr_bench.PRICES` with their source and date („stan na
2026-10, do weryfikacji"); see `docs/ASSUMPTIONS.md` (section I).

## Credentials

Cloud providers run only when their credentials are set in the environment of the `extract`
service (`.env`):

* Azure: `RENOVA_AZURE_DI_ENDPOINT`, `RENOVA_AZURE_DI_KEY`
* Google: `RENOVA_GOOGLE_PROJECT_ID`, `RENOVA_GOOGLE_LOCATION`, `RENOVA_GOOGLE_PROCESSOR_ID`,
  `RENOVA_GOOGLE_ACCESS_TOKEN`

Without them the provider's column reads „uruchomienie pominięte". Only synthetic pages are sent;
the per-organisation consent for external processing (ADR-0009) concerns customer documents in the
application and does not apply to this offline benchmark.
