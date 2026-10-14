@props(['status'])
@php
    $classes = [
        'uploaded' => 'bg-secondary-subtle text-secondary-emphasis',
        'processing' => 'bg-primary-subtle text-primary-emphasis',
        'processed' => 'bg-success-subtle text-success-emphasis',
        'failed' => 'bg-danger-subtle text-danger-emphasis',
    ];
@endphp
<span {{ $attributes->merge(['class' => 'badge '.($classes[$status] ?? 'bg-secondary-subtle text-secondary-emphasis')]) }}>{{ __('doc_status.'.$status) }}</span>
