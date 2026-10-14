# ADR-0009: Review decisions, re-verification and a strict content security policy

* Status: Accepted · 2026-10-14

## Context

Findings (ADR-0008) are born "do sprawdzenia". A person must decide each one (zgodne, rozbieżność,
uzgodniona zmiana, nie dotyczy), critical findings need a justification, and the history of who
decided what must survive re-evaluation and stay tamper-evident.

## Decision

* **Decisions are append-only rows** in `finding_decisions` (RLS, composite tenant key, only
  SELECT/INSERT granted, UPDATE/DELETE/TRUNCATE rejected by `renova_reject_mutation()` even for
  the schema owner). Each row stores the finding's `evidence_hash` and rule version at decision
  time. `findings` keeps a summary of the latest decision for lists and filters; a check
  constraint keeps summary and review status consistent. Every decision is also an audit event
  (decision, rule, severity, comment length — not the comment text).
* **Review states:** `do_sprawdzenia` → `rozstrzygniete`; when a re-evaluation reports different
  values (`evidence_hash` ≠ the decided one) the finding becomes `do_ponownej_weryfikacji` and
  keeps showing the earlier decision; equal values restore `rozstrzygniete`.
* **Rules for deciding:** only current findings, only in open cases, comment required for
  critical findings, any number of decisions (history kept). Permission `findings.decide`.
* **Case lifecycle:** `new` → `in_review` on the first evaluation; `closed` only when every
  current critical finding has a valid decision; reopening returns to `in_review`. Closed cases
  reject document uploads, type changes, re-evaluation and decisions. All transitions are audited.
* **Review screen:** the finding next to the source pages (signed, short-lived image URLs) with
  boxes for every compared value (subject document emphasised, context dashed), evidence table
  with confidences, rule source link, decision form and history, previous/next navigation.
* **No inline code:** Alpine.js was removed; one same-origin script (`public/js/review.js`)
  positions boxes from `data-box` attributes, links rows and boxes, and refreshes processing
  pages. Every web response carries `Content-Security-Policy` (`script-src 'self'`,
  `style-src 'self'`, images only from self and the object-store host, `frame-ancestors 'none'`,
  `form-action 'self'`), `Permissions-Policy`, COOP, and HSTS in production. A test scans the main
  pages for inline scripts, style attributes and event handlers.

## Consequences

* Phase 7 reports read decisions from `finding_decisions`; unapproved critical findings are
  identifiable by `review_status`.
* New UI behaviour goes into `review.js` (or another same-origin file), never inline.
