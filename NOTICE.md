# Notices

## Code adapted from the author's other repositories

Copyright (c) 2026 Sergen Şahin. Reused in RenovaCheck by the copyright holder. Each adapted
file carries a header naming its source.

| Source | RenovaCheck file(s) |
|---|---|
| careos `apps/backend/src/careos/core/{logging,context,config,errors}.py` | `services/extract/src/renova_extract/core/*.py` |
| careos `apps/backend/src/careos/api/{middleware,exception_handlers,health}.py` | `services/extract/src/renova_extract/api/*.py` |
| careos `apps/backend/src/careos/worker/runner.py` | `services/extract/src/renova_extract/worker/runner.py` |
| careos `apps/backend/Dockerfile`, `pyproject.toml` | `services/extract/Dockerfile`, `services/extract/pyproject.toml` |
| careos `migrations/versions/0001_initial_schema.py` (append-only trigger) | `apps/web/database/migrations/0000_00_00_000000_create_tenancy_foundation.php` |
| careos `docker-compose.yml`, `Makefile`, `.github/workflows/ci.yml`, `docs/decisions/` format | `compose.yaml`, `Makefile`, `.github/workflows/ci.yml`, `docs/ADR/` |
| emlakpro `infrastructure/docker-compose.yml` | `compose.yaml` (MinIO + bucket init) |
| emlakpro `apps/api/test/tenant-isolation.int-spec.ts` (scenarios) | `apps/web/tests/Feature/TenantIsolationTest.php` |
| emlakpro `apps/api/src/modules/security/audit.service.ts` (redaction) | `apps/web/app/Services/AuditLog.php` |
| konstela `supabase/tests/rls_baseline_test.sql` (idea) | `apps/web/tests/Feature/RlsBaselineTest.php` |

## Third-party components

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
