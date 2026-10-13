<?php

namespace App\Documents;

/** File type by content (magic bytes), never by name or browser-declared type. */
final class FileSniffer
{
    public const EXTENSIONS = ['application/pdf' => 'pdf', 'image/png' => 'png', 'image/jpeg' => 'jpg'];

    public static function mime(string $path): ?string
    {
        $handle = @fopen($path, 'rb');
        if ($handle === false) {
            return null;
        }
        $head = (string) fread($handle, 1024);
        fclose($handle);

        return match (true) {
            str_starts_with(ltrim($head, "\0\t\r\n\f "), '%PDF-') => 'application/pdf',
            str_starts_with($head, "\x89PNG\r\n\x1a\n") => 'image/png',
            str_starts_with($head, "\xff\xd8\xff") => 'image/jpeg',
            default => null,
        };
    }
}
