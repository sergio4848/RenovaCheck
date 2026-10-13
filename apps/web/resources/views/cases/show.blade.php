<x-layouts.app :title="$case->reference">
    <x-page-header :title="$case->title" :pretitle="$case->reference">
        <x-slot:actions>
            <a href="{{ route('cases.index') }}" class="btn btn-outline-secondary"><x-icon name="arrow-left" /> {{ __('Cases') }}</a>
        </x-slot:actions>
    </x-page-header>
    <div class="page-body">
        <div class="container-xl">
            @if (session('status'))
                <div class="alert alert-success" role="status">{{ session('status') }}</div>
            @endif
            <div class="row row-cards">
                <div class="col-lg-4">
                    <div class="card">
                        <div class="card-body">
                            <dl class="row mb-0">
                                <dt class="col-5">{{ __('Status') }}</dt>
                                <dd class="col-7"><x-status-badge :status="$case->status" /></dd>
                                <dt class="col-5">{{ __('Created by') }}</dt>
                                <dd class="col-7">{{ $case->creator?->name ?? "—" }}</dd>
                                <dt class="col-5">{{ __('Created') }}</dt>
                                <dd class="col-7 mb-0">{{ $case->created_at->format('Y-m-d H:i') }}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
                <div class="col-lg-8">
                    <div class="card">
                        <div class="card-header"><h3 class="card-title">{{ __('Documents') }}</h3></div>
                        <div class="empty">
                            <div class="empty-icon"><x-icon name="file-text" /></div>
                            <p class="empty-title">{{ __('No documents yet') }}</p>
                            <p class="empty-subtitle text-secondary">{{ __('Document upload arrives in the next iteration.') }}</p>
                        </div>
                    </div>
                </div>
                <div class="col-12">
                    <div class="card">
                        <div class="card-header"><h3 class="card-title">{{ __('Event log') }}</h3></div>
                        <div class="list-group list-group-flush">
                            @forelse ($events as $event)
                                <div class="list-group-item">
                                    <div class="row align-items-center">
                                        <div class="col-auto text-secondary small">{{ $event->created_at->format('Y-m-d H:i:s') }}</div>
                                        <div class="col">{{ __('event.'.$event->event_type) }} <span class="text-secondary">· {{ $event->actor?->name ?? __('System') }}</span></div>
                                    </div>
                                </div>
                            @empty
                                <div class="list-group-item text-secondary">{{ __('No events.') }}</div>
                            @endforelse
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</x-layouts.app>
