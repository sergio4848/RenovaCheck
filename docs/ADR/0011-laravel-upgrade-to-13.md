# ADR-0011: Upgrade the web application from Laravel 11 to Laravel 13 (via 12)

* Status: **Proposed** · 2026-10-14
* Supersedes, once accepted: the "Laravel 11" entry of the fixed stack (`docs/PLAN.md`, prompt
  section "Architecture") and the matching risk row in `docs/PLAN.md` §4.

## Context

The web application (`apps/web`) runs Laravel 11 (`laravel/framework` v11.57.0) on PHP 8.3.
Laravel 11 was fixed by the project prompt and has been accepted as a known risk since Phase 0.
Two facts changed that trade-off:

**1. Laravel 11 no longer gets security fixes.** Laravel's support policy gives each major
release 18 months of bug fixes and 2 years of security fixes:

| Version | Bug fixes until | Security fixes until | State on 2026-10-14 |
|---|---|---|---|
| 11 | 2025-09-03 | 2026-03-12 | end of life |
| 12 | 2026-08-13 | 2027-02-24 | security fixes only, ~4 months left |
| 13 | Q3 2027 | 2028-03-17 | fully supported |

**2. Our installed version has open advisories with no Laravel 11 fix.** `composer audit` reports
4 advisories for `laravel/framework`. As far as we could check, none is reachable from today's
code paths:

* Fortify serves only the login form (`features` is empty), so there is no `email` validation
  rule and no signed verification route.
* Document and page links are S3 presigned URLs from the AWS SDK, not Laravel signed routes.
* Debug pages are off outside local development.

The risk is therefore latent, not acute. It comes back with any new feature that uses those
APIs, such as member invitations, password reset or local-disk temporary URLs, and every future
advisory will again ship without a Laravel 11 fix.

| Advisory | Severity | Fixed in |
|---|---|---|
| CRLF injection in default email rule (CVE-2026-48019) | – | 12.60.0 / 13.10.0 |
| CRLF injection in default email rule (GHSA, no CVE) | high | 12.60.0 / 13.10.0 |
| Temporary Signed URL path confusion | medium | 12.61.1 / 13.12.0 |
| XSS in debug page information (CVE-2026-102279) | low | 12.69.0 / 13.30.0 |

The upgrade guides require one major version at a time (11 → 12, then 12 → 13). Laravel 13 needs
PHP ≥ 8.3, which the Docker image (`PHP_VERSION=8.3.26`) and CI (`php-version: "8.3"`) already use.

### Spike (measured, outside the repository)

Before proposing the change, the upgrade was tried on a copy of `apps/web` outside the repository,
using the same PostgreSQL test database with row-level security active. Nothing in the repository
was changed.

| Check | Laravel 11 (today) | Laravel 12.70.0 | Laravel 13.36.0 |
|---|---|---|---|
| Application code changes needed | – | **none** | **none** (2 optional config hardening lines, below) |
| `php artisan test` | 127 passed, 1 skipped¹ | 127 passed, 1 skipped¹ | 127 passed, 1 skipped¹ |
| `pint --test` | pass | pass | pass |
| `composer audit` | 4 advisories | **clean** | **clean** |
| Migrations apply → roll back → re-apply, seed twice | pass | pass | pass |
| `config:cache`, `route:cache`, `view:cache` | pass | – | pass |
| Live smoke: S3 put/get on MinIO, presigned URL fetch, extract `/health` over HTTP | pass (Guzzle 7) | – | pass (Guzzle 8) |

¹ The copy lived outside the monorepo, so the one test that needs `packages/rules` skips itself.
In the repository the same suite runs 128 tests.

The upgrade guides were checked item by item against the code:

* **12, UUIDv7 in `HasUuids` (medium).** Ten models use `HasUuids`. New rows get time-ordered
  v7 ids; existing v4 ids stay valid. No ordering depends on these ids: lists order by
  `created_at` or by the bigint `audit_events.id`. `EvaluateCase::input()` sorts documents by id
  only to make the input hash deterministic, and stays deterministic. Accepted as is.
* **12, other items: no impact.** Carbon 3 is already installed (3.14). The container's
  default-value change does not apply: no class resolved by the container has a nullable default.
  The `local` disk root is already explicit (`storage/app/private`). We use no SVG `image` rule,
  no `Schema::getTables()` and no `mergeIfMissing()`.
* **13, CSRF middleware renamed to `PreventRequestForgery` (high in the guide).** The code never
  references `VerifyCsrfToken`. The new `Sec-Fetch-Site` check passes for our same-origin forms;
  all form tests pass.
* **13, `cache.serializable_classes` and `session.serialization` (hardening).** Our config files
  predate both keys. The cache holds only rate-limiter counters and job locks, and the session
  holds only scalars (the active organization id). So `serializable_classes => false` and
  `serialization => 'json'` are safe; tests pass with both. Switching sessions to JSON logs
  everyone out once.
