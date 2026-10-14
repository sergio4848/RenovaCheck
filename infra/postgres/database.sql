-- Per-database setup, included from bootstrap.sql.
REVOKE ALL ON DATABASE :"DBNAME" FROM PUBLIC;
-- No TEMPORARY: temp tables could shadow public tables inside unqualified function bodies.
REVOKE TEMPORARY ON DATABASE :"DBNAME" FROM renova_app;
GRANT CONNECT ON DATABASE :"DBNAME" TO renova_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO renova_app;
-- Diacritic-insensitive and fuzzy matching for Polish addresses and names.
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
