"""Writes a synthetic dataset: one directory per case with its PDFs and ground_truth.json."""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from renova_synth.model import CaseTruth, DocumentTruth, FieldTruth, Quality
from renova_synth.render.canvas import PAGE_H, PAGE_W
from renova_synth.render.documents import render
from renova_synth.scan import degrade, transform_bbox
from renova_synth.scenario import CasePlan, DocSpec, plan_case

FILE_ORDER = {
    "wniosek_ekstrakt": "01",
    "oferta": "02",
    "umowa": "02",
    "aneks": "03",
    "faktura_zaliczkowa": "04",
    "faktura": "05",
    "faktura_korygujaca": "06",
    "protokol_odbioru": "07",
    "karta_produktu": "08",
}


@dataclass(frozen=True)
class DatasetSummary:
    cases: int
    documents: int
    by_type: dict[str, int]
    scans: int
    errors: dict[str, int]


def generate(out_dir: Path, cases: int, seed: int) -> DatasetSummary:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    truths = [write_case(out_dir, plan_case(seed, n)) for n in range(1, cases + 1)]
    summary = _summarize(truths)
    manifest = {
        "seed": seed,
        "cases": [t.case_id for t in truths],
        "documents": summary.documents,
        "documents_by_type": summary.by_type,
        "scanned_documents": summary.scans,
        "injected_errors_by_type": summary.errors,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return summary


def write_case(out_dir: Path, plan: CasePlan) -> CaseTruth:
    case_dir = out_dir / plan.case_id
    (case_dir / "documents").mkdir(parents=True)
    documents = []
    for doc in plan.documents:
        documents.append(_write_document(case_dir, plan, doc))
    truth = CaseTruth(
        case_id=plan.case_id,
        seed=plan.seed,
        contract_kind=plan.contract_kind,
        scenario=plan.scenario,
        facts=plan.facts,
        documents=tuple(documents),
        injected_errors=tuple(plan.errors),
        expected_findings=tuple(plan.findings),
    )
    (case_dir / "ground_truth.json").write_text(truth.model_dump_json(indent=2) + "\n")
    return truth


def _write_document(case_dir: Path, plan: CasePlan, doc: DocSpec) -> DocumentTruth:
    rng = random.Random(f"{plan.seed}-{doc.doc_id}")
    pdf, canvas = render(doc, rng)
    fields = [
        FieldTruth(name=p.name, text=p.text, value=p.value, page=p.page, bbox=p.bbox, injected_error=p.error_id)
        for p in canvas.placed
    ]
    quality = Quality.CLEAN
    if doc.scan:
        scan = degrade(pdf, seed=int(hashlib.sha256(doc.doc_id.encode()).hexdigest()[:8], 16))
        pdf = scan.pdf
        quality = Quality.SCAN
        fields = [
            f.model_copy(update={"bbox": transform_bbox(f.bbox, scan.angles[f.page - 1], PAGE_W, PAGE_H)})
            for f in fields
        ]
    file_name = f"{FILE_ORDER[doc.doc_type.value]}_{doc.doc_type.value}.pdf"
    path = case_dir / "documents" / file_name
    path.write_bytes(pdf)
    return DocumentTruth(
        doc_id=doc.doc_id,
        doc_type=doc.doc_type,
        file=f"documents/{file_name}",
        sha256=hashlib.sha256(pdf).hexdigest(),
        pages=canvas.page,
        quality=quality,
        template=doc.template,
        issue_date=doc.issue_date,
        fields=tuple(fields),
    )


def _summarize(truths: list[CaseTruth]) -> DatasetSummary:
    by_type: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    scans = 0
    for truth in truths:
        for doc in truth.documents:
            by_type[doc.doc_type.value] += 1
            scans += doc.quality is Quality.SCAN
        for err in truth.injected_errors:
            errors[err.type.value] += 1
    return DatasetSummary(
        cases=len(truths),
        documents=sum(by_type.values()),
        by_type=dict(sorted(by_type.items())),
        scans=scans,
        errors=dict(sorted(errors.items())),
    )
