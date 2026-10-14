<?php

use App\Support\Database\RowLevelSecurity;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        // Review decisions are append-only: a new decision adds a row, the history stays.
        // findings keeps a summary of the latest decision for listing and filtering.
        DB::unprepared(<<<'SQL'
            CREATE UNIQUE INDEX findings_id_org_uq ON findings (id, organization_id);

            ALTER TABLE findings DROP CONSTRAINT findings_review_status_check;
            ALTER TABLE findings ADD CONSTRAINT findings_review_status_check
                CHECK (review_status IN ('do_sprawdzenia', 'rozstrzygniete', 'do_ponownej_weryfikacji'));
            ALTER TABLE findings
                ADD COLUMN rule_source_url       varchar(500) NULL,
                ADD COLUMN decision              varchar(24) NULL
                    CHECK (decision IN ('zgodne', 'rozbieznosc', 'uzgodniona_zmiana', 'nie_dotyczy')),
                ADD COLUMN decided_at            timestamptz NULL,
                ADD COLUMN decided_by            uuid NULL REFERENCES users (id),
                ADD COLUMN decided_evidence_hash char(64) NULL,
                ADD CONSTRAINT findings_decision_summary_ck CHECK (
                    (decision IS NULL) = (decided_at IS NULL)
                    AND (decision IS NULL) = (decided_by IS NULL)
                    AND (decision IS NULL) = (review_status = 'do_sprawdzenia'));
            CREATE INDEX findings_decided_by_idx ON findings (decided_by);

            CREATE TABLE finding_decisions (
                id              uuid PRIMARY KEY,
                organization_id uuid NOT NULL,
                finding_id      uuid NOT NULL,
                decision        varchar(24) NOT NULL
                    CHECK (decision IN ('zgodne', 'rozbieznosc', 'uzgodniona_zmiana', 'nie_dotyczy')),
                comment         varchar(2000) NULL,
                decided_by      uuid NOT NULL REFERENCES users (id),
                evidence_hash   char(64) NOT NULL,
                rule_version    integer NOT NULL,
                created_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
                FOREIGN KEY (finding_id, organization_id)
                    REFERENCES findings (id, organization_id) ON DELETE CASCADE
            );
            CREATE INDEX finding_decisions_finding_idx ON finding_decisions (organization_id, finding_id, created_at);
            CREATE INDEX finding_decisions_decided_by_idx ON finding_decisions (decided_by);
            CREATE TRIGGER finding_decisions_append_only BEFORE UPDATE OR DELETE ON finding_decisions
                FOR EACH ROW EXECUTE FUNCTION renova_reject_mutation();
            CREATE TRIGGER finding_decisions_no_truncate BEFORE TRUNCATE ON finding_decisions
                FOR EACH STATEMENT EXECUTE FUNCTION renova_reject_mutation();
            SQL);

        RowLevelSecurity::isolateByOrganization('finding_decisions');
        RowLevelSecurity::grant('finding_decisions', ['SELECT', 'INSERT']);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            DROP TABLE IF EXISTS finding_decisions;
            ALTER TABLE findings DROP CONSTRAINT IF EXISTS findings_decision_summary_ck;
            ALTER TABLE findings
                DROP COLUMN IF EXISTS decided_evidence_hash,
                DROP COLUMN IF EXISTS decided_by,
                DROP COLUMN IF EXISTS decided_at,
                DROP COLUMN IF EXISTS decision,
                DROP COLUMN IF EXISTS rule_source_url;
            ALTER TABLE findings DROP CONSTRAINT findings_review_status_check;
            ALTER TABLE findings ADD CONSTRAINT findings_review_status_check CHECK (review_status IN ('do_sprawdzenia'));
            DROP INDEX IF EXISTS findings_id_org_uq;
            SQL);
    }
};
