# RenovaCheck

Prototype (TRL 3) of a B2B tool for firms that prepare and check documents for Polish thermal
modernisation projects (*termomodernizacja*, Czyste Powietrze). It cross-checks the documents of
one case — application extract, offer/contract, invoice, acceptance protocol, product card — for
consistency and missing documents. **Synthetic data only.**

Plan, scope and assumptions: [`docs/PLAN.md`](docs/PLAN.md), [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md).
Decisions: [`docs/ADR/`](docs/ADR/README.md).

## Architecture

```
                 ┌─────────────────────────── docker compose ───────────────────────────┐
  browser ──────►│ web    Laravel 11 · PHP 8.3 · Blade + Tabler · Fortify (sign-in)      │
  :8080          │  │     queue  (same image, php artisan queue:work redis)              │
                 │  │        │                                                          │
                 │  ▼        ▼                                                          │
                 │ postgres 16  ── row-level security: organization_id = app_current_org()│
                 │ redis 7      ── queues, sessions, cache                              │
                 │ minio        ── private bucket, signed URLs                          │
                 │  ▲                                                                   │
                 │  │ signed URL                                                        │
  :8001 ────────►│ extract  FastAPI · Python 3.12 (stateless: render, OCR, classify,      │
                 │          extract, rules)  ·  worker (same image, batch jobs)          │
                 └──────────────────────────────────────────────────────────────────────┘
```

* **Tenant isolation** is enforced by PostgreSQL row-level security; the web app runs as a role
  that owns no table and cannot bypass RLS ([ADR-0002](docs/ADR/0002-tenant-isolation-rls.md)).
* **The web app is the only database writer**; the extraction service is stateless
  ([ADR-0003](docs/ADR/0003-web-extract-boundary.md)).
* **The event log is append-only and hash-chained** ([ADR-0005](docs/ADR/0005-append-only-event-log.md)).
* Roles per organization: `owner` (everything) and `reviewer` (cases, findings, event log).

```
apps/web/            Laravel application
services/extract/    Python extraction service + worker
packages/rules/      document types, field dictionary, rules (YAML, versioned), schemas
tools/synth/         synthetic documents + ground truth
infra/postgres/      roles and databases bootstrap
infra/minio/         bucket and per-service accounts
docs/                plan, assumptions, ADRs, reports
```

## Quick start

Requirements: Docker with Compose v2, GNU make, openssl.

```bash
make up        # creates .env (dev defaults + fresh APP_KEY), builds, migrates, seeds, waits for health
make test      # Laravel tests (PostgreSQL + RLS) and Python tests, inside the containers
```

Open <http://localhost:8080> and sign in with a demo account (password `renova-demo`, set by
`DEMO_USER_PASSWORD`):

| E-mail | Organizations and roles |
|---|---|
| `wlasciciel@alfa.test` | Alfa Termo Audyt — owner |
| `weryfikator@alfa.test` | Alfa Termo Audyt — reviewer, Beta Dokumentacja — reviewer |
| `wlasciciel@beta.test` | Beta Dokumentacja — owner |

Synthetic data: `make synth` writes 20 cases (106 PDFs with ground truth) to `data/synth/`
and validates them against `packages/rules/schema/ground_truth.schema.json`; see
[`tools/synth/README.md`](tools/synth/README.md).

Document flow: on a case page, upload PDF/PNG/JPEG files; a queue job sends each one to the
extraction service, which renders page images, reads the text layer (or OCR for scans),
classifies the document type and reads the fields defined in
[`packages/rules/fields.yaml`](packages/rules/fields.yaml) with their page and box
([ADR-0007](docs/ADR/0007-field-extraction-and-provenance.md)). The document page shows the
fields next to the page image with the boxes they were read from. Virus scanning is optional:
`docker compose --profile av up -d` with `CLAMAV_ENABLED=true`.

When all documents of a case are processed, the rules in
[`packages/rules/rules/`](packages/rules/rules) run on the stored fields
([ADR-0008](docs/ADR/0008-rule-engine.md)): address, parties, device, amounts (net/gross,
advance, correction), missing documents, dates and signatures. Findings appear on the case page
as "do sprawdzenia" with the reason and links to the fields; "Sprawdź ponownie" re-runs them.
A rule change is a new rule version (`python -m renova_extract.rules lock --write` records it;
published versions are immutable).

Each finding opens a review screen: the source pages with the boxes of the compared values next
to the reason, the rule and its source. Reviewers decide *zgodne*, *rozbieżność*, *uzgodniona
zmiana* or *nie dotyczy* (a comment is required for critical findings); decisions are
append-only and audited, and a case closes only when every critical finding is decided
([ADR-0009](docs/ADR/0009-review-decisions-and-csp.md)). A five-minute walkthrough is in
[`docs/DEMO.md`](docs/DEMO.md).

`make eval` measures document type accuracy, per-field precision/recall (clean PDFs must reach
95 %; scans are reported) and per-rule TP/FP/FN on ground-truth fields (must be exact) and on
extracted fields, and writes `data/eval/{classification,extraction,rules}.json`.

OCR and the optional LLM helper are chosen in `.env`: `RENOVA_OCR_PROVIDER` (`tesseract`,
`text_layer`, `azure`, `google`) and `RENOVA_LLM_PROVIDER` (`off` by default, or `anthropic`;
its proposals are kept only when they occur verbatim in the page text). Document content goes to
these external services only for organizations that consented
(`php artisan org:external-processing <slug> on`); otherwise local Tesseract is used.

Object storage uses one account per service (created by `minio-init` from `S3_WEB_*` and
`S3_EXTRACT_*` in `.env`); the MinIO root account is only used for that setup. If your `.env`
predates these keys, copy them from `.env.example`.

Other targets: `make help`, `make logs`, `make seed` (idempotent), `make lint`, `make down`,
`make reset` (asks before deleting volumes).

| Service | URL |
|---|---|
| Web | <http://localhost:8080> |
| Extract API docs | <http://localhost:8001/docs> (health: `/health`, readiness: `/ready`) |
| MinIO API (signed URLs) | <http://localhost:9000> |
| MinIO console | <http://localhost:9001> |

### Builds behind a TLS-intercepting proxy

* Put the proxy CA as `infra/certs/*.crt` (git-ignored); images trust it during the build.
* `COMPOSE_BUILD_NETWORK=host` lets builds reach a proxy on the host's loopback.
* If Composer cannot download package archives, set `WEB_VENDOR_SEED=./apps/web/vendor` after a
  local `composer install` in `apps/web`; the image build then reuses that directory.

## Development without containers

```bash
# Python service
cd services/extract && python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest && .venv/bin/ruff check . && .venv/bin/mypy

# Laravel (needs the compose PostgreSQL on 127.0.0.1:5432)
cd apps/web && composer install && cp .env.example .env && php artisan key:generate
php artisan migrate --database=migrator && php artisan db:seed --database=migrator
php artisan test && vendor/bin/pint --test
```

## Decision log

Architecture decisions are recorded in [`docs/ADR/`](docs/ADR/README.md). Reused code from the
author's other repositories and third-party components are listed in [`NOTICE.md`](NOTICE.md)
and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Licence

Proprietary — all rights reserved. Third-party components keep their own licences.
