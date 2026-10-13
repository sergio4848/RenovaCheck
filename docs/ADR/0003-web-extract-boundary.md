# ADR-0003: Web ↔ extract boundary: one writer, stateless extraction

* Status: Accepted · 2026-10-13

## Context

Extraction (rendering, OCR, classification, field extraction, rules) is Python; the product,
tenancy and audit are Laravel. Two writers to one schema would duplicate RLS handling and audit.

## Decision

* Laravel owns the schema and is the only database writer. A Laravel queue job (Redis) calls
  the extract API with a short-lived signed object-storage URL and stores the returned result.
* The extract service is stateless: no database connection, bearer-token authentication
  (`RENOVA_INTERNAL_TOKEN`), readiness depends on Redis and object storage only.
* The Python worker (same image, `python -m renova_extract.worker`) consumes a Redis list for
  batch work: evaluation runs, OCR benchmarks and long OCR jobs.
* The rule engine and the evaluation harness live in Python so `make eval` runs without Laravel.

## Consequences

* Contract between the two sides is JSON with a schema in `packages/rules/schema/` (phase 4–5).
* Extraction results that fail schema validation are rejected by Laravel, never partially stored.
