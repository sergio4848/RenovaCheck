<?php

namespace App\Auth;

use App\Tenancy\TenantContext;
use Illuminate\Auth\EloquentUserProvider;
use Illuminate\Contracts\Auth\Authenticatable;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Eloquent user provider for a users table under row-level security: a user row is only
 * visible once app.user_id names it. The id comes from the encrypted session, the remember
 * cookie, or the auth_user_id_by_email() lookup during sign-in.
 */
class TenantAwareUserProvider extends EloquentUserProvider
{
    public function retrieveById($identifier): ?Authenticatable
    {
        if (! $this->identify($identifier)) {
            return null;
        }

        return parent::retrieveById($identifier);
    }

    public function retrieveByToken($identifier, #[\SensitiveParameter] $token): ?Authenticatable
    {
        if (! $this->identify($identifier)) {
            return null;
        }

        return parent::retrieveByToken($identifier, $token);
    }

    public function retrieveByCredentials(#[\SensitiveParameter] array $credentials): ?Authenticatable
    {
        $email = $credentials['email'] ?? null;
        if (! is_string($email) || $email === '') {
            return null;
        }

        $id = DB::selectOne('SELECT auth_user_id_by_email(?) AS id', [$email])?->id;

        return $this->identify($id) ? parent::retrieveById($id) : null;
    }

    private function identify(mixed $identifier): bool
    {
        if (! is_string($identifier) || ! Str::isUuid($identifier)) {
            return false;
        }
        app(TenantContext::class)->identifyUserId($identifier);

        return true;
    }
}
