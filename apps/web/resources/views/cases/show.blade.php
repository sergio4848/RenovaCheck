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
                        <div class="card-header"><h3 class="card-title">{{ __('Upload documents') }}</h3></div>
                        <div class="card-body">
                            @if ($errors->any())
                                <div class="alert alert-danger" role="alert">
                                    @foreach ($errors->all() as $error)<div>{{ $error }}</div>@endforeach
                                </div>
                            @endif
                            @if (session('upload_results'))
                                <ul class="list-unstyled mb-3">
                                    @foreach (session('upload_results') as $message)<li>{{ $message }}</li>@endforeach
                                </ul>
                            @endif
                            @can('cases.create')
                                <form method="POST" action="{{ route('documents.store', $case) }}" enctype="multipart/form-data" class="d-flex gap-2 flex-wrap align-items-start">
                                    @csrf
                                    <input type="file" name="files[]" multiple required accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" class="form-control w-auto flex-grow-1">
                                    <button type="submit" class="btn btn-primary"><x-icon name="plus" /> {{ __('Upload') }}</button>
                                </form>
                                <div class="form-text">{{ __('PDF, PNG or JPEG, up to :size MB per file, :count files at once.', ['size' => intdiv(config('documents.max_file_kb'), 1024), 'count' => config('documents.max_files_per_upload')]) }}</div>
                            @endcan
                        </div>
                    </div>
                </div>
                <div class="col-12">
                    <div class="card">
                        <div class="card-header"><h3 class="card-title">{{ __('Documents') }}</h3></div>
                        @if ($documents->isEmpty())
                            <div class="empty">
                                <div class="empty-icon"><x-icon name="file-text" /></div>
                                <p class="empty-title">{{ __('No documents yet') }}</p>
                                <p class="empty-subtitle text-secondary">{{ __('Upload the application extract, offer or contract, invoices, acceptance protocol and product card.') }}</p>
                            </div>
                        @else
                            <div class="table-responsive">
                                <table class="table table-vcenter card-table table-dense">
                                    <thead>
                                        <tr><th>{{ __('Document') }}</th><th>{{ __('Type') }}</th><th>{{ __('Pages') }}</th><th>{{ __('Status') }}</th><th>{{ __('Virus scan') }}</th></tr>
                                    </thead>
                                    <tbody>
                                        @foreach ($documents as $document)
                                            <tr>
                                                <td>
                                                    <a href="{{ route('documents.download', [$case, $document]) }}">{{ $document->original_name }}</a>
                                                    <div class="small text-secondary">{{ number_format($document->size_bytes / 1024, 0, ',', ' ') }} kB</div>
                                                </td>
                                                <td style="min-width: 15rem">
                                                    @if ($document->doc_type)
                                                        <span class="badge bg-primary-subtle text-primary-emphasis">{{ $document->doc_type->label() }}</span>
                                                        <span class="small text-secondary">
                                                            @if ($document->doc_type_source === 'user')
                                                                {{ __('set manually') }}
                                                            @else
                                                                {{ __('automatic') }} · {{ number_format($document->doc_type_confidence * 100, 0) }}%
                                                            @endif
                                                        </span>
                                                    @elseif ($document->status === 'processed')
                                                        <span class="badge bg-warning-subtle text-warning-emphasis">{{ __('Unrecognised — set the type') }}</span>
                                                    @else
                                                        <span class="text-secondary">—</span>
                                                    @endif
                                                    @can('cases.create')
                                                        @if ($document->status === 'processed')
                                                            <form method="POST" action="{{ route('documents.type', [$case, $document]) }}" class="d-flex gap-1 mt-1">
                                                                @csrf @method('PATCH')
                                                                <select name="doc_type" class="form-select form-select-sm" aria-label="{{ __('Document type') }}">
                                                                    @foreach (\App\Enums\DocType::cases() as $type)
                                                                        <option value="{{ $type->value }}" @selected($document->doc_type === $type)>{{ $type->label() }}</option>
                                                                    @endforeach
                                                                </select>
                                                                <button type="submit" class="btn btn-sm btn-outline-secondary">{{ __('Save') }}</button>
                                                            </form>
                                                        @endif
                                                    @endcan
                                                </td>
                                                <td>
                                                    @forelse ($document->pages as $page)
                                                        <a href="{{ route('documents.page', [$case, $document, $page->page_no]) }}" target="_blank" rel="noopener" class="badge bg-secondary-subtle text-secondary-emphasis text-decoration-none" title="{{ __('text_source.'.$page->text_source) }}">{{ $page->page_no }}</a>
                                                    @empty
                                                        <span class="text-secondary">—</span>
                                                    @endforelse
                                                </td>
                                                <td>
                                                    <x-document-status :status="$document->status" />
                                                    @if ($document->error_code)
                                                        <div class="small text-danger">{{ __('extract_error.'.$document->error_code) }}</div>
                                                    @endif
                                                </td>
                                                <td class="small text-secondary">{{ __('scan_status.'.$document->scan_status) }}</td>
                                            </tr>
                                        @endforeach
                                    </tbody>
                                </table>
                            </div>
                        @endif
                    </div>
                    @if ($documents->contains(fn ($d) => in_array($d->status, ['uploaded', 'processing'], true)))
                        {{-- Refresh while documents are being processed. --}}
                        <script>setTimeout(() => window.location.reload(), 4000);</script>
                    @endif
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
