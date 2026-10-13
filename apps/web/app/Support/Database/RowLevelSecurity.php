<?php

namespace App\Support\Database;

use Illuminate\Support\Facades\DB;

/**
 * DDL helpers for tenant isolation. Policies compare organization_id with app_current_org(),
 * which reads the app.organization_id setting written by App\Tenancy\TenantContext.
 * FORCE makes the policies apply to the table owner too; only superusers bypass them.
 */
final class RowLevelSecurity
{
    public static function appRole(): string
    {
        return (string) config('database.app_role');
    }

    /** Enable RLS with a single "same organization" policy for all commands. */
    public static function isolateByOrganization(string $table, string $column = 'organization_id'): void
    {
        DB::statement("ALTER TABLE {$table} ENABLE ROW LEVEL SECURITY");
        DB::statement("ALTER TABLE {$table} FORCE ROW LEVEL SECURITY");
        DB::statement(
            "CREATE POLICY {$table}_tenant_isolation ON {$table}
             USING ({$column} = app_current_org())
             WITH CHECK ({$column} = app_current_org())"
        );
    }

    /** @param  list<string>  $privileges */
    public static function grant(string $table, array $privileges): void
    {
        $role = self::quoteIdent(self::appRole());
        DB::statement(sprintf('GRANT %s ON %s TO %s', implode(', ', $privileges), $table, $role));
    }

    public static function quoteIdent(string $identifier): string
    {
        return '"'.str_replace('"', '""', $identifier).'"';
    }
}
