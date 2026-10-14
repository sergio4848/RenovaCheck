<?php

namespace App\Services\Antivirus;

/** Used when ClamAV is not enabled (compose profile "av" is off): the upload is recorded as not scanned. */
final class SkippingScanner implements Scanner
{
    public function scan(string $path): string
    {
        return 'skipped';
    }
}
