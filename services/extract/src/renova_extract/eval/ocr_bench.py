"""OCR benchmark: the same synthetic pages through every OCR adapter (Tesseract, Azure, Google).

Pages are whole documents from a synthetic set (tools/synth), taken in sorted order until the page
budget is filled exactly. Every page is rendered the way the analysis renders it and given to each
provider as an image, also pages that have a text layer, so all providers read the same pixels.

Measured per provider:

* field hit rate: share of ground-truth field texts found in the page's OCR text (whitespace and
  case normalised), per quality;
* CER/WER: against the PDF text layer of clean pages, both sides in line order;
* field F1: the deterministic field extractor run on the provider's words, scored as in
  ``eval.extraction``;
* time per page and an estimated cost (list prices, see ``PRICES``).

A provider without credentials is not run and reported as "uruchomienie pominięte".
"""

from __future__ import annotations

import json
import resource
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from renova_extract.core.config import Settings
from renova_extract.documents.loader import RENDER_DPI, load_document
from renova_extract.documents.models import Page, TextSource, Word
from renova_extract.eval import extraction
from renova_extract.eval.report import SKIPPED
from renova_extract.eval.timing import summarize
from renova_extract.fields.dictionary import FieldDictionary
from renova_extract.fields.extractors import FieldExtractor
from renova_extract.fields.layout import build_lines
from renova_extract.ocr.azure import AzureDocumentIntelligence
from renova_extract.ocr.base import OcrAdapter, OcrUnavailableError
from renova_extract.ocr.google import GoogleDocumentAI
from renova_extract.ocr.tesseract import TesseractPol

PROVIDERS = ("tesseract", "azure", "google")
VCPU_HOUR_USD = 0.05
PRICES: dict[str, dict[str, Any]] = {
    "azure": {
        "per_1000_pages_usd": 1.50,
        "note": "Azure AI Document Intelligence, prebuilt-read, pay-as-you-go S0: USD 1.50 per 1000 pages "
        "(first 1M pages/month; list price, stan na 2026-10, do weryfikacji: "
        "https://azure.microsoft.com/pricing/details/ai-document-intelligence/).",
    },
    "google": {
        "per_1000_pages_usd": 1.50,
        "note": "Google Document AI, Enterprise Document OCR: USD 1.50 per 1000 pages "
        "(1-5M pages/month; list price, stan na 2026-10, do weryfikacji: "
        "https://cloud.google.com/document-ai/pricing).",
    },
    "tesseract": {
        "per_1000_pages_usd": 0.0,
        "note": f"No licence fee (Apache-2.0); cost = measured CPU time x assumed USD {VCPU_HOUR_USD:.2f} "
        "per vCPU-hour of a general-purpose cloud VM (assumption, docs/ASSUMPTIONS.md).",
    },
}


@dataclass
class BenchPage:
    doc_id: str
    page_no: int
    quality: str
    page: Page
    reference: str  # text layer in line order; empty for scans
    field_texts: list[str]


@dataclass
class BenchDocument:
    truth: dict[str, Any]
    pages: list[BenchPage]


@dataclass
class ProviderRun:
    name: str
    status: str = "ok"
    pages: int = 0
    errors: int = 0
    durations: list[float] = field(default_factory=list)
    cpu_seconds: float = 0.0
    hits: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    char_edits: int = 0
    char_total: int = 0
    word_edits: int = 0
    word_total: int = 0
    fields: extraction.ExtractionReport = field(default_factory=lambda: extraction.ExtractionReport(ocr=""))


def normalise(text: str) -> str:
    return " ".join(text.casefold().split())


def line_text(words: list[Word]) -> str:
    """Words joined in reading order (lines top to bottom, words left to right)."""
    return "\n".join(" ".join(w.text for w in sorted(line.words, key=lambda w: w.x0)) for line in build_lines(words))


