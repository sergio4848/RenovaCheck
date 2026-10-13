<x-layouts.app :title="__('Members')">
    <x-page-header :title="__('Members')" :pretitle="$tenant->organization()->name" />
    <div class="page-body">
        <div class="container-xl">
            <div class="card">
                <div class="table-responsive">
                    <table class="table table-vcenter card-table table-dense">
                        <thead>
                            <tr><th>{{ __('Name') }}</th><th>{{ __('Email') }}</th><th>{{ __('Role') }}</th><th class="text-end">{{ __('Member since') }}</th></tr>
                        </thead>
                        <tbody>
                            @foreach ($members as $member)
                                <tr>
                                    <td>{{ $member->user->name }}</td>
                                    <td class="text-secondary">{{ $member->user->email }}</td>
                                    <td><span class="badge {{ $member->role === \App\Enums\Role::Owner ? 'bg-primary-subtle text-primary-emphasis' : 'bg-secondary-subtle text-secondary-emphasis' }}">{{ $member->role->label() }}</span></td>
                                    <td class="text-end text-secondary">{{ $member->created_at->format('Y-m-d') }}</td>
                                </tr>
                            @endforeach
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</x-layouts.app>
