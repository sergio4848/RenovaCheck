@props(['title' => null])
<x-layouts.base :title="$title">
<div class="page">
    <header class="navbar navbar-expand-md d-print-none border-bottom">
        <div class="container-xl">
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbar-menu" aria-controls="navbar-menu" aria-expanded="false" aria-label="{{ __('Toggle navigation') }}">
                <span class="navbar-toggler-icon"></span>
            </button>
            <a href="{{ route('cases.index') }}" class="navbar-brand me-3 fw-bold text-decoration-none">
                <span>Renova<span class="text-primary">Check</span></span>
            </a>
            <div class="navbar-nav flex-row order-md-last align-items-center gap-2">
                <button type="button" class="btn btn-ghost-secondary btn-icon" data-theme-toggle aria-label="{{ __('Toggle dark mode') }}">
                    <x-icon name="moon" class="hide-theme-dark" /><x-icon name="sun" class="hide-theme-light" />
                </button>
                @if ($tenant->organization())
                    <div class="nav-item dropdown">
                        <a href="#" class="nav-link px-2" data-bs-toggle="dropdown" aria-label="{{ __('Organization') }}">
                            <span class="d-none d-sm-inline text-truncate org-name">{{ $tenant->organization()->name }}</span>
                            <span class="badge bg-secondary-subtle text-secondary-emphasis ms-2">{{ $tenant->role()->label() }}</span>
                        </a>
                        <div class="dropdown-menu dropdown-menu-end">
                            <h6 class="dropdown-header">{{ __('Switch organization') }}</h6>
                            @foreach (auth()->user()->memberships()->with('organization')->get() as $membership)
                                <form method="POST" action="{{ route('organizations.switch') }}">
                                    @csrf
                                    <input type="hidden" name="organization_id" value="{{ $membership->organization_id }}">
                                    <button type="submit" class="dropdown-item {{ $membership->organization_id === $tenant->organizationId() ? 'active' : '' }}">
                                        {{ $membership->organization->name }}
                                    </button>
                                </form>
                            @endforeach
                        </div>
                    </div>
                @endif
                <div class="nav-item dropdown">
                    <a href="#" class="nav-link d-flex lh-1 p-0 px-2" data-bs-toggle="dropdown" aria-label="{{ __('User menu') }}">
                        <span class="avatar avatar-sm">{{ mb_strtoupper(mb_substr(auth()->user()->name, 0, 1)) }}</span>
                        <div class="d-none d-xl-block ps-2">
                            <div>{{ auth()->user()->name }}</div>
                            <div class="mt-1 small text-secondary">{{ auth()->user()->email }}</div>
                        </div>
                    </a>
                    <div class="dropdown-menu dropdown-menu-end">
                        <form method="POST" action="{{ route('logout') }}">
                            @csrf
                            <button type="submit" class="dropdown-item">{{ __('Sign out') }}</button>
                        </form>
                    </div>
                </div>
            </div>
            <div class="collapse navbar-collapse" id="navbar-menu">
                <ul class="navbar-nav">
                    @can('cases.view')
                        <li class="nav-item {{ request()->routeIs('cases.*') ? 'active' : '' }}">
                            <a class="nav-link" href="{{ route('cases.index') }}"><x-icon name="folders" class="nav-link-icon" /><span class="nav-link-title text-nowrap">{{ __('Cases') }}</span></a>
                        </li>
                    @endcan
                    @can('members.view')
                        <li class="nav-item {{ request()->routeIs('members.*') ? 'active' : '' }}">
                            <a class="nav-link" href="{{ route('members.index') }}"><x-icon name="users" class="nav-link-icon" /><span class="nav-link-title text-nowrap">{{ __('Members') }}</span></a>
                        </li>
                    @endcan
                    @can('audit.view')
                        <li class="nav-item {{ request()->routeIs('audit.*') ? 'active' : '' }}">
                            <a class="nav-link" href="{{ route('audit.index') }}"><x-icon name="list-check" class="nav-link-icon" /><span class="nav-link-title text-nowrap">{{ __('Event log') }}</span></a>
                        </li>
                    @endcan
                </ul>
            </div>
        </div>
    </header>
    <div class="page-wrapper">
        {{ $slot }}
        <footer class="footer footer-transparent d-print-none">
            <div class="container-xl text-secondary small">
                RenovaCheck · {{ __('Prototype — synthetic data only') }}
            </div>
        </footer>
    </div>
</div>
</x-layouts.base>
