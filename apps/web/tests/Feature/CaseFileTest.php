<?php

namespace Tests\Feature;

use App\Enums\Role;
use App\Models\CaseFile;
use App\Tenancy\TenantContext;
use Tests\TestCase;

class CaseFileTest extends TestCase
{
    public function test_creating_a_case_redirects_to_its_page_with_history(): void
    {
        $owner = $this->member(Role::Reviewer);

        $response = $this->actingAs($owner->user)
            ->post('/cases', ['reference' => 'CP/2026/0001', 'title' => 'Dom w Zielonowie']);

        app(TenantContext::class)->activate($owner);
        $case = CaseFile::query()->firstOrFail();
        $response->assertRedirect('/cases/'.$case->id);
        $this->assertSame('new', $case->status);
        $this->assertSame($owner->organization_id, $case->organization_id);

        $this->actingAs($owner->user)->get('/cases/'.$case->id)
            ->assertOk()
            ->assertSee('Dom w Zielonowie')
            ->assertSee('Utworzono sprawę');
    }

    public function test_reference_is_required_unique_and_well_formed(): void
    {
        $owner = $this->member();
        $this->actingAs($owner->user)->post('/cases', ['reference' => 'CP/1', 'title' => 'A']);

        $this->actingAs($owner->user)->post('/cases', ['reference' => 'CP/1', 'title' => 'B'])
            ->assertSessionHasErrors(['reference' => 'Taka wartość pola Sygnatura już istnieje.']);
        $this->actingAs($owner->user)->post('/cases', ['reference' => '<script>', 'title' => 'B'])
            ->assertSessionHasErrors('reference');
        $this->actingAs($owner->user)->post('/cases', ['reference' => '', 'title' => ''])
            ->assertSessionHasErrors(['reference', 'title']);
    }

    public function test_list_can_be_filtered_by_status(): void
    {
        $owner = $this->member();
        app(TenantContext::class)->run($owner, function () use ($owner) {
            CaseFile::create(['reference' => 'CP/OPEN', 'title' => 'A', 'created_by' => $owner->user_id]);
            CaseFile::create(['reference' => 'CP/DONE', 'title' => 'B', 'status' => 'closed', 'created_by' => $owner->user_id]);
        });

        $this->actingAs($owner->user)->get('/cases?status=closed')
            ->assertOk()
            ->assertSee('CP/DONE')
            ->assertDontSee('CP/OPEN');
    }
}
