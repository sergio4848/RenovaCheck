<?php

namespace App\Http\Requests;

use App\Tenancy\TenantContext;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreCaseFileRequest extends FormRequest
{
    /** @return array<string, mixed> */
    public function rules(): array
    {
        return [
            'reference' => [
                'required', 'string', 'max:64', 'regex:/^[\pL\pN\/\-_.]+$/u',
                Rule::unique('case_files', 'reference')
                    ->where('organization_id', app(TenantContext::class)->requireOrganizationId()),
            ],
            'title' => ['required', 'string', 'max:200'],
        ];
    }

    public function attributes(): array
    {
        return [
            'reference' => __('Reference'),
            'title' => __('Title'),
        ];
    }
}
