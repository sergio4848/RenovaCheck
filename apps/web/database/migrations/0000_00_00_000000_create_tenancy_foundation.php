<?php

use App\Support\Database\RowLevelSecurity;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        $role = RowLevelSecurity::quoteIdent(RowLevelSecurity::appRole());

        // Tenant context, written per request/job by App\Tenancy\TenantContext. An unset or empty
        // value yields NULL, so policies match no rows instead of erroring.
        DB::unprepared(<<<'SQL'
            CREATE OR REPLACE FUNCTION app_current_org() RETURNS uuid
                LANGUAGE sql STABLE
                SET search_path = pg_catalog, pg_temp
                AS $$ SELECT NULLIF(current_setting('app.organization_id', true), '')::uuid $$;

            CREATE OR REPLACE FUNCTION app_current_user() RETURNS uuid
                LANGUAGE sql STABLE
                SET search_path = pg_catalog, pg_temp
                AS $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;

            -- Append-only guard adapted from careos migrations/versions/0001_initial_schema.py
            -- (careos_reject_mutation) — Copyright (c) 2026 Sergen Şahin.
            CREATE OR REPLACE FUNCTION renova_reject_mutation() RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RAISE EXCEPTION 'RenovaCheck: % is append-only; % is not permitted', TG_TABLE_NAME, TG_OP
                        USING ERRCODE = 'insufficient_privilege';
                END;
                $$;
            SQL);

        DB::statement("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {$role}");
        DB::statement("GRANT EXECUTE ON FUNCTION app_current_org(), app_current_user() TO {$role}");
    }

    public function down(): void
    {
        $role = RowLevelSecurity::quoteIdent(RowLevelSecurity::appRole());
        DB::statement("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM {$role}");
        DB::unprepared(<<<'SQL'
            DROP FUNCTION IF EXISTS renova_reject_mutation();
            DROP FUNCTION IF EXISTS app_current_user();
            DROP FUNCTION IF EXISTS app_current_org();
            SQL);
    }
};