def edit_distance(a: list[str] | str, b: list[str] | str) -> int:
    """Levenshtein distance over characters (str) or tokens (list)."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def select_documents(dataset: Path, page_budget: int, max_pages: int = 50) -> list[BenchDocument]:
    """Whole documents in sorted order; a document that would overflow the budget is skipped."""
    selected: list[BenchDocument] = []
    total = 0
    for truth_file in sorted(dataset.glob("SYN-*/ground_truth.json")):
        truth = json.loads(truth_file.read_text())
        for doc in truth["documents"]:
            if total + doc["pages"] > page_budget:
                continue
            loaded = load_document((truth_file.parent / doc["file"]).read_bytes(), max_pages, ocr=None)
            pages = []
            for page in loaded.pages:
                reference = line_text(page.words) if page.source is TextSource.TEXT_LAYER else ""
                texts = [f["text"] for f in doc["fields"] if f["page"] == page.number and f.get("text")]
                pages.append(BenchPage(doc["doc_id"], page.number, doc["quality"], page, reference, texts))
            selected.append(BenchDocument(doc, pages))
            total += len(pages)
            if total == page_budget:
                return selected
    return selected


def providers_from(settings: Settings) -> dict[str, OcrAdapter | None]:
    """Adapters that can run with the configured credentials; None means skipped."""
    tesseract = TesseractPol()
    azure_key = settings.azure_di_key.get_secret_value() if settings.azure_di_key else ""
    google_token = settings.google_access_token.get_secret_value() if settings.google_access_token else ""
    return {
        "tesseract": tesseract if tesseract.available() else None,
        "azure": AzureDocumentIntelligence(settings.azure_di_endpoint, azure_key) if azure_key else None,
        "google": GoogleDocumentAI(
            settings.google_project_id or "", settings.google_location, settings.google_processor_id or "", google_token
        )
        if google_token and settings.google_project_id and settings.google_processor_id
        else None,
    }


def _children_cpu() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def run_provider(
    name: str,
    adapter: OcrAdapter,
    documents: list[BenchDocument],
    dictionary: FieldDictionary,
    clock: Callable[[], float] = time.perf_counter,
) -> ProviderRun:
    run = ProviderRun(name)
    extractor = FieldExtractor(dictionary)
    for document in documents:
        ocr_pages: list[Page] = []
        for bench_page in document.pages:
            source = bench_page.page
            cpu_before, started = _children_cpu() + time.process_time(), clock()
            try:
                words = adapter.recognize(source.image)
            except OcrUnavailableError:
                run.errors += 1
                words = []
            run.durations.append(clock() - started)
            run.cpu_seconds += _children_cpu() + time.process_time() - cpu_before
            run.pages += 1
            ocr_pages.append(
                Page(source.number, source.width_pt, source.height_pt, source.image, words, TextSource.OCR)
            )
            _score_text(run, bench_page, words)
        predicted = {f.name: f for f in extractor.extract(ocr_pages, document.truth["doc_type"])}
        run.fields.documents[document.truth["quality"]] += 1
        extraction._score(run.fields, dictionary, document.truth, predicted)
    if run.errors == run.pages and run.pages:
        run.status = "błąd: brak odpowiedzi"
    return run


def _score_text(run: ProviderRun, bench_page: BenchPage, words: list[Word]) -> None:
    text = normalise(" ".join(w.text for w in words))
    counts = run.hits[bench_page.quality]
    for expected in bench_page.field_texts:
        counts[0] += normalise(expected) in text
        counts[1] += 1
    if bench_page.reference:
        reference = normalise(bench_page.reference)
        hypothesis = normalise(line_text(words))
        run.char_edits += edit_distance(reference, hypothesis)
        run.char_total += len(reference)
        run.word_edits += edit_distance(reference.split(), hypothesis.split())
        run.word_total += len(reference.split())


def _cost(name: str, run: ProviderRun | None, pages: int) -> dict[str, Any]:
    price = PRICES[name]
    if name == "tesseract":
        total = (run.cpu_seconds if run else 0.0) / 3600 * VCPU_HOUR_USD
        per_page = total / pages if pages else 0.0
    else:
        per_page = price["per_1000_pages_usd"] / 1000
        total = per_page * pages
    return {"per_page_usd": round(per_page, 6), "total_usd": round(total, 4)}


def as_dict(run: ProviderRun, pages: int) -> dict[str, Any]:
    clean = run.fields.total("clean")
    scan = run.fields.total("scan")

    def f1(counts: extraction.Counts) -> float | None:
        p, r = counts.precision, counts.recall
        return round(2 * p * r / (p + r), 4) if p is not None and r is not None and p + r else None

    return {
        "status": run.status,
        "pages": run.pages,
        "errors": run.errors,
        "hit_rate": {q: round(h / n, 4) if n else None for q, (h, n) in sorted(run.hits.items())},
        "cer": round(run.char_edits / run.char_total, 4) if run.char_total else None,
        "wer": round(run.word_edits / run.word_total, 4) if run.word_total else None,
        "field_f1": {"clean": f1(clean), "scan": f1(scan)},
        "fields": {"clean": clean.as_dict(), "scan": scan.as_dict()},
        "latency": summarize(run.durations),
        "cpu_seconds": round(run.cpu_seconds, 1),
        "cost": _cost(run.name, run, pages),
        "cost_note": PRICES[run.name]["note"],
    }


def skipped(name: str, pages: int) -> dict[str, Any]:
    return {"status": SKIPPED, "cost": _cost(name, None, pages), "cost_note": PRICES[name]["note"]}


def benchmark(
    dataset: Path,
    page_budget: int,
    adapters: dict[str, OcrAdapter | None],
    dictionary: FieldDictionary,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    documents = select_documents(dataset, page_budget)
    pages = sum(len(d.pages) for d in documents)
    by_quality: dict[str, int] = defaultdict(int)
    for document in documents:
        by_quality[document.truth["quality"]] += len(document.pages)
    seeds = sorted({json.loads(p.read_text())["seed"] for p in dataset.glob("SYN-*/ground_truth.json")})
    result: dict[str, Any] = {
        "dataset": str(dataset),
        "seed": ", ".join(map(str, seeds)),
        "pages": pages,
        "pages_by_quality": dict(by_quality),
        "documents": len(documents),
        "dpi": RENDER_DPI,
        "providers": {},
    }
    for name in PROVIDERS:
        adapter = adapters.get(name)
        if adapter is None:
            result["providers"][name] = skipped(name, pages)
            continue
        if progress:
            progress(f"{name}: {pages} pages")
        result["providers"][name] = as_dict(run_provider(name, adapter, documents, dictionary), pages)
    return result
