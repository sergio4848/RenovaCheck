@props(['severity'])
@php
    $class = ['critical' => 'bg-danger-subtle text-danger-emphasis', 'warning' => 'bg-warning-subtle text-warning-emphasis', 'info' => 'bg-info-subtle text-info-emphasis'][$severity] ?? 'bg-secondary-subtle';
@endphp
<span {{ $attributes->merge(["class" => "badge {$class}", "data-severity" => $severity]) }}>{{ __('severity.'.$severity) }}@if (! $slot->isEmpty()) {{ $slot }}@endif</span>
