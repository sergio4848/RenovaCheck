from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pypdfium2 as pdfium

from renova_synth.generate import generate
from renova_synth.model import CaseTruth, DocType, ErrorType, Quality
from renova_synth.validate import SCHEMA_PATH, schema, validate_dataset

CORE_TYPES = {
    DocType.WNIOSEK_EKSTRAKT,
    DocType.FAKTURA,
    DocType.PROTOKOL_ODBIORU,
    DocType.KARTA_PRODUKTU,
}


def _truths(root: Path) -> list[CaseTruth]:
    return [CaseTruth.model_validate_json(p.read_text()) for p in sorted(root.glob("SYN-*/ground_truth.json"))]


def test_dataset_validates_against_committed_schema(dataset: Path) -> None:
    report = validate_dataset(dataset)
    assert report.problems == []
    assert report.cases == 20
    assert report.documents >= 100


def test_committed_schema_matches_the_model() -> None:
    assert json.loads(SCHEMA_PATH.read_text()) == schema(), "run: renova-synth schema"


def test_twenty_cases_with_five_document_slots_each(dataset: Path) -> None:
    truths = _truths(dataset)
    assert len(truths) == 20
    for truth in truths:
        types = {d.doc_type for d in truth.documents}
        assert {DocType.WNIOSEK_EKSTRAKT, DocType.FAKTURA, DocType.KARTA_PRODUKTU} <= types
        assert len(types & {DocType.OFERTA, DocType.UMOWA}) == 1
        has_protocol = DocType.PROTOKOL_ODBIORU in types
        assert has_protocol != (ErrorType.MISSING_PROTOCOL in truth.scenario)
    core = sum(1 for t in truths for d in t.documents if d.doc_type in CORE_TYPES | {DocType.OFERTA, DocType.UMOWA})
    missing = sum(ErrorType.MISSING_PROTOCOL in t.scenario for t in truths)
    assert core == 100 - missing


def test_every_error_type_is_injected_and_extra_invoices_are_about_thirty_percent(dataset: Path) -> None:
    truths = _truths(dataset)
    injected = Counter(e.type for t in truths for e in t.injected_errors)
    assert set(injected) == set(ErrorType)
    with_extra_invoice = sum(
        any(d.doc_type in {DocType.FAKTURA_ZALICZKOWA, DocType.FAKTURA_KORYGUJACA} for d in t.documents) for t in truths
    )
    assert with_extra_invoice == 6
    clean_cases = [t for t in truths if not t.scenario]
    assert clean_cases, "some cases must stay clean to measure false positives"


def test_generation_is_byte_for_byte_reproducible(tmp_path: Path) -> None:
    def digest(root: Path) -> dict[str, str]:
        return {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    generate(tmp_path / "a", cases=4, seed=7)
    generate(tmp_path / "b", cases=4, seed=7)
    generate(tmp_path / "c", cases=4, seed=8)
    assert digest(tmp_path / "a") == digest(tmp_path / "b")
    assert digest(tmp_path / "a") != digest(tmp_path / "c")


def test_each_clean_field_is_printed_inside_its_bounding_box(dataset: Path) -> None:
    checked = 0
    for truth in _truths(dataset):
        for doc in truth.documents:
            if doc.quality is not Quality.CLEAN:
                continue
            pdf = pdfium.PdfDocument(str(dataset / truth.case_id / doc.file))
            try:
                for f in doc.fields:
                    if not f.text:
                        continue  # signature areas carry no text
                    page = pdf[f.page - 1]
                    width, height = page.get_size()
                    text = page.get_textpage().get_text_bounded(
                        left=f.bbox.x0 * width - 1,
                        right=f.bbox.x1 * width + 1,
                        top=height - f.bbox.y0 * height + 1,
                        bottom=height - f.bbox.y1 * height - 1,
                    )
                    assert f.text in " ".join(text.split()), f"{doc.doc_id} {f.name}: {f.text!r} not in {text!r}"
                    checked += 1
            finally:
                pdf.close()
    assert checked > 1000


def test_scanned_documents_have_no_text_layer(dataset: Path) -> None:
    scans = [(t, d) for t in _truths(dataset) for d in t.documents if d.quality is Quality.SCAN]
    assert len(scans) >= 6
    for truth, doc in scans:
        pdf = pdfium.PdfDocument(str(dataset / truth.case_id / doc.file))
        try:
            assert pdf[0].get_textpage().get_text_range().strip() == ""
        finally:
            pdf.close()


def test_injected_errors_are_visible_in_the_written_values(dataset: Path) -> None:
    for truth in _truths(dataset):
        for err in truth.injected_errors:
            # A spelling variant keeps its canonical value; a correction's written value is the
            # corrected total across invoices, not a value printed on one document.
            derived = {ErrorType.STREET_SPELLING_VARIANT, ErrorType.CORRECTION_INVOICE}
            if err.doc_id is None or err.field is None or err.type in derived:
                continue
            doc = next(d for d in truth.documents if d.doc_id == err.doc_id)
            values = [f.value for f in doc.fields if f.name == err.field]
            assert err.written_value in values, f"{err.error_id}: {err.written_value} not in {values}"


def test_every_document_marks_itself_synthetic(dataset: Path) -> None:
    truth = _truths(dataset)[0]
    pdf = pdfium.PdfDocument(str(dataset / truth.case_id / truth.documents[0].file))
    try:
        assert "DOKUMENT SYNTETYCZNY" in pdf[0].get_textpage().get_text_range()
    finally:
        pdf.close()
