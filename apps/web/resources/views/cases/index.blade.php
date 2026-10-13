<x-layouts.app :title="__('Cases')">
    <x-page-header :title="__('Cases')" :pretitle="$tenant->organization()->name">
        @can('cases.create')
            <x-slot:actions>
                <button type="button" class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#new-case" aria-expanded="{{ $errors->any() ? 'true' : 'false' }}" aria-controls="new-case">
                    <x-icon name="plus" /> {{ __('New case') }}
                </button>
            </x-slot:actions>
        @endcan
    </x-page-header>
    <div class="page-body">
        <div class="container-xl">
            @if (session('status'))
                <div class="alert alert-success" role="status">{{ session('status') }}</div>
            @endif

            @can('cases.create')
                <div class="collapse {{ $errors->any() ? 'show' : '' }} mb-3" id="new-case">
                    <form method="POST" action="{{ route('cases.store') }}" class="card">
                        @csrf
                        <div class="card-body">
                            <div class="row g-3">
                                <div class="col-md-4">
                                    <label class="form-label required" for="reference">{{ __('Reference') }}</label>
                                    <input id="reference" name="reference" value="{{ old('reference') }}" class="form-control @error('reference') is-invalid @enderror" placeholder="CP/2026/0001" required maxlength="64">
                                    @error('reference')<div class="invalid-feedback">{{ $message }}</div>@enderror
                                </div>
                                <div class="col-md-8">
                                    <label class="form-label required" for="title">{{ __('Title') }}</label>
                                    <input id="title" name="title" value="{{ old('title') }}" class="form-control @error('title') is-invalid @enderror" required maxlength="200">
                                    @error('title')<div class="invalid-feedback">{{ $message }}</div>@enderror
                                </div>
                            </div>
                        </div>
                        <div class="card-footer text-end">
                            <button type="submit" class="btn btn-primary">{{ __('Create case') }}</button>
                        </div>
                    </form>
                </div>
            @endcan

            <div class="card">
                <div class="card-header">
                    <ul class="nav nav-pills card-header-pills" aria-label="{{ __('Filter by status') }}">
                        <li class="nav-item"><a class="nav-link {{ $status ? '' : 'active' }}" href="{{ route('cases.index') }}">{{ __('All') }}</a></li>
                        @foreach (\App\Models\CaseFile::STATUSES as $s)
                            <li class="nav-item"><a class="nav-link {{ $status === $s ? 'active' : '' }}" href="{{ route('cases.index', ['status' => $s]) }}">{{ __('status.'.$s) }}</a></li>
                        @endforeach
                    </ul>
                </div>
                @if ($cases->isEmpty())
                    <div class="empty">
                        <div class="empty-icon"><x-icon name="folders" /></div>
                        <p class="empty-title">{{ __('No cases yet') }}</p>
                        <p class="empty-subtitle text-secondary">{{ __('Create a case, then upload its documents to run the checks.') }}</p>
                    </div>
                @else
                    <div class="table-responsive">
                        <table class="table table-vcenter card-table table-dense">
                            <thead>
                                <tr>
                                    <th>{{ __('Reference') }}</th>
                                    <th>{{ __('Title') }}</th>
                                    <th>{{ __('Status') }}</th>
                                    <th>{{ __('Created by') }}</th>
                                    <th class="text-end">{{ __('Created') }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                @foreach ($cases as $case)
                                    <tr>
                                        <td><a href="{{ route('cases.show', $case) }}" class="font-mono">{{ $case->reference }}</a></td>
                                        <td>{{ $case->title }}</td>
                                        <td><x-status-badge :status="$case->status" /></td>
                                        <td class="text-secondary">{{ $case->creator?->name ?? "—" }}</td>
                                        <td class="text-end text-secondary">{{ $case->created_at->format('Y-m-d H:i') }}</td>
                                    </tr>
                                @endforeach
                            </tbody>
                        </table>
                    </div>
                    @if ($cases->hasPages())
                        <div class="card-footer">{{ $cases->links() }}</div>
                    @endif
                @endif
            </div>
        </div>
    </div>
</x-layouts.app>
