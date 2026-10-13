"""Document type accuracy on a synthetic dataset (tools/synth output)."""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from renova_extract.classify.classifier import DocTypeClassifier
from renova_extract.documents.loader import load_document
from renova_extract.ocr.base import OcrAdapter


@dataclass
class DocResult:
    doc_id: str
    expected: str
    predicted: str | None
    quality: str
    text_source: str
    confidence: float


@dataclass
class ClassificationReport:
    ocr: str
    results: list[DocResult] = field(default_factory=list)
    seconds: float = 0.0

    def accuracy(self, quality: str | None = None) -> tuple[int, int]:
        rows = [r for r in self.results if quality is None or r.quality == quality]
        return sum(r.predicted == r.expected for r in rows), len(rows)

    def confusion(self) -> dict[str, dict[str, int]]:
        table: dict[str, Counter[str]] = {}
        for r in self.results:
            table.setdefault(r.expected, Counter())[r.predicted or "unknown"] += 1
        return {k: dict(v) for k, v in sorted(table.items())}

    def as_dict(self) -> dict[str, Any]:
        correct, total = self.accuracy()
        return {
            "ocr": self.ocr,
            "accuracy": round(correct / total, 4) if total else None,
            "correct": correct,
            "total": total,
            "by_quality": {
                q: dict(zip(("correct", "total"), self.accuracy(q), strict=True)) for q in ("clean", "scan")
            },
            "confusion": self.confusion(),
            "seconds": round(self.seconds, 1),
            "errors": [asdict(r) for r in self.results if r.predicted != r.expected],
        }


def evaluate(
    dataset: Path, classifier: DocTypeClassifier, ocr: OcrAdapter | None, max_pages: int = 50
) -> ClassificationReport:
    report = ClassificationReport(ocr=ocr.name if ocr else "none")
    started = time.perf_counter()
    for truth_file in sorted(dataset.glob("SYN-*/ground_truth.json")):
        truth = json.loads(truth_file.read_text())
        for doc in truth["documents"]:
            loaded = load_document((truth_file.parent / doc["file"]).read_bytes(), max_pages, ocr)
            result = classifier.classify(loaded.text)
            report.results.append(
                DocResult(
                    doc_id=doc["doc_id"],
                    expected=doc["doc_type"],
                    predicted=result.doc_type,
                    quality=doc["quality"],
                    text_source=",".join(sorted({p.source.value for p in loaded.pages})),
                    confidence=result.confidence,
                )
            )
    report.seconds = time.perf_counter() - started
    return report
