<?php

namespace Tests\Feature\Auth;

use App\Enums\Role;
use App\Models\User;
use Tests\TestCase;

class LoginTest extends TestCase
{
    public function test_login_page_is_polish_by_default(): void
    {
        $this->get('/login')
            ->assertOk()
            ->assertSee('Zaloguj się do konta')
            ->assertSee('Prototyp — wyłącznie dane syntetyczne');
    }

    public function test_guest_is_redirected_to_login(): void
    {
        $this->get('/cases')->assertRedirect('/login');
    }

    public function test_member_can_sign_in_and_lands_on_cases(): void
    {
        $membership = $this->member(Role::Reviewer);

        $this->post('/login', ['email' => $membership->user->email, 'password' => 'password'])
            ->assertRedirect('/cases');
        $this->assertAuthenticatedAs($membership->user);

        $this->get('/cases')->assertOk()->assertSee($membership->organization->name);
    }

    public function test_wrong_password_is_rejected_without_revealing_which_field(): void
    {
        $membership = $this->member();

        $this->from('/login')
            ->post('/login', ['email' => $membership->user->email, 'password' => 'wrong'])
            ->assertRedirect('/login')
            ->assertSessionHasErrors(['email' => 'Nieprawidłowy e-mail lub hasło.']);
        $this->assertGuest();
    }

    public function test_login_is_throttled_after_five_failures(): void
    {
        $membership = $this->member();
        for ($i = 0; $i < 5; $i++) {
            $this->post('/login', ['email' => $membership->user->email, 'password' => 'wrong']);
        }

        $this->post('/login', ['email' => $membership->user->email, 'password' => 'password'])
            ->assertStatus(429);
        $this->assertGuest();
    }

    public function test_user_without_membership_is_signed_out(): void
    {
        $user = $this->asOwner(fn () => User::factory()->create());

        $this->actingAs($user)->get('/cases')
            ->assertRedirect('/login')
            ->assertSessionHasErrors('email');
        $this->assertGuest();
    }

    public function test_sign_out(): void
    {
        $membership = $this->member();

        $this->actingAs($membership->user)->post('/logout')->assertRedirect('/');
        $this->assertGuest();
    }
}
