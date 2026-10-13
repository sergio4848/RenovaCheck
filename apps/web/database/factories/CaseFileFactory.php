<?php

namespace Database\Factories;

use App\Models\CaseFile;
use App\Models\User;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<CaseFile>
 */
class CaseFileFactory extends Factory
{
    public function definition(): array
    {
        return [
            'reference' => sprintf('CP/2026/%04d', fake()->unique()->numberBetween(1, 9999)),
            'title' => 'Termomodernizacja domu jednorodzinnego',
            'status' => 'new',
            'created_by' => User::factory(),
        ];
    }
}
