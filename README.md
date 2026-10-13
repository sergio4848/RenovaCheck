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
packages/rules/      rule set, field dictionary, schemas        (phase 4–5)
tools/synth/         synthetic documents + ground truth         (phase 2)
infra/postgres/      roles and databases bootstrap
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

Other targets: `make help`, `make logs`, `make seed` (idempotent), `make lint`, `make down`,
`make reset` (asks before deleting volumes).

| Service | URL |
|---|---|
| Web | <http://localhost:8080> |
| Extract API docs | <http://localhost:8001/docs> (health: `/health`, readiness: `/ready`) |
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
