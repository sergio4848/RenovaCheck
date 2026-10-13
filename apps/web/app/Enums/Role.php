<?php

namespace App\Enums;

enum Role: string
{
    case Owner = 'owner';
    case Reviewer = 'reviewer';

    /** @return list<Permission> */
    public function permissions(): array
    {
        return match ($this) {
            self::Owner => Permission::cases(),
            self::Reviewer => [
                Permission::CasesView,
                Permission::CasesCreate,
                Permission::FindingsDecide,
                Permission::AuditView,
            ],
        };
    }

    public function allows(Permission $permission): bool
    {
        return in_array($permission, $this->permissions(), true);
    }

    public function label(): string
    {
        return __('role.'.$this->value);
    }
}
