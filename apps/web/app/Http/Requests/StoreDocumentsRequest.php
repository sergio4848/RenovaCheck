<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class StoreDocumentsRequest extends FormRequest
{
    /** @return array<string, mixed> */
    public function rules(): array
    {
        return [
            'files' => ['required', 'array', 'min:1', 'max:'.config('documents.max_files_per_upload')],
            // mimetypes is checked with finfo on the content; DocumentIntake re-checks magic bytes.
            'files.*' => [
                'required', 'file', 'max:'.config('documents.max_file_kb'),
                'mimetypes:application/pdf,image/png,image/jpeg', 'extensions:pdf,png,jpg,jpeg',
            ],
        ];
    }

    public function attributes(): array
    {
        return ['files' => __('Files'), 'files.*' => __('File')];
    }
}
