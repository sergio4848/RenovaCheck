# ADR-0007: Deterministic field extraction with provenance

* Status: Accepted · 2026-10-14

## Context

The rule engine (phase 5) compares fields across the documents of a case: address, investor,
contractor, product, amounts, dates, signatures. A reviewer must see where each value came from,
and a value that cannot be read must never be guessed. Documents vary in layout (two-column vs
stacked blocks, different labels, money formats `1 234,56 zł` / `1234,56 PLN` / `1.234,56 zł`,
dates `05.06.2026` / `2026-06-05`, street spellings with and without the patron's first name).

## Decision

* **Field dictionary** `packages/rules/fields.yaml` (v2) names every field, its type, the document
  types it is read from, and an ordered list of extraction methods with anchors. Anchors are
  compared after folding (lower case, no diacritics); longer anchors win.
* **Layout model:** words with boxes (text layer or OCR) are grouped into lines and column
  segments (a gap wider than ~1.6 word heights splits a line). Methods: `label` (anchor, value in
  the rest of the line), `block` (heading segment, value below it in the same column), `above`,
  `title_number`, `address` (one segment `<street> <no>, <postal> <city>`), `signature` (ink above
  the caption, measured on the page image). A label at the end of a skewed scan line continues on
  the neighbouring line at the same height.
* **Normalization** per type, idempotent, so ground truth and extracted text compare with the same
  code: money → exact decimal string, dates → ISO, power → decimal kW, NIP → digits, street → name
  without prefix (`ul.`, `al.`, …) and patron first name/initial, model → upper case without
  dashes/spaces, names/towns → folded.
* **Provenance:** every field carries `{value, text, doc_id, page, bbox, method, confidence,
  status}`; the box is cut to the characters of the value, also inside a word. Confidence is the
  method weight × the lowest OCR word confidence. `unreadable` (no value, confidence 0) is
  produced only when a real label (a phrase or a word ending in `:`) is followed by text that does
  not parse; a missing field is simply absent.
* **Type decides the fields:** the classifier's type, or the type a person set (sent as
  `doc_type`; correcting the type re-runs the analysis).
* **LLM helper (optional, off by default):** for fields still missing, a model may propose text
  spans (temperature 0, JSON validated against a schema). A proposal is kept only if the field was
  requested, the text occurs verbatim on the named page and parses as the field's type; its
  confidence is capped at 0.5 and its method is `llm`. Failures never fail an analysis.
* **OCR adapters:** Tesseract (pol) locally; Azure Document Intelligence `prebuilt-read` (Poland
  Central endpoint, operation URL must stay on the endpoint host) and Google Document AI, selected
  with `RENOVA_OCR_PROVIDER`.
* **Storage (web):** `document_fields` under RLS with a composite tenant key; rows are replaced as
  a whole on reprocessing; the web app validates the whole field list (known names, boxes in
  `[0, 1]`, page within the document, value iff `ok`) before storing anything.

## Consequences

* `make eval` reports precision/recall and box hit rate per field for clean PDFs (threshold 95 %)
  and scans (reported, no threshold), from the same normalizers the product uses.
* New document layouts mostly need anchors in `fields.yaml`, not code.
* Anchor-based extraction is tuned on two synthetic template families; real documents will need
  more anchors and a measured second round (TRL 4).
