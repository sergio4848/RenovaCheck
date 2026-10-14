<?php

namespace Tests\Unit;

use App\Services\Antivirus\ClamdScanner;
use App\Services\Antivirus\InfectedFile;
use PHPUnit\Framework\TestCase;

class ClamdScannerTest extends TestCase
{
    private const EICAR = 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*';

    /** A minimal clamd INSTREAM server in a child process; returns [process, port]. */
    private function fakeClamd(): array
    {
        $server = <<<'PHP'
            $s = stream_socket_server('tcp://127.0.0.1:0');
            fwrite(STDOUT, explode(':', stream_socket_get_name($s, false))[1]."\n");
            $c = stream_socket_accept($s, 10);
            $cmd = fread($c, 10);
            $data = '';
            while (true) {
                $len = unpack('N', fread($c, 4))[1];
                if ($len === 0) { break; }
                while ($len > 0) { $chunk = fread($c, $len); $data .= $chunk; $len -= strlen($chunk); }
            }
            fwrite($c, $cmd === "zINSTREAM\0" && str_contains($data, 'EICAR') ? "stream: Eicar-Test-Signature FOUND\0" : "stream: OK\0");
            fclose($c);
            PHP;
        $process = proc_open([PHP_BINARY, '-r', $server], [1 => ['pipe', 'w']], $pipes);
        $port = (int) trim((string) fgets($pipes[1]));

        return [$process, $port];
    }

    private function file(string $content): string
    {
        $path = tempnam(sys_get_temp_dir(), 'av');
        file_put_contents($path, $content);

        return $path;
    }

    public function test_clean_file(): void
    {
        [$process, $port] = $this->fakeClamd();
        $this->assertSame('clean', ClamdScanner::tcp('127.0.0.1', $port)->scan($this->file(str_repeat('a', 200000))));
        proc_close($process);
    }

    public function test_infected_file(): void
    {
        [$process, $port] = $this->fakeClamd();
        try {
            $this->expectException(InfectedFile::class);
            ClamdScanner::tcp('127.0.0.1', $port)->scan($this->file(self::EICAR));
        } finally {
            proc_close($process);
        }
    }

    public function test_unreachable_clamd_fails_closed(): void
    {
        $this->expectException(\RuntimeException::class);
        ClamdScanner::tcp('127.0.0.1', 1, 0.5)->scan($this->file('x'));
    }
}
