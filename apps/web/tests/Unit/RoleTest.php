<?php

namespace Tests\Unit;

use App\Enums\Permission;
use App\Enums\Role;
use PHPUnit\Framework\TestCase;

class RoleTest extends TestCase
{
    public function test_owner_has_every_permission(): void
    {
        foreach (Permission::cases() as $permission) {
            $this->assertTrue(Role::Owner->allows($permission), $permission->value);
        }
    }

    public function test_reviewer_cannot_manage_or_view_members(): void
    {
        $this->assertFalse(Role::Reviewer->allows(Permission::MembersView));
        $this->assertFalse(Role::Reviewer->allows(Permission::MembersManage));
        $this->assertTrue(Role::Reviewer->allows(Permission::FindingsDecide));
    }
}
