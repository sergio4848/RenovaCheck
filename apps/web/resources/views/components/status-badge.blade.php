@props(['status'])
@php
    $classes = [
        'new' => 'bg-primary-subtle text-primary-emphasis',
        'in_review' => 'bg-warning-subtle text-warning-emphasis',
        'closed' => 'bg-success-subtle text-success-emphasis',
    ];
@endphp
<span {{ $attributes->merge(['class' => 'badge '.($classes[$status] ?? 'bg-secondary-subtle text-secondary-emphasis')]) }}>{{ __('status.'.$status) }}</span>
