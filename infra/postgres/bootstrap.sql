-- Roles and databases for RenovaCheck. Run as a superuser with psql variables owner_pw and app_pw:
--   psql -v ON_ERROR_STOP=1 -v owner_pw=... -v app_pw=... -f bootstrap.sql
-- Idempotent: safe to re-run (CI runs it against a fresh service container).
--
-- renova_owner : owns schema objects, runs migrations and seeders; BYPASSRLS for provisioning.
-- renova_app   : runtime role for web and queue; owns nothing, never bypasses RLS.

SELECT format('CREATE ROLE renova_owner LOGIN BYPASSRLS PASSWORD %L', :'owner_pw')
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'renova_owner') \gexec
SELECT format('CREATE ROLE renova_app LOGIN NOBYPASSRLS PASSWORD %L', :'app_pw')
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'renova_app') \gexec
-- Lets tests run as the owner connection and switch to the runtime role with SET ROLE.
GRANT renova_app TO renova_owner;

SELECT 'CREATE DATABASE renova OWNER renova_owner'
 WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'renova') \gexec
SELECT 'CREATE DATABASE renova_test OWNER renova_owner'
 WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'renova_test') \gexec

\connect renova
\ir database.sql
\connect renova_test
\ir database.sql
