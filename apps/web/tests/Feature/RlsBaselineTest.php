<?php

namespace Tests\Feature;

use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * Structural guarantees, checked against the catalog so a new table cannot silently skip them.
 * Idea from konstela supabase/tests/rls_baseline_test.sql — Copyright (c) 2026 Sergen Şahin.
 */
class RlsBaselineTest extends TestCase
{
    public function test_every_tenant_table_has_forced_row_level_security(): void
    {
        $tables = DB::select(<<<'SQL'
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relkind = 'r'
               AND (EXISTS (SELECT 1 FROM information_schema.columns col
                             WHERE col.table_schema = 'public' AND col.table_name = c.relname
                               AND col.column_name = 'organization_id')
                    OR c.relname IN ('organizations', 'users'))
            SQL);

        $this->assertNotEmpty($tables);
        foreach ($tables as $table) {
            $this->assertTrue($table->relrowsecurity, "{$table->relname}: RLS not enabled");
            $this->assertTrue($table->relforcerowsecurity, "{$table->relname}: RLS not forced");
        }
    }

    public function test_runtime_role_cannot_bypass_rls_or_own_tables(): void
    {
        $role = DB::selectOne(
            'SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user'
        );
        $owned = DB::selectOne(
            "SELECT count(*) AS n FROM pg_tables WHERE schemaname = 'public' AND tableowner = current_user"
        );

        $this->assertSame(config('database.app_role'), DB::selectOne('SELECT current_user AS u')->u);
        $this->assertFalse($role->rolsuper);
        $this->assertFalse($role->rolbypassrls);
        $this->assertSame(0, (int) $owned->n);
    }

    public function test_runtime_role_cannot_create_organizations(): void
    {
        $this->expectException(QueryException::class);
        $this->expectExceptionMessage('permission denied');
        DB::table('organizations')->insert(['id' => (string) Str::uuid(), 'name' => 'X', 'slug' => 'x']);
    }

    public function test_runtime_role_cannot_create_temporary_tables(): void
    {
        // Temp tables could shadow public tables inside unqualified function bodies.
        $this->expectException(QueryException::class);
        $this->expectExceptionMessage('permission denied');
        DB::statement('CREATE TEMP TABLE audit_events (organization_id uuid, hash char(64), id bigint)');
    }

    public function test_runtime_role_has_no_update_or_delete_privilege_on_audit_events(): void
    {
        $privileges = DB::selectOne(<<<'SQL'
            SELECT has_table_privilege(current_user, 'audit_events', 'UPDATE') AS can_update,
                   has_table_privilege(current_user, 'audit_events', 'DELETE') AS can_delete,
                   has_table_privilege(current_user, 'audit_events', 'TRUNCATE') AS can_truncate
            SQL);

        $this->assertFalse($privileges->can_update);
        $this->assertFalse($privileges->can_delete);
        $this->assertFalse($privileges->can_truncate);
    }
}
