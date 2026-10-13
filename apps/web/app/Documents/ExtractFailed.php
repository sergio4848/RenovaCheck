<?php

namespace App\Documents;

use RuntimeException;
use Throwable;

final class ExtractFailed extends RuntimeException
{
    public function __construct(public readonly string $errorCode, public readonly bool $retryable, ?Throwable $previous = null)
    {
        parent::__construct("Extraction failed: {$errorCode}", 0, $previous);
    }
}
