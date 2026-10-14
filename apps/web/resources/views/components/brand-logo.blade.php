@props(['height' => 28])
{{-- Two files so the logo keeps its contrast in both themes; app.css shows the one for the active theme. --}}
<img src="{{ asset('images/logo-horizontal.svg') }}" alt="RenovaCheck" height="{{ $height }}" class="brand-logo brand-logo-light">
<img src="{{ asset('images/logo-inverse.svg') }}" alt="RenovaCheck" height="{{ $height }}" class="brand-logo brand-logo-dark">
