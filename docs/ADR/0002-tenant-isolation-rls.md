# ADR-0002: Tenant isolation with PostgreSQL row-level security

* Status: Accepted · 2026-10-13

## Context

Customers are document-preparation firms; one firm must never see another firm's cases.
careos (ADR-005) and emlakpro (ADR-0003) isolated tenants in the application layer only.
For RenovaCheck the database must enforce it as well.

## Decision

* Two database roles. `renova_owner` owns the schema, runs migrations and seeders, and has
  `BYPASSRLS` for provisioning. `renova_app` is the runtime role for web and queue: it owns no
  table and cannot bypass RLS. Bootstrap: `infra/postgres/bootstrap.sql`.
* Every tenant table has `organization_id` and `ENABLE` + `FORCE ROW LEVEL SECURITY` with a
  policy `organization_id = app_current_org()`. `app_current_org()` reads the session setting
  `app.organization_id`; unset means NULL, which matches no row.
* `organizations` and `memberships` additionally let a user see their own memberships
  (`app.user_id`) so the active organization can be chosen before it is set.
* `App\Tenancy\TenantContext` writes both settings. The `tenant` middleware activates the
  session's organization (or the first membership) before route-model binding, and clears it on
  terminate. Queue jobs must use `TenantContext::run()`.
* A global Eloquent scope (`BelongsToOrganization`) filters by the same id and throws when no
  organization is active, so a missing context fails closed instead of returning nothing silently.
* Cross-tenant access answers 404, never 403.
* `users` is a global identity table, also under forced RLS: a user row is visible to the user
  themself and to members of the active organization, and only the user can update it.
  Sign-in maps an e-mail to an id with the `SECURITY DEFINER` function `auth_user_id_by_email()`;
  `App\Auth\TenantAwareUserProvider` sets `app.user_id` before loading the row.
* Functions used by policies and triggers pin `search_path`, and the runtime role has no
  `TEMPORARY` privilege, so temp tables cannot shadow public tables.

## Consequences

* Tests run against PostgreSQL with the runtime role (`SET ROLE renova_app` inside the test
  transaction), including raw SQL that bypasses Eloquent (`tests/Feature/TenantIsolationTest.php`).
* `RlsBaselineTest` fails when a new table with `organization_id` lacks forced RLS.
* Connections are not persistent (mod_php), so a session setting cannot leak between requests;
  long-lived workers clear it after each job. `set_config()` is transactional, so clearing must
  happen outside a transaction that can roll back (queue job middleware, phase 3).
* Known limits: policies check the organization, not the role (a reviewer could change
  memberships through raw SQL if the application exposed such a path; it does not), and the
  `app.*` settings can be changed by any SQL running as the runtime role, so RLS protects against
  missing filters, not against SQL injection.
