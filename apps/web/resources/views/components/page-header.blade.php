@props(['title', 'pretitle' => null])
<div class="page-header d-print-none">
    <div class="container-xl">
        <div class="row g-2 align-items-center">
            <div class="col">
                @if ($pretitle)
                    <div class="page-pretitle">{{ $pretitle }}</div>
                @endif
                <h2 class="page-title">{{ $title }}</h2>
            </div>
            @isset($actions)
                <div class="col-auto ms-auto d-print-none">{{ $actions }}</div>
            @endisset
        </div>
    </div>
</div>
