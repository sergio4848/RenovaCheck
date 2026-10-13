"""Field extraction precision/recall against the synthetic ground truth (tools/synth output).

Scoring is per (document, field). The ground truth may print a field more than once (the
acceptance protocol repeats the address); a prediction is correct when its normalized value
equals the normalized value of any of those occurrences.

* TP: predicted ``ok`` and correct.
* FP: predicted ``ok`` and wrong, or predicted for a field the document does not contain.
* FN: in the ground truth but not predicted correctly (missing, wrong or unreadable).
* ``unreadable`` predictions are abstentions: they count as FN, never as FP.

Provenance is checked separately: the page matches and the box overlaps a ground-truth box
(IoU >= 0.5) for correct values.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from renova_extract.documents.loader import load_document
from renova_extract.fields.dictionary import FieldDictionary
from renova_extract.fields.extractors import ExtractedField, FieldExtractor
from renova_extract.fields.layout import Box
from renova_extract.fields.normalize import normalize
from renova_extract.ocr.base import OcrAdapter

IOU_HIT = 0.5


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    unreadable: int = 0
    bbox_hits: int = 0

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "unreadable": self.unreadable,
            "precision": _round(self.precision),
            "recall": _round(self.recall),
            "bbox_hit_rate": _round(self.bbox_hits / self.tp) if self.tp else None,
        }


@dataclass
class ExtractionReport:
    ocr: str
    counts: dict[str, dict[str, Counts]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(Counts)))
    errors: list[dict[str, Any]] = field(default_factory=list)
    documents: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    seconds: float = 0.0

    def total(self, quality: str) -> Counts:
        total = Counts()
        for per_quality in self.counts.values():
            c = per_quality.get(quality)
            if c is None:
                continue
            total.tp += c.tp
            total.fp += c.fp
            total.fn += c.fn
            total.unreadable += c.unreadable
            total.bbox_hits += c.bbox_hits
        return total

    def as_dict(self) -> dict[str, Any]:
        qualities = ("clean", "scan")
        return {
            "ocr": self.ocr,
            "documents": dict(self.documents),
            "overall": {q: self.total(q).as_dict() for q in qualities},
            "fields": {
                name: {q: per_quality[q].as_dict() for q in qualities if q in per_quality}
                for name, per_quality in sorted(self.counts.items())
            },
            "seconds": round(self.seconds, 1),
            "errors": self.errors,
        }


def evaluate(
    dataset: Path, dictionary: FieldDictionary, ocr: OcrAdapter | None, max_pages: int = 50
) -> ExtractionReport:
    extractor = FieldExtractor(dictionary)
    report = ExtractionReport(ocr=ocr.name if ocr else "none")
    started = time.perf_counter()
    for truth_file in sorted(dataset.glob("SYN-*/ground_truth.json")):
        truth = json.loads(truth_file.read_text())
        for doc in truth["documents"]:
            loaded = load_document((truth_file.parent / doc["file"]).read_bytes(), max_pages, ocr)
            predicted = {f.name: f for f in extractor.extract(loaded.pages, doc["doc_type"])}
            report.documents[doc["quality"]] += 1
            _score(report, dictionary, doc, predicted)
    report.seconds = time.perf_counter() - started
    return report


def _score(
    report: ExtractionReport, dictionary: FieldDictionary, doc: dict[str, Any], predicted: dict[str, ExtractedField]
) -> None:
    quality = doc["quality"]
    expected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in doc["fields"]:
        expected[item["name"]].append(item)

    for name, occurrences in expected.items():
        counts = report.counts[name][quality]
        field_type = dictionary.get(name).type
        values = {normalize(field_type, o["value"]) for o in occurrences}
        got = predicted.get(name)
        if got is None or got.status == "unreadable":
            counts.fn += 1
            counts.unreadable += got is not None
            _error(report, doc, name, "unreadable" if got else "missing", occurrences[0]["text"], got)
            continue
        if got.value in values:
            counts.tp += 1
            if any(o["page"] == got.page and iou(got.bbox, Box(**o["bbox"])) >= IOU_HIT for o in occurrences):
                counts.bbox_hits += 1
            continue
        counts.fp += 1
        counts.fn += 1
        _error(report, doc, name, "wrong", occurrences[0]["text"], got)

    for name, got in predicted.items():
        if name not in expected and got.status == "ok":
            report.counts[name][quality].fp += 1
            _error(report, doc, name, "not_in_document", None, got)


def _error(
    report: ExtractionReport,
    doc: dict[str, Any],
    name: str,
    kind: str,
    expected: str | None,
    got: ExtractedField | None,
) -> None:
    report.errors.append(
        {
            "doc_id": doc["doc_id"],
            "quality": doc["quality"],
            "field": name,
            "kind": kind,
            "expected": expected,
            "got": None if got is None else got.text,
            "value": None if got is None else got.value,
        }
    )


def iou(a: Box, b: Box) -> float:
    ix = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    iy = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    inter = ix * iy
    union = (a.x1 - a.x0) * (a.y1 - a.y0) + (b.x1 - b.x0) * (b.y1 - b.y0) - inter
    return inter / union if union > 0 else 0.0


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 4)
