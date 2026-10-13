<?php

use App\Support\Database\RowLevelSecurity;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        // One row per field read from a document, with where it was read (page + box) and how.
        // Values are the normalized comparison form ("39350.00", "2026-06-05", "kosciuszki");
        // raw_text keeps the text as printed. Rows are replaced as a whole on reprocessing.
        DB::unprepared(<<<'SQL'
            ALTER TABLE documents ADD COLUMN extraction jsonb NULL;

            CREATE TABLE document_fields (
                id              uuid PRIMARY KEY,
                organization_id uuid NOT NULL,
                document_id     uuid NOT NULL,
                name            varchar(64) NOT NULL CHECK (name ~ '^[a-z][a-z0-9_]*$'),
                value           varchar(500) NULL,
                raw_text        varchar(500) NOT NULL,
                page_no         integer NOT NULL CHECK (page_no > 0),
                bbox            jsonb NOT NULL,
                method          varchar(16) NOT NULL
                    CHECK (method IN ('label', 'block', 'above', 'title_number', 'address', 'signature', 'llm')),
                confidence      numeric(4, 3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
                status          varchar(12) NOT NULL CHECK (status IN ('ok', 'unreadable')),
                created_at      timestamptz NULL,
                updated_at      timestamptz NULL,
                FOREIGN KEY (document_id, organization_id)
                    REFERENCES documents (id, organization_id) ON DELETE CASCADE,
                UNIQUE (document_id, name),
                CONSTRAINT document_fields_value_status_ck CHECK ((status = 'ok') = (value IS NOT NULL))
            );
            CREATE INDEX document_fields_org_name_idx ON document_fields (organization_id, name);
            SQL);

        RowLevelSecurity::isolateByOrganization('document_fields');
        RowLevelSecurity::grant('document_fields', ['SELECT', 'INSERT', 'UPDATE', 'DELETE']);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            DROP TABLE IF EXISTS document_fields;
            ALTER TABLE documents DROP COLUMN IF EXISTS extraction;
            SQL);
    }
};
