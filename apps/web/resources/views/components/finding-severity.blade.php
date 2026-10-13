@props(['severity'])
@php
    $class = ['critical' => 'bg-danger-subtle text-danger-emphasis', 'warning' => 'bg-warning-subtle text-warning-emphasis', 'info' => 'bg-info-subtle text-info-emphasis'][$severity] ?? 'bg-secondary-subtle';
@endphp
<span {{ $attributes->merge(['class' => "badge {$class}"]) }}>{{ __('severity.'.$severity) }}</span>
