<?php

use App\Support\Database\RowLevelSecurity;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        // Append-only event log. UPDATE/DELETE/TRUNCATE are rejected by triggers, and each row
        // carries a SHA-256 over its content and the previous row's hash within the same
        // organization, so a removed or altered row breaks the chain (audit_chain_break()).
        DB::unprepared(<<<'SQL'
            -- id is assigned only by the audit_events_chain trigger (never by the client).
            CREATE SEQUENCE IF NOT EXISTS audit_events_id_seq;
            CREATE TABLE audit_events (
                id              bigint PRIMARY KEY,
                organization_id uuid NOT NULL REFERENCES organizations (id),
                actor_user_id   uuid NULL REFERENCES users (id),
                event_type      varchar(64) NOT NULL,
                subject_type    varchar(64) NULL,
                subject_id      uuid NULL,
                payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
                created_at      timestamptz NOT NULL DEFAULT now(),
                prev_hash       char(64) NULL,
                hash            char(64) NOT NULL
            );
            -- Dropped together with the table (migrate:fresh only drops tables).
            ALTER SEQUENCE audit_events_id_seq OWNED BY audit_events.id;
            CREATE INDEX audit_events_org_id_idx ON audit_events (organization_id, id);
            -- A chain has exactly one start and no forks, even under REPEATABLE READ snapshots.
            CREATE UNIQUE INDEX audit_events_chain_link_uq ON audit_events (organization_id, prev_hash);
            CREATE UNIQUE INDEX audit_events_chain_start_uq ON audit_events (organization_id) WHERE prev_hash IS NULL;
            CREATE INDEX audit_events_subject_idx ON audit_events (subject_type, subject_id);
            CREATE INDEX audit_events_actor_idx ON audit_events (actor_user_id);

            CREATE OR REPLACE FUNCTION audit_event_hash(e audit_events) RETURNS char(64)
                LANGUAGE sql IMMUTABLE
                SET search_path = public, pg_temp
                AS $$
                    -- A JSON array keeps field boundaries unambiguous (no delimiter collisions).
                    SELECT encode(sha256(convert_to(jsonb_build_array(
                        e.prev_hash,
                        e.organization_id,
                        e.actor_user_id,
                        e.event_type,
                        e.subject_type,
                        e.subject_id,
                        e.payload,
                        to_char(e.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US')
                    )::text, 'UTF8')), 'hex')
                $$;

            CREATE OR REPLACE FUNCTION audit_events_chain() RETURNS trigger
                LANGUAGE plpgsql
                SET search_path = public, pg_temp
                AS $$
                BEGIN
                    -- Serialize writers per organization so two inserts cannot share a predecessor.
                    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.organization_id::text, 0));
                    -- Assign id and time only after the lock, so id order is chain order and a
                    -- client-supplied id is ignored.
                    NEW.id := nextval('public.audit_events_id_seq');
                    NEW.created_at := clock_timestamp();
                    SELECT a.hash INTO NEW.prev_hash
                      FROM audit_events a
                     WHERE a.organization_id = NEW.organization_id
                     ORDER BY a.id DESC
                     LIMIT 1;
                    NEW.hash := audit_event_hash(NEW);
                    RETURN NEW;
                END;
                $$;

            -- Returns the id of the first event in the active organization whose hash does not
            -- match its content or predecessor, or NULL when the chain is intact.
            CREATE OR REPLACE FUNCTION audit_chain_break() RETURNS bigint
                LANGUAGE plpgsql STABLE
                SET search_path = public, pg_temp
                AS $$
                DECLARE
                    e audit_events;
                    expected_prev char(64) := NULL;
                BEGIN
                    IF app_current_org() IS NULL THEN
                        RAISE EXCEPTION 'audit_chain_break() requires an active organization';
                    END IF;
                    FOR e IN SELECT * FROM audit_events WHERE organization_id = app_current_org() ORDER BY id LOOP
                        IF e.prev_hash IS DISTINCT FROM expected_prev OR e.hash <> audit_event_hash(e) THEN
                            RETURN e.id;
                        END IF;
                        expected_prev := e.hash;
                    END LOOP;
                    RETURN NULL;
                END;
                $$;

            CREATE TRIGGER audit_events_chain BEFORE INSERT ON audit_events
                FOR EACH ROW EXECUTE FUNCTION audit_events_chain();
            CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events
                FOR EACH ROW EXECUTE FUNCTION renova_reject_mutation();
            CREATE TRIGGER audit_events_no_truncate BEFORE TRUNCATE ON audit_events
                FOR EACH STATEMENT EXECUTE FUNCTION renova_reject_mutation();

            ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
            ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
            CREATE POLICY audit_events_read ON audit_events FOR SELECT
                USING (organization_id = app_current_org());
            CREATE POLICY audit_events_append ON audit_events FOR INSERT
                WITH CHECK (organization_id = app_current_org());
            SQL);

        RowLevelSecurity::grant('audit_events', ['SELECT', 'INSERT']);
        RowLevelSecurity::grant('audit_events_id_seq', ['USAGE']);
        $role = RowLevelSecurity::quoteIdent(RowLevelSecurity::appRole());
        DB::statement("GRANT EXECUTE ON FUNCTION audit_chain_break() TO {$role}");
    }

    public function down(): void
    {
        if (app()->isProduction()) {
            throw new RuntimeException('Refusing to drop the append-only event log in production.');
        }
        DB::unprepared(<<<'SQL'
            DROP FUNCTION IF EXISTS audit_chain_break();
            DROP TABLE IF EXISTS audit_events CASCADE;
            DROP SEQUENCE IF EXISTS audit_events_id_seq;
            DROP FUNCTION IF EXISTS audit_events_chain();
            SQL);
    }
};
