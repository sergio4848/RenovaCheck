#!/bin/sh
# Runs once, on first initialisation of the postgres volume (docker-entrypoint-initdb.d).
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v owner_pw="$RENOVA_OWNER_PASSWORD" -v app_pw="$RENOVA_APP_PASSWORD" \
  -f /renova-sql/bootstrap.sql
