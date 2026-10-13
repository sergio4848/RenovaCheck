<x-layouts.base :title="__('Sign in')" body-class="d-flex flex-column">
<div class="page page-center">
    <div class="container container-tight py-4">
        <div class="text-center mb-4">
            <span class="fs-2 fw-bold">Renova<span class="text-primary">Check</span></span>
            <div class="text-secondary mt-1">{{ __('Document consistency checks for thermal modernisation projects') }}</div>
        </div>
        <div class="card card-md">
            <div class="card-body">
                <h2 class="h2 text-center mb-4">{{ __('Sign in to your account') }}</h2>
                @if ($errors->any())
                    <div class="alert alert-danger" role="alert">{{ $errors->first() }}</div>
                @endif
                <form method="POST" action="{{ route('login') }}" autocomplete="off" novalidate>
                    @csrf
                    <div class="mb-3">
                        <label class="form-label" for="email">{{ __('Email') }}</label>
                        <input type="email" id="email" name="email" value="{{ old('email') }}" class="form-control @error('email') is-invalid @enderror" required autofocus autocomplete="username">
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="password">{{ __('Password') }}</label>
                        <input type="password" id="password" name="password" class="form-control" required autocomplete="current-password">
                    </div>
                    <div class="mb-2">
                        <label class="form-check">
                            <input type="checkbox" class="form-check-input" name="remember" value="1">
                            <span class="form-check-label">{{ __('Remember me on this device') }}</span>
                        </label>
                    </div>
                    <div class="form-footer">
                        <button type="submit" class="btn btn-primary w-100">{{ __('Sign in') }}</button>
                    </div>
                </form>
            </div>
        </div>
        <div class="text-center text-secondary small mt-3">{{ __('Prototype — synthetic data only') }}</div>
    </div>
</div>
</x-layouts.base>
