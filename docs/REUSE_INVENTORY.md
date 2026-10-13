# Yeniden kullanım envanteri

Tarama tarihi: 2026-10-13 · Kaynak: `github.com/sergio4848` (75 repo listelendi) · Klonlar: `/tmp/scan/` (sığ klon, salt okunur).

**Kararlar:** `kopyala` = dosya olduğu gibi (yalnızca isim/versiyon değişikliği) · `uyarlayarak al` = yapı/SQL/desen alınır, kod RenovaCheck stack'inde yeniden yazılır · `alma` = alınmaz.

## 0. Özet

| Repo | Stack | Lisans | Değer |
|---|---|---|---|
| **careos** | FastAPI + SQLAlchemy/Alembic + Redis worker (Py 3.13), Next.js web, Postgres 18, compose, Makefile, GH Actions | `LICENSE.md`: "Copyright (c) 2026 Sergen Şahin. All rights reserved." (lisans seçilmemiş) | **Yüksek** – Python servis iskeleti, append-only audit trigger, compose/Makefile/CI, ADR formatı |
| **emlakpro** | NestJS + Prisma + Postgres 16 + Redis + MinIO, Next.js, pnpm/turbo | `LICENSE`: "Copyright (c) 2026 Sergen Şahin. All rights reserved." (yalnız değerlendirme amaçlı görüntüleme) | **Orta** – compose (MinIO + bucket init, test DB), üyelik/rol şeması, tenant izolasyon test senaryoları, audit redaksiyonu |
| **konstela** | Expo/React Native + Supabase (Postgres RLS, Edge Functions) | LICENSE dosyası yok → tüm hakları saklı kabul | **Orta** – RLS/pgTAP baseline testleri, AI çağrı defteri + "approve/off" modları, insan-onay kuyruğu deseni, CI sertleştirme |
| konstela-site | Statik HTML | Yok; fontlar OFL ama `OFL.txt` eksik | Yok |
| php-laravel-eshop | Laravel 10, Jetstream 4, Livewire 3 | Laravel iskeleti (MIT) | Düşük – GH Actions PHP workflow, Fortify aksiyonları |
| Laravel9-BitirmeProjeSistemi | Laravel 9, Jetstream 2 | Black Dashboard (Creative Tim, LICENSE dosyası eksik), BootstrapMade EstateAgency (kredi linki şartlı) | Düşük – rol middleware fikri |
| PhpLaravelNewsCorparate, laravel-api | Laravel 9 | HTML Codex şablonu CC BY 4.0 | Yok |
| python-django-ecommerce, PYTHON-Django-orderfoodwebsite | Django 3.2/4.1 | FoodHut MIT, Bootshop lisans bilinmiyor | Yok |

**Sonuç:** Hiçbir repoda Laravel 11 + Tabler, Postgres RLS (düz Postgres), S3 signed URL, dosya önizleme, PDF/rapor üretimi, YAML kural motoru ya da Lehçe i18n yok → bunlar sıfırdan yazılır. Python servisi, veritabanı güvenlik desenleri ve altyapı dosyaları güçlü biçimde yeniden kullanılır.

**Lisans notu:** careos/emlakpro/konstela'nın telif sahibi "Sergen Şahin" (repo sahibi). Kendi kodunun yeniden kullanımı sahibin kararıdır → `PLAN.md` Soru 1. Onay gelene kadar hiçbir dosya kopyalanmaz. Kopyalanan her dosyanın başına kaynak satırı eklenir (`# Adapted from careos/<yol> — Copyright (c) 2026 Sergen Şahin`) ve köke `NOTICE.md` (kaynak repo → dosya listesi) konur. Üçüncü taraf temalar (Black Dashboard, EstateAgency, HTML Codex, Bootshop) **alınmaz**.

## 1. careos

