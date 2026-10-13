# ADR-0008: Deterministic rule engine with dated, versioned rules

* Status: Accepted · 2026-10-14

## Context

Fields read from a case's documents (ADR-0007) must be checked against each other: address and
parties, device, amounts (net/gross, advance, correction), missing documents, dates and
signatures. The checks must be explainable, reproducible, tied to the programme rules in force
for the case, and they never decide a case: a person does (phase 6).

## Decision

* **Rules are data.** One YAML file per published version, `packages/rules/rules/<ID>@<v>.yaml`,
  with `id, version, title_pl, program, edition, family, valid_from, valid_to, severity, inputs,
  comparator, threshold, emits, source_url, notes`. `threshold` holds the comparator's typed
  parameters. The JSON Schema `packages/rules/schema/rule.schema.json` is generated from the
  pydantic model and checked in tests; `rules.lock.json` stores each version's content hash, so
  a published version cannot change: a change is a new version with its own regression fixture
  (`services/extract/tests/fixtures/rules/<ID>@<v>.json`).
* **Selection by date:** the reference date is the application date (wniosek), else the contract
  date, else the case's creation date sent by the web app; the highest version valid on that
  date runs. No valid rule produces a `no_rules` finding, never silence.
* **Comparators (Python, deterministic):** majority vote per field (a deviating document is the
  subject; no strict majority yields one finding without a culprit; with an annex, documents
  before and after it are compared separately), street spelling, annex change, invoice total vs
  contract or annex (recognises net typed as gross), advance settlement, correction invoices,
  net + VAT = gross, required documents, date order, signatures, source quality. Fields are
  selected by document type and name; unreadable or low-confidence values never vote and are
  reported by the source-quality rule instead. Documents are processed in a canonical order.
* **Findings** are always `do_sprawdzenia`, carry a Polish reason with the values, evidence
  (document, field, value), subject and context documents, a `fingerprint` (rule, outcome,
  subject documents, fields; stable across reprocessing) and an `evidence_hash` (changes when the
  values change). Explanatory outcomes (spelling, advance, correction) are `info`.
* **Boundary:** `POST /v1/cases/evaluate` (internal token) is stateless. The web job
  `EvaluateCase` sends the stored fields, validates the whole response (documents and fields
  must belong to the case), upserts findings by fingerprint, marks findings that are no longer
  reported as not current (never deletes them), records a `case_evaluations` row and an audit
  event. It runs when the last document of a case finishes processing and on "Sprawdź ponownie";
  unchanged input is skipped unless forced.
* **Evaluation:** `make eval` scores every rule (TP/FP/FN) on ground-truth fields (rules alone;
  any FP/FN fails) and on extracted fields (whole chain; reported).

## Consequences

* Programme changes become new rule versions with a `valid_from`; old cases keep being judged
  by the rules of their date.
* `review_status` (reviewer) is separate from `is_current` (engine), so phase 6 decisions survive
  re-evaluation; a changed `evidence_hash` can trigger a second look.
* Source URLs point to the programme site; the exact programme documents (05/06) were not
  available, so every rule says "do weryfikacji" in its notes.
