<?php

namespace Database\Factories;

use App\Models\Organization;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Str;

/**
 * @extends Factory<Organization>
 */
class OrganizationFactory extends Factory
{
    public function definition(): array
    {
        $name = 'Biuro '.fake()->unique()->lastName().' (DEMO)';

        return ['name' => $name, 'slug' => Str::slug($name)];
    }
}
