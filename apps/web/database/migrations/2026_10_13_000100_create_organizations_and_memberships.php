<?php

use App\Support\Database\RowLevelSecurity;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('organizations', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->string('name', 160);
            $table->string('slug', 64)->unique();
            $table->timestamps();
        });

        Schema::create('memberships', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('organization_id')->constrained()->cascadeOnDelete();
            $table->foreignUuid('user_id')->constrained()->cascadeOnDelete();
            $table->string('role', 16);
            $table->timestamps();
            $table->unique(['organization_id', 'user_id']);
            // The unique index leads with organization_id; user lookups need their own index.
            $table->index('user_id');
        });
        DB::statement("ALTER TABLE memberships ADD CONSTRAINT memberships_role_check CHECK (role IN ('owner', 'reviewer'))");

        // Memberships are visible inside the active organization, and a user can always see their
        // own memberships (needed to pick the active organization before it is set).
        DB::unprepared(<<<'SQL'
            ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
            ALTER TABLE memberships FORCE ROW LEVEL SECURITY;
            CREATE POLICY memberships_visible ON memberships FOR SELECT
                USING (organization_id = app_current_org() OR user_id = app_current_user());
            CREATE POLICY memberships_write ON memberships FOR ALL
                USING (organization_id = app_current_org())
                WITH CHECK (organization_id = app_current_org());

            ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
            ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
            CREATE POLICY organizations_visible ON organizations FOR SELECT
                USING (
                    id = app_current_org()
                    OR EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.organization_id = organizations.id AND m.user_id = app_current_user()
                    )
                );
            CREATE POLICY organizations_update ON organizations FOR UPDATE
                USING (id = app_current_org())
                WITH CHECK (id = app_current_org());
            SQL);

        // Users are global identities, visible to the user themself and to members of the active
        // organization. Sign-in resolves an e-mail to an id through a SECURITY DEFINER function, so
        // the runtime role never needs to read other users' rows.
        DB::unprepared(<<<'SQL'
            ALTER TABLE users ENABLE ROW LEVEL SECURITY;
            ALTER TABLE users FORCE ROW LEVEL SECURITY;
            CREATE POLICY users_visible ON users FOR SELECT
                USING (
                    id = app_current_user()
                    OR EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_id = users.id AND m.organization_id = app_current_org()
                    )
                );
            CREATE POLICY users_update_self ON users FOR UPDATE
                USING (id = app_current_user())
                WITH CHECK (id = app_current_user());

            CREATE OR REPLACE FUNCTION auth_user_id_by_email(p_email text) RETURNS uuid
                LANGUAGE sql STABLE SECURITY DEFINER
                SET search_path = public, pg_temp
                AS $$ SELECT id FROM public.users WHERE email = p_email $$;
            REVOKE ALL ON FUNCTION auth_user_id_by_email(text) FROM PUBLIC;
            SQL);
        $role = RowLevelSecurity::quoteIdent(RowLevelSecurity::appRole());
        DB::statement("GRANT EXECUTE ON FUNCTION auth_user_id_by_email(text) TO {$role}");

        // Organizations are provisioned by operators (seed/migrator), never by the web app.
        RowLevelSecurity::grant('organizations', ['SELECT', 'UPDATE']);
        RowLevelSecurity::grant('memberships', ['SELECT', 'INSERT', 'UPDATE', 'DELETE']);
    }

    public function down(): void
    {
        // These policies reference memberships.
        DB::unprepared(<<<'SQL'
            DROP FUNCTION IF EXISTS auth_user_id_by_email(text);
            DROP POLICY IF EXISTS users_visible ON users;
            DROP POLICY IF EXISTS users_update_self ON users;
            ALTER TABLE users NO FORCE ROW LEVEL SECURITY;
            ALTER TABLE users DISABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS organizations_visible ON organizations;
            SQL);
        Schema::dropIfExists('memberships');
        Schema::dropIfExists('organizations');
    }
};