| Dosya | Ne işe yarar | RenovaCheck'te nerede | Karar |
|---|---|---|---|
| `apps/backend/Dockerfile` | Çok aşamalı, venv tabanlı, root olmayan kullanıcı (uid 10001), `INSTALL_DEV` arg; tek image → API + worker | `services/extract/Dockerfile` | **kopyala** (`PYTHON_VERSION=3.12`, kullanıcı adı `renova`; poppler-utils + tesseract-ocr-pol apt katmanı eklenir) |
| `apps/backend/src/careos/core/logging.py` | structlog JSON log, request_id, secret/PII anahtar redaksiyonu | `services/extract/src/renova_extract/core/logging.py` | **kopyala** (isimler) |
| `apps/backend/src/careos/core/errors.py`, `api/exception_handlers.py` | Kodlu hata gövdesi (`error.code`), tutarlı handler'lar | `services/extract/.../core/errors.py`, `api/exception_handlers.py` | **kopyala** (domain hata kodları değişir) |
| `apps/backend/src/careos/api/middleware.py` | Request-id middleware, erişim logu | `services/extract/.../api/middleware.py` | **kopyala** |
| `apps/backend/src/careos/core/config.py` | pydantic-settings, `SecretStr`, prod'da güvensiz varsayılanı reddetme | `services/extract/.../core/config.py` | **uyarlayarak al** (önek `RENOVA_`; Twilio/telefon alanları silinir; OCR_PROVIDER, LLM_PROVIDER, S3 alanları eklenir) |
| `apps/backend/src/careos/api/health.py` | `/health` (bağımlılıksız), `/ready` (DB+Redis), `/metrics` | `services/extract/.../api/health.py` | **uyarlayarak al** (escalation alanları çıkar, MinIO kontrolü girer) |
| `apps/backend/src/careos/worker/runner.py` | SIGTERM ile düzgün kapanma, heartbeat dosyası, lease döngüsü | `services/extract/.../worker/runner.py` | **uyarlayarak al** (Postgres `SKIP LOCKED` yerine Redis kuyruğu tüketicisi) |
| `apps/backend/migrations/versions/0001_initial_schema.py:442-454` | `careos_reject_mutation()` trigger'ı → UPDATE/DELETE engelli append-only tablo | `apps/web/database/migrations/*_create_audit_events.php` (`DB::unprepared`) | **uyarlayarak al** (SQL neredeyse aynı; hash zinciri sütunu eklenir) |
| `apps/backend/src/careos/modules/audit/service.py` | Audit kaydı iş değişikliğiyle aynı transaction'da; reddedilen deneme ayrı transaction'da | `apps/web/app/Services/AuditLog.php` | **uyarlayarak al** (PHP'ye port) |
| `apps/backend/src/careos/modules/identity/rbac.py`, `principal.py` | Rol → yetki matrisi; route'lar yetkiye bağlı | `apps/web/app/Providers/AuthServiceProvider` Gate'leri | **uyarlayarak al** (owner/reviewer matrisi) |
| `apps/backend/tests/conftest.py`, `tests/integration/test_tenant_isolation.py` | Gerçek Postgres'e karşı test, oturum başı migration, testler arası TRUNCATE; tenant izolasyon paketi | `services/extract/tests/conftest.py`; izolasyon fikri → `apps/web/tests/Feature/TenantIsolationTest.php` | **uyarlayarak al** |
| `apps/backend/pyproject.toml` | Sabit versiyonlar; ruff (bandit, DTZ), strict mypy, pytest ayarları | `services/extract/pyproject.toml` | **uyarlayarak al** (`py312`, bağımlılık listesi değişir) |
| `docker-compose.yml` | postgres/redis + tek seferlik `migrate`, healthcheck'ler, portlar 127.0.0.1'e bağlı | kök `docker-compose.yml` | **uyarlayarak al** (Postgres 16, MinIO, `web`/`queue`/`extract`/`worker` servisleri) |
| `infra/docker/postgres/init/01-test-database.sql` | Test veritabanını oluşturur | `infra/postgres/init/01-test-database.sql` | **kopyala** (`renova_test`) |
| `Makefile` | up/down/reset/logs/seed/test/lint hedefleri | kök `Makefile` | **uyarlayarak al** (`synth`, `eval`, `test-web`=`php artisan test`) |
| `.github/workflows/ci.yml` | ruff+mypy, migration ileri-geri-ileri, seed idempotency, compose smoke | `.github/workflows/ci.yml` | **uyarlayarak al** (Node işi → PHP/Composer işi) |
| `.pre-commit-config.yaml`, `.editorconfig`, `.gitattributes`, `.env.example` | gitleaks, private key tespiti, ruff | kök | **kopyala** (web hook'ları Pint'e çevrilir; `.env.example` içerik yeniden yazılır) |
| `docs/decisions/README.md` + ADR şablonu | Status/tarih → Context → Decision → Consequences; index tablosu | `docs/ADR/` | **kopyala** (yalnızca format + index; içerik yeni) |
| `docs/decisions/ADR-005-multi-tenancy.md` | Kiracı katmanları, başka kiracı kaydına 404, bileşik FK | `docs/ADR/0002-tenant-isolation-rls.md` | **uyarlayarak al** (RenovaCheck'te RLS zorunlu) |
| `apps/web/**` (React/Next) | UI bileşenleri, AppShell, audit tablosu | — | **alma** (stack uyumsuz; Tabler karşılıyor) |
| `packages/contracts/*` | JSON Schema + OpenAPI + TS tipleri | — | **alma** (fikir olarak: web↔extract sözleşmesi JSON Schema, `packages/rules/schema/`) |

## 2. emlakpro

| Dosya | Ne işe yarar | RenovaCheck'te nerede | Karar |
|---|---|---|---|
| `infrastructure/docker-compose.yml` | Postgres + tmpfs `postgres-test` (5433) + Redis `noeviction` + MinIO + `mc mb` bucket init, healthcheck'li | kök compose'un MinIO/test-DB kısmı | **uyarlayarak al** |
| `infrastructure/postgres/init/01-extensions.sql` | pg_trgm, unaccent, uuid-ossp | `infra/postgres/init/00-extensions.sql` | **uyarlayarak al** (PostGIS/pgvector çıkar; `unaccent` Lehçe diakritik normalizasyonunda kullanılır) |
| `apps/api/prisma/schema.prisma` (Organization/User/Membership/Role) + `migrations/20260909000100_init` | Rol üyelik üzerinde; kullanıcı ↔ organizasyon | `organizations`, `users`, `memberships` Laravel migration'ları | **uyarlayarak al** |
| `packages/contracts/src/auth/rbac.ts` | Rol → yetki haritası | Gate tanımları | **uyarlayarak al** (yalnızca matris fikri) |
| `apps/api/src/common/tenancy/*`, `docs/adr/0003-tenant-isolation.md` | Org id yalnızca doğrulanmış üyelikten gelir; tenant bağlamı yoksa istisna | `SetTenantContext` middleware (`SET LOCAL app.organization_id`) | **uyarlayarak al** (emlakpro RLS kullanmıyor; politikalar yeni yazılır) |
| `apps/api/test/tenant-isolation.int-spec.ts`, `test/prepare-integration.ts` | İki tenant seed, filtresiz sorgular sızmıyor mu; DB adı `_test` değilse çalışmayı reddet | `apps/web/tests/Feature/TenantIsolationTest.php`, `RlsPolicyTest.php` | **uyarlayarak al** (senaryolar birebir PHPUnit'e) |
| `apps/api/src/modules/security/audit.service.ts` + `AuditLog` modeli | Aynı transaction'da audit, hassas anahtar redaksiyon regex'i | `AuditLog` servisi sütun/indeks tasarımı | **uyarlayarak al** |
| `packages/design-tokens/src/*` | Renk/spacing token'ları + a11y kontrast testi | Tabler `--tblr-*` override | **alma** (Tabler varsayılan paleti yeterli; prototipte tema işi yok) |
| `.github/workflows/ci.yml` | static + integration ayrımı, hata durumunda log dökümü, `concurrency` | CI yapısı | **uyarlayarak al** (careos ile birleştirilir) |
| `apps/api/src/platform/storage/object-storage.service.ts` | Çıplak S3 istemcisi, signed URL yok | — | **alma** (Laravel `Storage::temporaryUrl`) |
| `packages/ui/**`, `apps/web/**` | React bileşenleri, Next oturumu | — | **alma** (stack uyumsuz) |
| `apps/api/src/config/env.ts` | zod env doğrulama | — | **alma** (pydantic-settings / Laravel config) |

## 3. konstela

| Dosya | Ne işe yarar | RenovaCheck'te nerede | Karar |
|---|---|---|---|
| `supabase/tests/rls_baseline_test.sql`, `server_only_test.sql` | pgTAP: "her tabloda RLS açık", "uygulama rolünün yetkisiz erişimi yok", tablo allowlist | `apps/web/tests/Feature/RlsBaselineTest.php` (katalog sorguları PHPUnit içinde) | **uyarlayarak al** (pgTAP yerine PHPUnit; bkz. ASSUMPTIONS C10) |
| `supabase/migrations/20261005212515_initial_schema.sql` | `security definer` + `set search_path=''`, `revoke all`, private şema, migration başında rollback yorumu | RLS migration'larının yazım kuralları | **uyarlayarak al** (politikalar `auth.uid()` → `current_setting('app.organization_id')::uuid`; `FORCE ROW LEVEL SECURITY`, tablo sahibi olmayan uygulama rolü) |
| `supabase/migrations/20261010180000_ai_calls.sql`, `..170000_ai_config.sql` | AI çağrı defteri (started→done/failed/refused), bütçe rezervasyonu | `extraction_runs` tablosu (yöntem, sağlayıcı, süre, durum) | **uyarlayarak al** (bütçe kısmı alınmaz; LLM varsayılan kapalı) |
| `supabase/functions/_shared/aiRun.ts`, `aiPrompt.ts` | gate → model → çıktı kontrolü → tek tekrar → defter; kullanıcı metnini veri olarak çitleme | `services/extract/.../llm/assist.py` | **uyarlayarak al** (kontrol = Pydantic şeması + sayfa metninde string-match) |
| `docs/AI-FOUNDATION.md` | Durum kodu tablosu, modlar (`vertex`/`approve`/`off`) | `docs/EXTRACTION.md` | **uyarlayarak al** (format; `off`/`fake` modu CI için) |
| `supabase/migrations/20261009270000_photo_review.sql` | İnsan-onay kuyruğu view'ı + `moderate_*(id, decision, reason)` | Bulgu karar akışı | **uyarlayarak al** (RenovaCheck'te her karar ayrıca append-only olay günlüğüne yazılır) |
| `.github/workflows/ci.yml` | Aksiyonlar SHA'ya pinli, `permissions: contents: read`, concurrency | CI sertleştirme | **uyarlayarak al** |
| `docs/PHASE1.md` | "Onaylanacak kararlar / DB tarafından zorlanan / Açık noktalar" formatı | `docs/PLAN.md` faz notları | **uyarlayarak al** (format) |
| `src/**`, `jest*`, `web/**`, `docs/design/*` | RN/TS kodu, marka token'ları | — | **alma** |
| `konstela-site/**` (fontlar, görseller, deck) | Marka varlıkları | — | **alma** |

## 4. Eski Laravel/Django repoları

| Dosya | Ne işe yarar | RenovaCheck'te nerede | Karar |
|---|---|---|---|
| `php-laravel-eshop/.github/workflows/tests.yml` | setup-php matrisi + phpunit | CI'daki PHP işinin iskeleti | **uyarlayarak al** (PHP 8.3 sabit, Postgres servis konteyneri, Pint) |
| `php-laravel-eshop/app/Actions/Fortify/*` | CreateNewUser, PasswordValidationRules | `apps/web/app/Actions/Fortify/*` | **uyarlayarak al** (Laravel 11 Fortify stub'ları zaten yayınlanıyor; yalnızca parola kuralları referans) |
| `php-laravel-eshop/tests/Feature/*` (Auth, Registration…) | Jetstream auth testleri | `apps/web/tests/Feature/Auth/*` | **uyarlayarak al** |
| `Laravel9-BitirmeProjeSistemi/app/Http/Middleware/CheckAdmin.php`, `Models/Role.php` | Global rol kontrolü | `EnsureOrganizationRole` middleware | **alma** (org kapsamlı değil; Gate/Policy ile yeniden yazılır) |
| `Laravel9-BitirmeProjeSistemi/app/Http/Controllers/Admin/*` | Doğrulamasız public-disk upload | — | **alma** (güvenlik açığı deseni) |
| `Laravel9-BitirmeProjeSistemi/public/assets/admin/**` (Black Dashboard), `public/assets/css/style.css` (EstateAgency) | Üçüncü taraf temalar | — | **alma** (lisans dosyası eksik / kredi şartlı; Tabler ile çakışır) |
| `PhpLaravelNewsCorparate/**`, `laravel-api/**` | Jetstream iskeleti, boş API stub'ları | — | **alma** |
| Django repoları | E-ticaret görünümleri | — | **alma** (başka stack, test/PDF yok) |

## 5. Sıfırdan yazılacaklar

Laravel 11 + Tabler Blade layout/bileşenleri · organizasyon/rol + RLS politikaları · güvenli upload (MIME/magic byte, boyut, ClamAV opsiyonel) + MinIO signed URL · sayfa görüntüsü + bbox overlay · OCR adaptörleri · alan sözlüğü + deterministik çıkarıcılar · YAML kural motoru + şema · sentetik belge üreteci · PDF/CSV rapor · `lang/pl.json` · eval/OCR benchmark scriptleri.