* **13, other items: no impact.** We already set `CACHE_PREFIX`/`REDIS_PREFIX`/`SESSION_COOKIE`
  defaults explicitly. Pagination uses `useBootstrapFive()`. We have no MySQL, no `upsert`, no
  queue event listeners, no `array_first()` helpers and no PHPUnit doc-block annotations
  (PHPUnit 12 removed them).

Dependency changes found by the spike (everything else resolves unchanged):

| Package | Today | Laravel 12 | Laravel 13 |
|---|---|---|---|
| `laravel/framework` | 11.57.0 | 12.70.0 | 13.36.0 |
| `laravel/tinker` | 2.11.1 | 2.11.1 | **3.0.2** |
| `phpunit/phpunit` (dev) | 11.5.57 | 11.5.57 | **12.5.39** |
| `guzzlehttp/guzzle` | 7.15.5 | 7.15.5 | **8.2.0** (also used by the AWS SDK; live smoke passes) |
| `brick/math` | 0.14.8 | 0.14.8 | 1.0.0 |
| `symfony/*` | 7.4.18–7.4.20 | 7.4.21 | 7.4.21 |
| `laravel/fortify`, `laravel/passkeys`, `barryvdh/laravel-dompdf`, `league/flysystem-aws-s3-v3`, `predis/predis`, `nunomaduro/collision` | unchanged | unchanged | unchanged |

## Options

1. **Stay on Laravel 11.** No work. The four advisories stay open but are not reachable today;
   any future advisory will have no fix. That is acceptable for a synthetic-data prototype, not
   for anything touching real case documents (TRL 4 and beyond).
2. **Upgrade to Laravel 12 only.** Smallest change (two `composer.json` lines, no code). Fixes
   all four advisories, but support ends on 2027-02-24, so a second upgrade is due within about
   four months.
3. **Upgrade 11 → 12 → 13 (proposed).** Fixes all four advisories and gives security support until
   March 2028. The spike shows no application code changes on either step. Two dependency majors
   (Tinker 3, PHPUnit 12) and Guzzle 8 come with it, all verified by the test suite and the live
   smoke test.

## Decision (proposed)

Upgrade `apps/web` to Laravel 13 on one migration branch, in two steps that each stay green:

1. **Laravel 12:** `laravel/framework:^12.0`. Run the full checks.
2. **Laravel 13:**
   * `laravel/framework:^13.0`, `laravel/tinker:^3.0`, `phpunit/phpunit:^12.0`;
   * `"php": "^8.3"` in `composer.json`, to match Laravel 13's requirement;
   * `config/cache.php` `'serializable_classes' => false` and `config/session.php`
     `'serialization' => 'json'`.

   Run the full checks again.

Acceptance criteria for the migration branch:

* `composer audit` clean.
* CI green: Pint, migrations apply/rollback/re-apply, seed twice, PHPUnit on PostgreSQL with RLS,
  and the full stack job (`make up`, `make test`, `make eval`).
* Rebuilt web image (`make up`) passes the Playwright demo on SYN-2026-012 (upload → findings →
  decisions → close → PDF/CSV report) with no CSP errors in the console.
* Docs updated in the same branch: `docs/PLAN.md` (stack and risk row), `README.md` (architecture
  line), `docs/ASSUMPTIONS.md` J, this ADR's status set to Accepted.

Rollback: revert the branch. Neither step changes the database schema, and v7 UUIDs created in
between remain valid under Laravel 11, so no data migration is involved.

## Consequences

* The "fixed stack" in the prompt and PLAN changes from Laravel 11 to Laravel 13. This needs the
  project owner's approval, hence *Proposed*. Until then Laravel 11 with the four advisories
  remains an accepted risk (ASSUMPTIONS J2).
* Expected effort is small. The spike needed no code changes; the work is dependency updates,
  two config lines, the image rebuild and the end-to-end checks.
* Not yet verified, and left to the migration branch:
  * the Docker image built with Laravel 13;
  * the Playwright demo against that image;
  * JSON sessions in Redis behind the real login flow (only the test session driver was
    exercised).
* Users are signed out once when sessions switch to JSON.
* Afterwards, minor Laravel releases carry security fixes. CI should run `composer audit` so a new
  advisory fails the build instead of waiting for someone to notice. That is a small follow-up,
  not part of this upgrade.

## Sources

* Laravel support policy and dates: <https://laravel.com/docs/13.x/releases>,
  <https://laravel-news.com/laravel-releases>
* Upgrade guides: <https://laravel.com/docs/12.x/upgrade>, <https://laravel.com/docs/13.x/upgrade>
* Advisories: `composer audit` on `apps/web/composer.lock` (2026-10-14)
