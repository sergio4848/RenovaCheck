<?php

namespace App\Tenancy;

use RuntimeException;

final class MissingTenantContext extends RuntimeException
{
    public function __construct()
    {
        parent::__construct('No active organization in the current context.');
    }
}
