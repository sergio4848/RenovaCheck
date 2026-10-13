<?php

namespace App\Services\Antivirus;

interface Scanner
{
    /** 'clean' or 'skipped'; throws InfectedFile when a signature matches. */
    public function scan(string $path): string;
}
