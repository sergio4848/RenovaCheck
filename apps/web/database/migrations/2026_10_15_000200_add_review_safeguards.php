<?php

use App\Support\Database\RowLevelSecurity;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        $role = RowLevelSecurity::quoteIdent(RowLevelSecurity::appRole());
        DB::unprepared(<<<SQL
            -- Document content goes to external services (cloud OCR, LLM helper) only with consent.
            ALTER TABLE organizations ADD COLUMN allow_external_processing boolean NOT NULL DEFAULT false;

            -- Jobs run without a user, so they cannot see organizations through RLS; this reads the
            -- flag of the active organization only.
            CREATE OR REPLACE FUNCTION app_org_allows_external() RETURNS boolean
                LANGUAGE sql STABLE SECURITY DEFINER
                SET search_path = public, pg_temp
                AS \$\$ SELECT COALESCE((SELECT allow_external_processing FROM organizations WHERE id = app_current_org()), false) \$\$;
            REVOKE ALL ON FUNCTION app_org_allows_external() FROM PUBLIC;
            GRANT EXECUTE ON FUNCTION app_org_allows_external() TO {$role};

            -- A failed evaluation is recorded, so the case page and closing can see it.
            ALTER TABLE case_evaluations
                ADD COLUMN status varchar(8) NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'failed')),
                ADD COLUMN error_code varchar(64) NULL,
                ALTER COLUMN reference_date DROP NOT NULL,
                ALTER COLUMN reference_source DROP NOT NULL,
                ALTER COLUMN ruleset DROP NOT NULL,
                ADD CONSTRAINT case_evaluations_result_ck CHECK (
                    (status = 'ok' AND reference_date IS NOT NULL AND reference_source IS NOT NULL AND ruleset IS NOT NULL
                        AND error_code IS NULL)
                    OR (status = 'failed' AND error_code IS NOT NULL));

            -- What the reviewer saw when deciding, kept with the decision (the finding is updated in place).
            ALTER TABLE finding_decisions
                ADD COLUMN reason_pl varchar(2000) NULL,
                ADD COLUMN evidence jsonb NULL;
            SQL);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            ALTER TABLE finding_decisions DROP COLUMN IF EXISTS evidence, DROP COLUMN IF EXISTS reason_pl;
            DELETE FROM case_evaluations WHERE status = 'failed';
            ALTER TABLE case_evaluations
                DROP CONSTRAINT IF EXISTS case_evaluations_result_ck,
                DROP COLUMN IF EXISTS error_code,
                DROP COLUMN IF EXISTS status,
                ALTER COLUMN reference_date SET NOT NULL,
                ALTER COLUMN reference_source SET NOT NULL,
                ALTER COLUMN ruleset SET NOT NULL;
            DROP FUNCTION IF EXISTS app_org_allows_external();
            ALTER TABLE organizations DROP COLUMN IF EXISTS allow_external_processing;
            SQL);
    }
};
