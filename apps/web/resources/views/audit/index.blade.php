<x-layouts.app :title="__('Event log')">
    <x-page-header :title="__('Event log')" :pretitle="$tenant->organization()->name" />
    <div class="page-body">
        <div class="container-xl">
            @if ($brokenAt === null)
                <div class="alert alert-success d-flex align-items-center gap-2" role="status">
                    <x-icon name="shield-check" /> {{ __('Hash chain verified: no event has been altered or removed.') }}
                </div>
            @else
                <div class="alert alert-danger d-flex align-items-center gap-2" role="alert">
                    <x-icon name="alert-triangle" /> {{ __('Hash chain broken at event #:id.', ['id' => $brokenAt]) }}
                </div>
            @endif
            <div class="card">
                <div class="table-responsive">
                    <table class="table table-vcenter card-table table-dense">
                        <thead>
                            <tr><th>#</th><th>{{ __('Time') }}</th><th>{{ __('Event') }}</th><th>{{ __('User') }}</th><th>{{ __('Subject') }}</th><th>{{ __('Hash') }}</th></tr>
                        </thead>
                        <tbody>
                            @forelse ($events as $event)
                                <tr>
                                    <td class="text-secondary">{{ $event->id }}</td>
                                    <td class="text-secondary text-nowrap">{{ $event->created_at->format('Y-m-d H:i:s') }}</td>
                                    <td>{{ __('event.'.$event->event_type) }}</td>
                                    <td>{{ $event->actor?->name ?? __('System') }}</td>
                                    <td class="text-secondary">{{ $event->subject_type ? __('subject.'.$event->subject_type) : '—' }}</td>
                                    <td><span class="font-mono hash" title="{{ $event->hash }}">{{ $event->hash }}</span></td>
                                </tr>
                            @empty
                                <tr><td colspan="6" class="text-center text-secondary py-4">{{ __('No events.') }}</td></tr>
                            @endforelse
                        </tbody>
                    </table>
                </div>
                @if ($events->hasPages())
                    <div class="card-footer">{{ $events->links() }}</div>
                @endif
            </div>
        </div>
    </div>
</x-layouts.app>
