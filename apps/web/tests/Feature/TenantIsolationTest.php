<?php

namespace Tests\Feature;

use App\Enums\Role;
use App\Models\CaseFile;
use App\Models\Membership;
use App\Services\AuditLog;
use App\Tenancy\MissingTenantContext;
use App\Tenancy\TenantContext;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * Two organizations with data; every path must return only the active organization's rows.
 * Scenarios ported from emlakpro apps/api/test/tenant-isolation.int-spec.ts — Copyright (c) 2026 Sergen Şahin.
 */
class TenantIsolationTest extends TestCase
{
    private Membership $alfa;

    private Membership $beta;

    private CaseFile $alfaCase;

    private CaseFile $betaCase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->alfa = $this->member(Role::Owner);
        $this->beta = $this->member(Role::Owner);
        $this->alfaCase = $this->caseIn($this->alfa, 'CP/A/1');
        $this->betaCase = $this->caseIn($this->beta, 'CP/B/1');
        app(TenantContext::class)->clear();
    }

    private function caseIn(Membership $membership, string $reference): CaseFile
    {
        return app(TenantContext::class)->run($membership, function () use ($membership, $reference) {
            $case = CaseFile::create(['reference' => $reference, 'title' => 'Dom', 'created_by' => $membership->user_id]);
            app(AuditLog::class)->record('case.created', $case);

            return $case;
        });
    }

    public function test_case_list_shows_only_own_organization(): void
    {
        $this->actingAs($this->alfa->user)->get('/cases')
            ->assertOk()
            ->assertSee('CP/A/1')
            ->assertDontSee('CP/B/1');
    }

    public function test_other_organizations_case_is_not_found_not_forbidden(): void
    {
        $this->actingAs($this->alfa->user)->get('/cases/'.$this->betaCase->id)->assertNotFound();
    }

    public function test_event_log_shows_only_own_organization(): void
    {
        $response = $this->actingAs($this->alfa->user)->get('/audit')->assertOk();
        $this->assertSame(1, substr_count($response->getContent(), 'Utworzono sprawę'));
    }

    public function test_unfiltered_sql_is_still_limited_by_row_level_security(): void
    {
        app(TenantContext::class)->activate($this->alfa);

        $this->assertSame([$this->alfaCase->id], DB::table('case_files')->pluck('id')->all());
        $this->assertSame(1, DB::table('audit_events')->count());
        $this->assertSame(
            [$this->alfa->organization_id],
            DB::table('organizations')->pluck('id')->all(),
        );
    }

    public function test_without_tenant_context_rls_returns_nothing_and_models_fail_closed(): void
    {
        $this->assertSame(0, DB::table('case_files')->count());
        $this->assertSame(0, DB::table('audit_events')->count());

        $this->expectException(MissingTenantContext::class);
        CaseFile::query()->count();
    }

    public function test_writing_into_another_organization_is_rejected_by_the_database(): void
    {
        app(TenantContext::class)->activate($this->alfa);

        $this->expectException(QueryException::class);
        $this->expectExceptionMessage('row-level security');
        DB::table('case_files')->insert([
            'id' => (string) Str::uuid(),
            'organization_id' => $this->beta->organization_id,
            'reference' => 'CP/X',
            'title' => 'X',
            'status' => 'new',
            'created_by' => $this->alfa->user_id,
        ]);
    }

    public function test_updates_cannot_reach_other_organizations_rows(): void
    {
        app(TenantContext::class)->activate($this->alfa);

        $affected = DB::table('case_files')->where('id', $this->betaCase->id)->update(['title' => 'hijacked']);

        $this->assertSame(0, $affected);
    }

    public function test_user_sees_own_memberships_but_not_other_members_of_foreign_organizations(): void
    {
        $shared = $this->member(Role::Reviewer, $this->beta->organization, $this->alfa->user);
        app(TenantContext::class)->activate($this->alfa);

        $visible = DB::table('memberships')->pluck('id')->sort()->values()->all();

        $expected = collect([$this->alfa->id, $shared->id])->sort()->values()->all();
        $this->assertSame($expected, $visible, 'beta owner membership must stay hidden');
    }

    public function test_users_of_other_organizations_are_invisible(): void
    {
        app(TenantContext::class)->activate($this->alfa);

        $this->assertSame([$this->alfa->user_id], DB::table('users')->pluck('id')->all());
        $this->assertSame(0, DB::table('users')->where('id', $this->beta->user_id)->update(['name' => 'x']));
    }

    public function test_sign_in_lookup_does_not_expose_other_users(): void
    {
        $row = DB::selectOne('SELECT auth_user_id_by_email(?) AS id', [$this->beta->user->email]);

        $this->assertSame($this->beta->user_id, $row->id);
        $this->assertSame(0, DB::table('users')->count(), 'lookup must not widen row visibility');
    }

    public function test_switching_to_an_organization_without_membership_is_not_found(): void
    {
        $this->actingAs($this->alfa->user)
            ->post('/organizations/switch', ['organization_id' => $this->beta->organization_id])
            ->assertNotFound();
    }

    public function test_switching_to_a_member_organization_changes_the_visible_data(): void
    {
        $this->member(Role::Reviewer, $this->beta->organization, $this->alfa->user);

        $this->actingAs($this->alfa->user)
            ->post('/organizations/switch', ['organization_id' => $this->beta->organization_id])
            ->assertRedirect('/cases');

        $this->actingAs($this->alfa->user)->get('/cases')
            ->assertSee('CP/B/1')
            ->assertDontSee('CP/A/1');
    }

    public function test_same_reference_is_allowed_in_different_organizations(): void
    {
        $this->actingAs($this->beta->user)
            ->post('/cases', ['reference' => 'CP/A/1', 'title' => 'Dom'])
            ->assertSessionHasNoErrors();
    }
}
