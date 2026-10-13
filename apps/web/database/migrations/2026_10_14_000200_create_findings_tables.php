<?php

use App\Support\Database\RowLevelSecurity;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        // A finding is identified by its fingerprint (rule, outcome, subject documents, fields), so a
        // re-evaluation updates the same row and a later review decision stays attached to it.
        // is_current says whether the latest evaluation still reports it; review_status is the
        // reviewer's side (phase 6 adds decisions). Rows are never deleted by evaluation.
        DB::unprepared(<<<'SQL'
            CREATE TABLE findings (
                id                uuid PRIMARY KEY,
                organization_id   uuid NOT NULL,
                case_file_id      uuid NOT NULL,
                fingerprint       char(64) NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
                rule_id           varchar(16) NOT NULL,
                rule_version      integer NOT NULL CHECK (rule_version >= 0),
                family            varchar(16) NOT NULL
                    CHECK (family IN ('address', 'product', 'amount', 'completeness', 'quality')),
                outcome           varchar(32) NOT NULL CHECK (outcome IN (
                    'discrepancy', 'match_after_normalization', 'agreed_change', 'explained_by_advance',
                    'explained_by_correction', 'missing_document', 'unreadable_source', 'no_rules')),
                severity          varchar(8) NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
                title_pl          varchar(200) NOT NULL,
                reason_pl         varchar(2000) NOT NULL,
                subject_doc_ids   jsonb NOT NULL,
                context_doc_ids   jsonb NOT NULL,
                fields            jsonb NOT NULL,
                evidence          jsonb NOT NULL,
                evidence_hash     char(64) NOT NULL,
                is_current        boolean NOT NULL DEFAULT true,
                review_status     varchar(24) NOT NULL DEFAULT 'do_sprawdzenia'
                    CHECK (review_status IN ('do_sprawdzenia')),
                first_seen_at     timestamptz NOT NULL,
                last_evaluated_at timestamptz NOT NULL,
                created_at        timestamptz NULL,
                updated_at        timestamptz NULL,
                FOREIGN KEY (case_file_id, organization_id)
                    REFERENCES case_files (id, organization_id) ON DELETE CASCADE,
                UNIQUE (case_file_id, fingerprint)
            );
            CREATE INDEX findings_case_current_idx ON findings (organization_id, case_file_id, is_current);

            -- One row per evaluation run: what was read, under which rules and reference date.
            CREATE TABLE case_evaluations (
                id               uuid PRIMARY KEY,
                organization_id  uuid NOT NULL,
                case_file_id     uuid NOT NULL,
                input_hash       char(64) NOT NULL,
                reference_date   date NOT NULL,
                reference_source varchar(24) NOT NULL
                    CHECK (reference_source IN ('application_date', 'contract_date', 'fallback')),
                ruleset          jsonb NOT NULL,
                findings_count   integer NOT NULL CHECK (findings_count >= 0),
                created_at       timestamptz NULL,
                updated_at       timestamptz NULL,
                FOREIGN KEY (case_file_id, organization_id)
                    REFERENCES case_files (id, organization_id) ON DELETE CASCADE
            );
            CREATE INDEX case_evaluations_case_idx ON case_evaluations (organization_id, case_file_id, created_at);
            SQL);

        RowLevelSecurity::isolateByOrganization('findings');
        RowLevelSecurity::grant('findings', ['SELECT', 'INSERT', 'UPDATE']);
        RowLevelSecurity::isolateByOrganization('case_evaluations');
        RowLevelSecurity::grant('case_evaluations', ['SELECT', 'INSERT']);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            DROP TABLE IF EXISTS case_evaluations;
            DROP TABLE IF EXISTS findings;
            SQL);
    }
};
