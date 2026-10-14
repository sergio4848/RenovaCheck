from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from renova_extract.core.errors import UnsupportedDocumentError
from renova_extract.documents.loader import load_document
from renova_extract.documents.models import TextSource
from renova_extract.documents.sniff import JPEG, PDF, PNG, sniff_mime
from renova_extract.ocr.tesseract import TesseractPol, parse_tsv

FIXTURES = Path(__file__).parent / "fixtures"
needs_tesseract = pytest.mark.skipif(not TesseractPol().available(), reason="tesseract not installed")


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("L", (200, 100), 255).save(buffer, "PNG")
    return buffer.getvalue()


def test_sniff_by_content_not_name() -> None:
    assert sniff_mime(b"%PDF-1.7\n...") == PDF
    assert sniff_mime(_png()) == PNG
    assert sniff_mime(b"\xff\xd8\xff\xe0rest") == JPEG
    assert sniff_mime(b"<html>%PDF-1.7</html>") is None
    assert sniff_mime(b"MZ\x90\x00") is None


def test_clean_pdf_uses_text_layer_with_positioned_words() -> None:
    doc = load_document((FIXTURES / "faktura_clean.pdf").read_bytes(), max_pages=50, ocr=None)
    assert doc.mime == PDF
    page = doc.pages[0]
    assert page.source is TextSource.TEXT_LAYER
    assert "Faktura" in page.text and "FV/145/05/2026" in page.text
    number = next(w for w in page.words if w.text == "FV/145/05/2026")
    assert 0 < number.x0 < number.x1 < 1 and 0 < number.y0 < number.y1 < 0.2
    assert page.image.mode == "L" and page.image.width > 1000


def test_scanned_pdf_has_no_text_without_ocr() -> None:
    doc = load_document((FIXTURES / "faktura_scan.pdf").read_bytes(), max_pages=50, ocr=None)
    assert doc.pages[0].source is TextSource.NONE
    assert doc.text == ""


@needs_tesseract
def test_scanned_pdf_is_read_with_tesseract() -> None:
    doc = load_document((FIXTURES / "faktura_scan.pdf").read_bytes(), max_pages=50, ocr=TesseractPol())
    page = doc.pages[0]
    assert page.source is TextSource.OCR
    assert "Faktura" in page.text
    assert all(0 <= w.x0 < w.x1 <= 1 and 0 <= w.y0 < w.y1 <= 1 for w in page.words)


def test_page_limit_and_unsupported_content() -> None:
    with pytest.raises(UnsupportedDocumentError):
        load_document((FIXTURES / "faktura_clean.pdf").read_bytes(), max_pages=0, ocr=None)
    with pytest.raises(UnsupportedDocumentError):
        load_document(b"just text", max_pages=50, ocr=None)
    with pytest.raises(UnsupportedDocumentError):
        load_document(b"%PDF-1.7 truncated garbage", max_pages=50, ocr=None)


def test_images_become_a_single_page() -> None:
    doc = load_document(_png(), max_pages=50, ocr=None)
    assert doc.mime == PNG and len(doc.pages) == 1
    assert doc.pages[0].source is TextSource.NONE


def test_parse_tesseract_tsv() -> None:
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "1\t1\t0\t0\t0\t0\t0\t0\t1000\t500\t-1\t\n"
        "5\t1\t1\t1\t1\t1\t100\t50\t200\t20\t91.5\tFaktura\n"
        "5\t1\t1\t1\t1\t2\t310\t50\t60\t20\t-1\t \n"
        "5\t1\t1\t1\t1\t3\t400\t50\t100\t20\t88\tVAT\n"
    )
    words = parse_tsv(tsv, 1000, 500)
    assert [w.text for w in words] == ["Faktura", "VAT"]
    assert words[0].x0 == 0.1 and words[0].y1 == pytest.approx(0.14)
    assert words[0].confidence == pytest.approx(0.915)


def test_oversized_pdf_pages_render_within_the_pixel_cap() -> None:
    import pypdfium2 as pdfium

    from renova_extract.documents.loader import MAX_PAGE_PIXELS

    pdf = pdfium.PdfDocument.new()
    pdf.new_page(14400, 14400)
    buffer = io.BytesIO()
    pdf.save(buffer)
    doc = load_document(buffer.getvalue(), max_pages=50, ocr=None)
    image = doc.pages[0].image
    assert image.width * image.height <= MAX_PAGE_PIXELS
    assert doc.pages[0].width_pt == pytest.approx(14400)


def test_images_beyond_the_pixel_cap_are_rejected_before_decoding() -> None:
    buffer = io.BytesIO()
    Image.new("1", (9000, 5000), 1).save(buffer, "PNG")  # 45 MP, a few kB compressed
    with pytest.raises(UnsupportedDocumentError):
        load_document(buffer.getvalue(), max_pages=50, ocr=None)


def test_absurd_dpi_metadata_is_clamped() -> None:
    buffer = io.BytesIO()
    Image.new("L", (300, 300), 255).save(buffer, "PNG", dpi=(1, 1))
    page = load_document(buffer.getvalue(), max_pages=50, ocr=None).pages[0]
    assert page.width_pt == pytest.approx(300 * 72 / 30)
