<?php

use App\Support\Database\RowLevelSecurity;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        // Composite foreign keys (id, organization_id) make it impossible to attach a document to a
        // case — or a page to a document — of another organization, independently of RLS.
        DB::unprepared(<<<'SQL'
            CREATE UNIQUE INDEX case_files_id_org_uq ON case_files (id, organization_id);

            CREATE TABLE documents (
                id                  uuid PRIMARY KEY,
                organization_id     uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
                case_file_id        uuid NOT NULL,
                original_name       varchar(255) NOT NULL,
                mime                varchar(64) NOT NULL,
                size_bytes          bigint NOT NULL CHECK (size_bytes > 0),
                sha256              char(64) NOT NULL,
                storage_key         varchar(255) NOT NULL,
                status              varchar(16) NOT NULL DEFAULT 'uploaded'
                    CHECK (status IN ('uploaded', 'processing', 'processed', 'failed')),
                scan_status         varchar(16) NOT NULL
                    CHECK (scan_status IN ('skipped', 'clean')),
                doc_type            varchar(32) NULL CHECK (doc_type IN (
                    'wniosek_ekstrakt', 'oferta', 'umowa', 'aneks', 'faktura', 'faktura_zaliczkowa',
                    'faktura_korygujaca', 'protokol_odbioru', 'karta_produktu')),
                doc_type_source     varchar(16) NULL CHECK (doc_type_source IN ('classifier', 'user')),
                doc_type_confidence numeric(4, 3) NULL CHECK (doc_type_confidence BETWEEN 0 AND 1),
                classification      jsonb NULL,
                page_count          integer NULL CHECK (page_count > 0),
                error_code          varchar(64) NULL,
                uploaded_by         uuid NOT NULL REFERENCES users (id),
                processed_at        timestamptz NULL,
                created_at          timestamptz NULL,
                updated_at          timestamptz NULL,
                FOREIGN KEY (case_file_id, organization_id)
                    REFERENCES case_files (id, organization_id) ON DELETE CASCADE,
                CONSTRAINT documents_type_source_ck CHECK ((doc_type IS NULL) = (doc_type_source IS NULL))
            );
            -- The same file uploaded twice into one case is one document.
            CREATE UNIQUE INDEX documents_case_sha_uq ON documents (case_file_id, sha256);
            CREATE UNIQUE INDEX documents_id_org_uq ON documents (id, organization_id);
            CREATE INDEX documents_org_case_idx ON documents (organization_id, case_file_id, created_at);
            CREATE INDEX documents_uploaded_by_idx ON documents (uploaded_by);

            CREATE TABLE document_pages (
                id              uuid PRIMARY KEY,
                organization_id uuid NOT NULL,
                document_id     uuid NOT NULL,
                page_no         integer NOT NULL CHECK (page_no > 0),
                width_pt        numeric(8, 2) NOT NULL,
                height_pt       numeric(8, 2) NOT NULL,
                image_key       varchar(255) NOT NULL,
                image_width_px  integer NOT NULL,
                image_height_px integer NOT NULL,
                text_source     varchar(16) NOT NULL CHECK (text_source IN ('text_layer', 'ocr', 'none')),
                word_count      integer NOT NULL DEFAULT 0,
                created_at      timestamptz NULL,
                updated_at      timestamptz NULL,
                FOREIGN KEY (document_id, organization_id)
                    REFERENCES documents (id, organization_id) ON DELETE CASCADE,
                UNIQUE (document_id, page_no)
            );
            CREATE INDEX document_pages_org_idx ON document_pages (organization_id);
            SQL);

        foreach (['documents', 'document_pages'] as $table) {
            RowLevelSecurity::isolateByOrganization($table);
            RowLevelSecurity::grant($table, ['SELECT', 'INSERT', 'UPDATE', 'DELETE']);
        }
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            DROP TABLE IF EXISTS document_pages;
            DROP TABLE IF EXISTS documents;
            DROP INDEX IF EXISTS case_files_id_org_uq;
            SQL);
    }
};
