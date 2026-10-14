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
            @error('case')
                <div class="alert alert-danger" role="alert">{{ $message }}</div>
            @enderror
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
                            @can('findings.decide')
                                <div class="mt-3">
                                    @if ($case->status === 'closed')
                                        <form method="POST" action="{{ route('cases.reopen', $case) }}">@csrf
                                            <button type="submit" class="btn btn-outline-secondary w-100">{{ __('Reopen case') }}</button>
                                        </form>
                                    @else
                                        <form method="POST" action="{{ route('cases.close', $case) }}">@csrf
                                            <button type="submit" class="btn btn-outline-primary w-100">{{ __('Close case') }}</button>
                                        </form>
                                        <div class="form-hint">{{ __('Possible when every critical finding has a decision.') }}</div>
                                    @endif
                                </div>
                            @endcan
                        </div>
                    </div>
                </div>
                <div class="col-lg-8">
                    <div class="card">
                        <div class="card-header"><h3 class="card-title">{{ __('Upload documents') }}</h3></div>
                        <div class="card-body">
                            @php($uploadErrors = collect($errors->getMessages())->filter(fn ($messages, $key) => str_starts_with($key, 'files'))->flatten())
                            @if ($uploadErrors->isNotEmpty())
                                <div class="alert alert-danger" role="alert">
                                    @foreach ($uploadErrors as $error)<div>{{ $error }}</div>@endforeach
                                </div>
                            @endif
                            @if (session('upload_results'))
                                <ul class="list-unstyled mb-3">
                                    @foreach (session('upload_results') as $message)<li>{{ $message }}</li>@endforeach
                                </ul>
                            @endif
                            @if ($case->status !== 'closed' && auth()->user()->can('cases.create'))
                                <form method="POST" action="{{ route('documents.store', $case) }}" enctype="multipart/form-data" class="d-flex gap-2 flex-wrap align-items-start">
                                    @csrf
                                    <input type="file" name="files[]" multiple required accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" class="form-control w-auto flex-grow-1">
                                    <button type="submit" class="btn btn-primary"><x-icon name="plus" /> {{ __('Upload') }}</button>
                                </form>
                                <div class="form-text">{{ __('PDF, PNG or JPEG, up to :size MB per file, :count files at once.', ['size' => intdiv(config('documents.max_file_kb'), 1024), 'count' => config('documents.max_files_per_upload')]) }}</div>
                            @endif
                        </div>
                    </div>
                </div>
                <div class="col-12">
                    @php($byId = $documents->keyBy('id'))
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">{{ __('Findings') }}</h3>
                            <div class="card-actions d-flex align-items-center gap-3">
                                @if ($evaluation)
                                    <span class="small text-secondary">
                                        {{ __('Checked :when · rules valid on :date (:count)', ['when' => $evaluation->created_at->format('Y-m-d H:i'), 'date' => $evaluation->reference_date->format('d.m.Y'), 'count' => count($evaluation->ruleset)]) }}
                                    </span>
                                @endif
                                @if ($case->status !== 'closed' && auth()->user()->can('cases.create'))
                                    <form method="POST" action="{{ route('cases.evaluate', $case) }}">
                                        @csrf
                                        <button type="submit" class="btn btn-sm btn-outline-secondary">{{ __('Check again') }}</button>
                                    </form>
                                @endif
                            </div>
                        </div>
                        @if ($findings->isEmpty())
                            <div class="card-body text-secondary">
                                {{ $evaluation ? __('No findings: the documents are consistent under the current rules.') : __('The case has not been checked yet. It is checked automatically once all documents are processed.') }}
                            </div>
                        @else
                            <div class="list-group list-group-flush">
                                @foreach ($findings as $finding)
                                    <div class="list-group-item" id="finding-{{ $finding->id }}">
                                        <div class="d-flex flex-wrap gap-2 align-items-center mb-1">
                                            <x-finding-severity :severity="$finding->severity" />
                                            <a href="{{ route('findings.show', [$case, $finding]) }}" class="fw-bold">{{ $finding->title_pl }}</a>
                                            <span class="small text-secondary font-mono">{{ $finding->rule_id }} v{{ $finding->rule_version }}</span>
                                            <span class="ms-auto d-flex gap-1">
                                                @if ($finding->decision)
                                                    <span class="badge bg-success-subtle text-success-emphasis">{{ __('decision.'.$finding->decision) }}</span>
                                                @endif
                                                <span class="badge {{ $finding->review_status === 'rozstrzygniete' ? 'bg-secondary-subtle text-secondary-emphasis' : 'bg-warning-subtle text-warning-emphasis' }}">{{ __('review_status.'.$finding->review_status) }}</span>
                                            </span>
                                        </div>
                                        <div>{{ $finding->reason_pl }}</div>
                                        @if ($finding->subject_doc_ids)
                                            <div class="small mt-1">
                                                @foreach ($finding->subject_doc_ids as $docId)
                                                    @if ($doc = $byId->get($docId))
                                                        <a href="{{ route('documents.show', [$case, $doc]) }}{{ $finding->fields && $doc->fields->contains('name', $finding->fields[0]) ? '#field-'.$finding->fields[0] : '' }}" class="me-2">{{ $doc->original_name }}</a>
                                                    @endif
                                                @endforeach
                                            </div>
                                        @endif
                                    </div>
                                @endforeach
                            </div>
                        @endif
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
                                                    <a href="{{ route('documents.show', [$case, $document]) }}">{{ $document->original_name }}</a>
                                                    <div class="small text-secondary">
                                                        {{ number_format($document->size_bytes / 1024, 0, ',', ' ') }} kB
                                                        @if ($document->fields_count)
                                                            · {{ __(':count fields', ['count' => $document->fields_count]) }}
                                                        @endif
                                                    </div>
                                                </td>
                                                <td class="col-doc-type">
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
                                                    @if ($case->status !== 'closed' && auth()->user()->can('cases.create'))
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
                                                    @endif
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
                        <div data-refresh="4000" hidden></div>
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
                                        <div class="col">
                                            {{ __('event.'.$event->event_type) }}
                                            @if ($event->event_type === 'finding.decided')
                                                <span class="badge bg-secondary-subtle text-secondary-emphasis">{{ __('decision.'.($event->payload['decision'] ?? '')) }}</span>
                                            @elseif ($event->event_type === 'case.status_changed')
                                                <span class="text-secondary">({{ __('status.'.($event->payload['from'] ?? '')) }} → {{ __('status.'.($event->payload['to'] ?? '')) }})</span>
                                            @endif
                                            <span class="text-secondary">· {{ $event->actor?->name ?? __('System') }}</span>
                                        </div>
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
