# ADR-0001: Monorepo layout and fixed stack

* Status: Accepted · 2026-10-13

## Context

RenovaCheck is a two-week TRL 3 prototype: synthetic documents in, consistency findings out.
The stack was fixed up front (Laravel + Python + PostgreSQL + Redis + S3-compatible storage).

## Decision

| Path | Content |
|---|---|
| `apps/web` | Laravel 11 (PHP 8.3; upgraded to Laravel 13 by [ADR-0011](0011-laravel-upgrade-to-13.md)), Blade + Tabler 1.6 (vendored, MIT), Alpine.js, Fortify sign-in. No SPA. |
| `services/extract` | Python 3.12, FastAPI API + Redis-list batch worker, one image with two entrypoints. |
| `packages/rules` | YAML rule set, field dictionary and their JSON Schemas (from phase 2/4). |
| `tools/synth` | Synthetic document and ground-truth generator (phase 2). |
| `infra/` | PostgreSQL bootstrap, optional build CA certificates. |
| `docs/` | Plan, assumptions, reuse inventory, ADRs, evaluation reports. |

Everything runs with `docker compose` through `make up | seed | test`. Laravel 11 is kept as
decided even though its security support ended in March 2026; moving to 12 is a separate decision.

## Consequences

* One repository, two languages; each has its own linter and test runner, both wired into CI.
* No Node build step: Tabler and Alpine are committed as built files with their licences.
