<?php

namespace Tests\Feature;

use App\Enums\Role;
use Tests\TestCase;

class AuthorizationTest extends TestCase
{
    public function test_owner_sees_members_page(): void
    {
        $owner = $this->member(Role::Owner);

        $this->actingAs($owner->user)->get('/members')
            ->assertOk()
            ->assertSee($owner->user->email)
            ->assertSee('Właściciel');
    }

    public function test_reviewer_cannot_see_members_page_or_menu_entry(): void
    {
        $reviewer = $this->member(Role::Reviewer);

        $this->actingAs($reviewer->user)->get('/members')->assertForbidden();
        $this->actingAs($reviewer->user)->get('/cases')->assertOk()->assertDontSee('Członkowie');
    }

    public function test_both_roles_can_create_cases_and_read_the_event_log(): void
    {
        foreach ([Role::Owner, Role::Reviewer] as $role) {
            $membership = $this->member($role);
            $this->actingAs($membership->user)
                ->post('/cases', ['reference' => 'CP/'.$role->value, 'title' => 'Dom'])
                ->assertRedirect();
            $this->actingAs($membership->user)->get('/audit')->assertOk();
        }
    }
}
