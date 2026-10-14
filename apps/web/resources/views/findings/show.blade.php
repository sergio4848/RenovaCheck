<x-layouts.app :title="$finding->title_pl">
    <x-page-header :title="$finding->title_pl" :pretitle="$case->reference.' · '.__('Finding :n of :total', ['n' => $position ?? '–', 'total' => $total])">
        <x-slot:actions>
            <a href="{{ route('cases.show', $case) }}#finding-{{ $finding->id }}" class="btn btn-outline-secondary"><x-icon name="arrow-left" /> {{ __('Case') }}</a>
            @if ($previous)
                <a href="{{ route('findings.show', [$case, $previous]) }}" class="btn btn-outline-secondary" rel="prev">{{ __('Previous') }}</a>
            @endif
            @if ($next)
                <a href="{{ route('findings.show', [$case, $next]) }}" class="btn btn-outline-secondary" rel="next">{{ __('Next') }}</a>
            @endif
        </x-slot:actions>
    </x-page-header>
    <div class="page-body">
        <div class="container-xl">
            @if (session('status'))
                <div class="alert alert-success" role="status">{{ session('status') }}</div>
            @endif
            <div class="row row-cards">
                {{-- Source pages with the boxes the values were read from --}}
                <div class="col-lg-7">
                    <div class="card">
                        <div class="card-header">
                            <ul class="nav nav-tabs card-header-tabs" role="tablist">
                                @foreach ($documents as $i => $document)
                                    <li class="nav-item" role="presentation">
                                        <a href="#doc-{{ $document->id }}" class="nav-link {{ $i === 0 ? 'active' : '' }}" data-bs-toggle="tab" role="tab"
                                           aria-selected="{{ $i === 0 ? 'true' : 'false' }}">
                                            {{ $document->doc_type?->label() ?? $document->original_name }}
                                            @if (in_array($document->id, $finding->subject_doc_ids, true))
                                                <span class="badge bg-primary-subtle text-primary-emphasis ms-1">{{ __('checked') }}</span>
                                            @endif
                                        </a>
                                    </li>
                                @endforeach
                            </ul>
                        </div>
                        <div class="tab-content">
                            @forelse ($documents as $i => $document)
                                @php($rows = collect($evidence)->filter(fn ($e) => $e['document']?->id === $document->id && $e['source']))
                                @php($pageNumbers = $rows->map(fn ($e) => $e['source']->page_no)->unique()->sort()->values())
                                <div class="tab-pane {{ $i === 0 ? 'active show' : '' }}" id="doc-{{ $document->id }}" role="tabpanel">
                                    <div class="card-body py-2 small text-secondary d-flex justify-content-between">
                                        <a href="{{ route('documents.show', [$case, $document]) }}">{{ $document->original_name }}</a>
                                        <span>{{ $pageNumbers->isEmpty() ? __('no boxes for this finding') : __('page :n', ['n' => $pageNumbers->implode(', ')]) }}</span>
                                    </div>
                                    @foreach ($document->pages->whereIn('page_no', $pageNumbers->isEmpty() ? [1] : $pageNumbers->all()) as $page)
                                        <div class="page-view">
                                            <img src="{{ route('documents.page', [$case, $document, $page->page_no]) }}" alt="{{ __('Page :n', ['n' => $page->page_no]) }}"
                                                 width="{{ $page->image_width_px }}" height="{{ $page->image_height_px }}" loading="lazy">
                                            @foreach ($rows->filter(fn ($e) => $e['source']->page_no === $page->page_no) as $row)
                                                <a href="#evidence-{{ $row['key'] }}" class="field-box {{ $row['subject'] ? '' : 'is-context' }}"
                                                   data-box="{{ $row['source']->boxData() }}" data-field-key="{{ $row['key'] }}"
                                                   title="{{ $row['source']->label() }}"><span class="visually-hidden">{{ $row['source']->label() }}</span></a>
                                            @endforeach
                                        </div>
                                    @endforeach
                                </div>
                            @empty
                                <div class="card-body text-secondary">{{ __('This finding is about the case as a whole, not about a value in a document.') }}</div>
                            @endforelse
                        </div>
                    </div>
                </div>

                {{-- Finding, evidence and decision --}}
                <div class="col-lg-5">
                    <div class="card mb-3">
                        <div class="card-body">
                            <div class="d-flex flex-wrap gap-2 align-items-center mb-2">
                                <x-finding-severity :severity="$finding->severity" />
                                <span class="badge bg-secondary-subtle text-secondary-emphasis">{{ __('review_status.'.$finding->review_status) }}</span>
                                <span class="small text-secondary font-mono ms-auto">{{ $finding->rule_id }} v{{ $finding->rule_version }}</span>
                            </div>
                            <p class="mb-2">{{ $finding->reason_pl }}</p>
                            <div class="small text-secondary">
                                {{ __('family.'.$finding->family) }} · {{ __('outcome.'.$finding->outcome) }}
                                @if ($finding->rule_source_url)
                                    · <a href="{{ $finding->rule_source_url }}" target="_blank" rel="noopener noreferrer">{{ __('Rule source') }}</a>
                                @endif
                            </div>
                            @php($confidences = collect($evidence)->pluck('source')->filter()->pluck('confidence'))
                            @if ($confidences->isNotEmpty())
                                <div class="small mt-1 {{ $confidences->min() < 0.8 ? 'text-warning' : 'text-secondary' }}">
                                    {{ __('Lowest reading confidence: :p%', ['p' => number_format($confidences->min() * 100, 0)]) }}
                                </div>
                            @endif
                        </div>
                        @if ($evidence)
                            <div class="table-responsive">
                                <table class="table table-vcenter card-table table-dense">
                                    <thead><tr><th>{{ __('Document') }}</th><th>{{ __('Field') }}</th><th>{{ __('As printed') }}</th><th class="text-end">{{ __('Confidence') }}</th></tr></thead>
                                    <tbody>
                                        @foreach ($evidence as $row)
                                            <tr class="evidence-row" id="evidence-{{ $row['key'] }}" data-field-key="{{ $row['key'] }}" tabindex="0">
                                                <td>
                                                    {{ $row['document']?->doc_type?->label() ?? '—' }}
                                                    @if ($row['subject'])<span class="badge bg-primary-subtle text-primary-emphasis ms-1">{{ __('checked') }}</span>@endif
                                                </td>
                                                <td>{{ __('field.'.$row['field']) }}</td>
                                                <td>{{ $row['text'] ?: $row['value'] }}</td>
                                                <td class="text-end small text-secondary">{{ $row['source'] ? number_format($row['source']->confidence * 100, 0).'%' : '—' }}</td>
                                            </tr>
                                        @endforeach
                                    </tbody>
                                </table>
                            </div>
                        @endif
                    </div>

                    <div class="card mb-3">
                        <div class="card-header"><h3 class="card-title">{{ __('Decision') }}</h3></div>
                        <div class="card-body">
                            @if ($errors->any())
                                <div class="alert alert-danger" role="alert">@foreach ($errors->all() as $error)<div>{{ $error }}</div>@endforeach</div>
                            @endif
                            @if ($finding->review_status === 'do_ponownej_weryfikacji')
                                <div class="alert alert-warning" role="status">{{ __('The values changed after the last decision. Check them again.') }}</div>
                            @endif
                            @can('findings.decide')
                                @if ($case->status === 'closed')
                                    <p class="text-secondary mb-0">{{ __('The case is closed. Reopen it to change decisions.') }}</p>
                                @elseif (! $finding->is_current)
                                    <p class="text-secondary mb-0">{{ __('This finding is no longer reported; check the case again.') }}</p>
                                @else
                                    <form method="POST" action="{{ route('findings.decide', [$case, $finding]) }}">
                                        @csrf
                                        <fieldset class="mb-3">
                                            <legend class="form-label">{{ __('Reviewer decision') }}</legend>
                                            <div class="d-grid gap-2">
                                                @foreach (\App\Models\FindingDecision::DECISIONS as $value)
                                                    <label class="decision-option">
                                                        <input type="radio" name="decision" value="{{ $value }}" class="form-check-input me-2" required @checked(old('decision', $finding->decision) === $value)>
                                                        <strong>{{ __('decision.'.$value) }}</strong>
                                                        <span class="d-block small text-secondary">{{ __('decision_help.'.$value) }}</span>
                                                    </label>
                                                @endforeach
                                            </div>
                                        </fieldset>
                                        <div class="mb-3">
                                            <label class="form-label {{ $finding->severity === 'critical' ? 'required' : '' }}" for="comment">{{ __('Comment') }}</label>
                                            <textarea id="comment" name="comment" rows="3" maxlength="2000" class="form-control @error('comment') is-invalid @enderror" @required($finding->severity === 'critical')>{{ old('comment') }}</textarea>
                                            <div class="form-hint">{{ $finding->severity === 'critical' ? __('Required for critical findings: what you checked and why.') : __('Optional.') }}</div>
                                        </div>
                                        <button type="submit" class="btn btn-primary">{{ __('Save decision') }}</button>
                                    </form>
                                @endif
                            @else
                                <p class="text-secondary mb-0">{{ __('You can view this finding but not decide on it.') }}</p>
                            @endcan
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-header"><h3 class="card-title">{{ __('Decision history') }}</h3></div>
                        <div class="list-group list-group-flush">
                            @forelse ($decisions as $decision)
                                <div class="list-group-item">
                                    <div class="d-flex justify-content-between small text-secondary">
                                        <span>{{ $decision->decider?->name ?? '—' }}</span>
                                        <span>{{ $decision->created_at->format('Y-m-d H:i') }}</span>
                                    </div>
                                    <div><strong>{{ __('decision.'.$decision->decision) }}</strong>
                                        @if ($decision->evidence_hash !== $finding->evidence_hash)
                                            <span class="badge bg-warning-subtle text-warning-emphasis ms-1">{{ __('made on earlier values') }}</span>
                                        @endif
                                    </div>
                                    @if ($decision->comment)<div class="small">{{ $decision->comment }}</div>@endif
                                </div>
                            @empty
                                <div class="list-group-item text-secondary">{{ __('No decision yet.') }}</div>
                            @endforelse
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</x-layouts.app>
