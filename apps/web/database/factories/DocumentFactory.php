<?php

namespace Database\Factories;

use App\Models\Document;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<Document>
 */
class DocumentFactory extends Factory
{
    public function definition(): array
    {
        return [
            'original_name' => 'faktura.pdf',
            'mime' => 'application/pdf',
            'size_bytes' => 1024,
            'sha256' => hash('sha256', fake()->unique()->uuid()),
            'storage_key' => 'org/x/original.pdf',
            'status' => 'uploaded',
            'scan_status' => 'skipped',
        ];
    }
}
