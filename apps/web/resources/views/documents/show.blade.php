<x-layouts.app :title="$document->original_name">
    <x-page-header :title="$document->original_name" :pretitle="$case->reference">
        <x-slot:actions>
            <a href="{{ route('cases.show', $case) }}" class="btn btn-outline-secondary"><x-icon name="arrow-left" /> {{ __('Case') }}</a>
            <a href="{{ route('documents.download', [$case, $document]) }}" class="btn btn-outline-secondary">{{ __('Download original') }}</a>
        </x-slot:actions>
    </x-page-header>
    <div class="page-body">
        <div class="container-xl" x-data="{ active: null }">
            <div class="row row-cards">
                <div class="col-lg-5 order-lg-2">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">{{ __('Fields read from the document') }}</h3>
                            <div class="card-actions small text-secondary">
                                {{ $document->doc_type?->label() ?? __('Unrecognised — set the type') }}
                            </div>
                        </div>
                        @if ($fields->isEmpty())
                            <div class="card-body text-secondary">
                                {{ $document->status === 'processed' ? __('No fields were found in this document.') : __('The document is being processed.') }}
                            </div>
                        @else
                            <div class="table-responsive">
                                <table class="table table-vcenter card-table table-dense">
                                    <thead>
                                        <tr><th>{{ __('Field') }}</th><th>{{ __('As printed') }}</th><th class="text-end">{{ __('Confidence') }}</th></tr>
                                    </thead>
                                    <tbody>
                                        @foreach ($fields as $field)
                                            <tr class="field-row" id="field-{{ $field->name }}"
                                                :class="active === '{{ $field->name }}' && 'is-active'"
                                                @mouseenter="active = '{{ $field->name }}'" @focusin="active = '{{ $field->name }}'">
                                                <td>
                                                    <a href="#box-{{ $field->name }}" class="text-reset">{{ $field->label() }}</a>
                                                    <div class="small text-secondary">{{ __('field_method.'.$field->method) }} · {{ __('page :n', ['n' => $field->page_no]) }}</div>
                                                </td>
                                                <td>
                                                    @if ($field->status === 'unreadable')
                                                        <span class="badge bg-warning-subtle text-warning-emphasis">{{ __('unreadable') }}</span>
                                                        <div class="small text-secondary text-truncate field-raw">{{ $field->raw_text }}</div>
                                                    @elseif (in_array($field->value, ['true', 'false'], true) && str_starts_with($field->name, 'signature_'))
                                                        {{ $field->value === 'true' ? __('signed') : __('not signed') }}
                                                    @else
                                                        <span class="field-raw">{{ $field->raw_text }}</span>
                                                        @if ($field->showsNormalized())
                                                            <div class="small text-secondary font-mono">{{ $field->value }}</div>
                                                        @endif
                                                    @endif
                                                </td>
                                                <td class="text-end small {{ $field->confidence < 0.8 ? 'text-warning' : 'text-secondary' }}">{{ number_format($field->confidence * 100, 0) }}%</td>
                                            </tr>
                                        @endforeach
                                    </tbody>
                                </table>
                            </div>
                        @endif
                    </div>
                </div>
                <div class="col-lg-7 order-lg-1">
                    @forelse ($document->pages as $page)
                        <div class="card mb-3">
                            <div class="card-header"><h3 class="card-title">{{ __('Page :n', ['n' => $page->page_no]) }}</h3>
                                <div class="card-actions small text-secondary">{{ __('text_source.'.$page->text_source) }}</div>
                            </div>
                            <div class="page-view">
                                <img src="{{ route('documents.page', [$case, $document, $page->page_no]) }}" alt="{{ __('Page :n', ['n' => $page->page_no]) }}" width="{{ $page->image_width_px }}" height="{{ $page->image_height_px }}" loading="lazy">
                                @foreach ($fields->where('page_no', $page->page_no) as $field)
                                    <a href="#field-{{ $field->name }}" id="box-{{ $field->name }}" class="field-box {{ $field->status === 'unreadable' ? 'is-unreadable' : '' }}"
                                       style="{{ $field->boxStyle() }}" title="{{ $field->label() }}"
                                       :class="active === '{{ $field->name }}' && 'is-active'"
                                       @mouseenter="active = '{{ $field->name }}'"><span class="visually-hidden">{{ $field->label() }}</span></a>
                                @endforeach
                            </div>
                        </div>
                    @empty
                        <div class="card"><div class="card-body text-secondary">{{ __('The document is being processed.') }}</div></div>
                    @endforelse
                </div>
            </div>
        </div>
    </div>
</x-layouts.app>
