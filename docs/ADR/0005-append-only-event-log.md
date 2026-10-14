# ADR-0005: Append-only, hash-chained event log

* Status: Accepted · 2026-10-13

## Context

Findings are decided by people; the report must show who decided what and when, and nobody —
including someone with database access — may rewrite that history unnoticed.

## Decision

* `audit_events` is written only through `App\Services\AuditLog`, in the same transaction as the
  change it describes.
* `BEFORE UPDATE OR DELETE` and `BEFORE TRUNCATE` triggers reject mutation (pattern from
  careos `careos_reject_mutation()`); the runtime role is granted only `SELECT, INSERT`.
* A `BEFORE INSERT` trigger takes a per-organization advisory lock, then assigns `id` from the
  sequence (ignoring any client-supplied id), `created_at = clock_timestamp()`, `prev_hash`
  (latest hash of the organization) and `hash = sha256(jsonb_build_array(prev_hash, …fields))`.
  Unique indexes on `(organization_id, prev_hash)` and on the single chain start reject forks.
* `audit_chain_break()` returns the first event whose hash does not match (it refuses to run
  without an active organization); the event log page shows the result.
* Payload keys that look like secrets are redacted before writing.

## Consequences

* Inserts into the log are serialized per organization; fine at prototype volume.
* Tampering by a schema owner who disables triggers is detected, not prevented. Removing the
  newest events is not detectable without an external anchor of the head hash (later work).
