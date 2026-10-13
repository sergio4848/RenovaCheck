<?php

namespace App\Services\Antivirus;

use Closure;
use RuntimeException;

/**
 * Streams a file to clamd with the INSTREAM command (zINSTREAM, 4-byte big-endian chunk sizes,
 * zero-length terminator). Any reply other than "OK" or "FOUND" is an error: the upload fails closed.
 */
final class ClamdScanner implements Scanner
{
    private const CHUNK = 65536;

    /** @param  Closure(): resource  $connect */
    public function __construct(private readonly Closure $connect) {}

    public static function tcp(string $host, int $port, float $timeout = 10.0): self
    {
        return new self(function () use ($host, $port, $timeout) {
            set_error_handler(static fn () => true); // connection errors are reported by the return value
            try {
                $socket = stream_socket_client("tcp://{$host}:{$port}", $errno, $error, $timeout);
            } finally {
                restore_error_handler();
            }
            if ($socket === false) {
                throw new RuntimeException('ClamAV is unavailable.');
            }
            stream_set_timeout($socket, (int) ceil($timeout));

            return $socket;
        });
    }

    public function scan(string $path): string
    {
        $socket = ($this->connect)();
        $file = fopen($path, 'rb');
        try {
            fwrite($socket, "zINSTREAM\0");
            while (! feof($file)) {
                $chunk = (string) fread($file, self::CHUNK);
                if ($chunk === '') {
                    break;
                }
                fwrite($socket, pack('N', strlen($chunk)).$chunk);
            }
            fwrite($socket, pack('N', 0));
            $reply = trim((string) stream_get_contents($socket), "\0\r\n ");
        } finally {
            fclose($file);
            fclose($socket);
        }

        if (str_ends_with($reply, 'FOUND')) {
            throw new InfectedFile;
        }
        if (! str_ends_with($reply, 'OK')) {
            throw new RuntimeException('Unexpected ClamAV reply.');
        }

        return 'clean';
    }
}
