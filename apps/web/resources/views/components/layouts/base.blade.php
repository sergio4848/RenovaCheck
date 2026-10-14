@props(['title' => null, 'bodyClass' => ''])
<!doctype html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}" data-bs-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>{{ isset($title) ? $title.' · ' : '' }}RenovaCheck</title>
    <link rel="stylesheet" href="{{ asset('vendor/tabler/tabler.min.css') }}">
    <link rel="stylesheet" href="{{ asset('css/app.css') }}">
    <script src="{{ asset('js/theme.js') }}"></script>
</head>
<body class="{{ $bodyClass ?? '' }}">
    {{ $slot }}
    <script src="{{ asset('vendor/tabler/tabler.min.js') }}" defer></script>
    <script src="{{ asset('js/review.js') }}" defer></script>
</body>
</html>
