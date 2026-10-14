# Architecture Decision Records

Short, dated records of decisions that shape RenovaCheck. Format: context, decision, consequences.
A superseded ADR is kept and marked, never deleted. (Format adapted from careos/docs/decisions —
Copyright (c) 2026 Sergen Şahin.)

| ADR | Title | Status |
|---|---|---|
| [0001](0001-monorepo-layout.md) | Monorepo layout and fixed stack | Accepted |
| [0002](0002-tenant-isolation-rls.md) | Tenant isolation with PostgreSQL row-level security | Accepted |
| [0003](0003-web-extract-boundary.md) | Web ↔ extract boundary: one writer, stateless extraction | Accepted |
| [0004](0004-object-storage-image.md) | Object storage image after MinIO stopped publishing images | Accepted |
| [0005](0005-append-only-event-log.md) | Append-only, hash-chained event log | Accepted |
| [0006](0006-document-intake-and-classification.md) | Document intake, storage and type classification | Accepted |
| [0007](0007-field-extraction-and-provenance.md) | Deterministic field extraction with provenance | Accepted |
| [0008](0008-rule-engine.md) | Deterministic rule engine with dated, versioned rules | Accepted |
| [0009](0009-review-decisions-and-csp.md) | Review decisions, re-verification and a strict content security policy | Accepted |
