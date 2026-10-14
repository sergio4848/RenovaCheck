@props(['name'])
@php
    // Outline glyphs from Tabler Icons 3.35.0 (MIT, see resources/icons/LICENSE).
    $paths = [
        'moon' => '<path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1 -8.313 -12.454z"/>',
        'sun' => '<path d="M12 12m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0"/> <path d="M3 12h1m8 -9v1m8 8h1m-9 8v1m-6.4 -15.4l.7 .7m12.1 -.7l-.7 .7m0 11.4l.7 .7m-12.1 -.7l-.7 .7"/>',
        'folders' => '<path d="M9 3h3l2 2h5a2 2 0 0 1 2 2v7a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-9a2 2 0 0 1 2 -2"/> <path d="M17 16v2a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-9a2 2 0 0 1 2 -2h2"/>',
        'users' => '<path d="M9 7m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0"/> <path d="M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"/> <path d="M16 3.13a4 4 0 0 1 0 7.75"/> <path d="M21 21v-2a4 4 0 0 0 -3 -3.85"/>',
        'list-check' => '<path d="M3.5 5.5l1.5 1.5l2.5 -2.5"/> <path d="M3.5 11.5l1.5 1.5l2.5 -2.5"/> <path d="M3.5 17.5l1.5 1.5l2.5 -2.5"/> <path d="M11 6l9 0"/> <path d="M11 12l9 0"/> <path d="M11 18l9 0"/>',
        'plus' => '<path d="M12 5l0 14"/> <path d="M5 12l14 0"/>',
        'alert-triangle' => '<path d="M12 9v4"/> <path d="M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636 -2.87l-8.106 -13.536a1.914 1.914 0 0 0 -3.274 0z"/> <path d="M12 16h.01"/>',
        'shield-check' => '<path d="M11.46 20.846a12 12 0 0 1 -7.96 -14.846a12 12 0 0 0 8.5 -3a12 12 0 0 0 8.5 3a12 12 0 0 1 -.09 7.06"/> <path d="M15 19l2 2l4 -4"/>',
        'file-text' => '<path d="M14 3v4a1 1 0 0 0 1 1h4"/> <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"/> <path d="M9 9l1 0"/> <path d="M9 13l6 0"/> <path d="M9 17l6 0"/>',
        'search' => '<path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0"/> <path d="M21 21l-6 -6"/>',
        'circle-check' => '<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/> <path d="M9 12l2 2l4 -4"/>',
        'arrow-left' => '<path d="M5 12l14 0"/> <path d="M5 12l6 6"/> <path d="M5 12l6 -6"/>',
        'lock' => '<path d="M5 13a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v6a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-6z"/> <path d="M11 16a1 1 0 1 0 2 0a1 1 0 0 0 -2 0"/> <path d="M8 11v-4a4 4 0 1 1 8 0v4"/>',
        'building' => '<path d="M3 21l18 0"/> <path d="M9 8l1 0"/> <path d="M9 12l1 0"/> <path d="M9 16l1 0"/> <path d="M14 8l1 0"/> <path d="M14 12l1 0"/> <path d="M14 16l1 0"/> <path d="M5 21v-16a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v16"/>',
    ];
@endphp
<svg xmlns="http://www.w3.org/2000/svg" {{ $attributes->merge(['class' => 'icon']) }} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{!! $paths[$name] ?? '' !!}</svg>
