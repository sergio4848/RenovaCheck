"""Turns uploaded bytes into pages: rendered images plus positioned words.

PDF pages use their text layer when it holds enough characters; pages without one (and images)
go to the OCR adapter when one is configured. Rendering uses pdfium (Apache-2.0/BSD).
"""

from __future__ import annotations

import io
import math
import time

import pypdfium2 as pdfium
from PIL import Image, UnidentifiedImageError

from renova_extract.core.errors import UnsupportedDocumentError
from renova_extract.documents.models import LoadedDocument, Page, TextSource, Word
from renova_extract.documents.sniff import JPEG, PDF, PNG, sniff_mime
from renova_extract.ocr.base import OcrAdapter, OcrUnavailableError

RENDER_DPI = 150
MIN_TEXT_LAYER_CHARS = 20
# Resource caps: a tiny PDF can declare a 200x200 inch page, an image can claim gigapixels.
MAX_PAGE_PIXELS = 25_000_000
MAX_IMAGE_PIXELS = 40_000_000
MAX_CHARS_PER_PAGE = 100_000
MIN_DPI, MAX_DPI = 30, 1200
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS  # Pillow's own check; _load_image also checks before decoding


def load_document(
    data: bytes, max_pages: int, ocr: OcrAdapter | None, ocr_budget_seconds: float = 150.0
) -> LoadedDocument:
    mime = sniff_mime(data)
    if mime == PDF:
        pages = _load_pdf(data, max_pages)
    elif mime in (PNG, JPEG):
        pages = [_load_image(data)]
    else:
        raise UnsupportedDocumentError("Only PDF, PNG and JPEG documents are supported.")
    if ocr is not None:
        # One overall OCR budget per document; pages beyond it stay without text.
        deadline = time.monotonic() + ocr_budget_seconds
        for page in pages:
            if page.source is TextSource.NONE and time.monotonic() < deadline:
                _ocr_page(page, ocr)
    return LoadedDocument(mime=mime, pages=pages)


def _load_pdf(data: bytes, max_pages: int) -> list[Page]:
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        raise UnsupportedDocumentError("The PDF cannot be opened (damaged or password-protected).") from exc
    try:
        if len(pdf) == 0:
            raise UnsupportedDocumentError("The PDF has no pages.")
        if len(pdf) > max_pages:
            raise UnsupportedDocumentError(
                f"The PDF has more than {max_pages} pages.", details={"max_pages": max_pages}
            )
        pages = []
        for index in range(len(pdf)):
            page = pdf[index]
            width, height = page.get_size()
            image = page.render(scale=render_scale(width, height), grayscale=True).to_pil().convert("L")
            words = text_layer_words(page, width, height)
            chars = sum(len(w.text) for w in words)
            source = TextSource.TEXT_LAYER if chars >= MIN_TEXT_LAYER_CHARS else TextSource.NONE
            pages.append(Page(index + 1, width, height, image, words if chars else [], source))
            page.close()
        return pages
    finally:
        pdf.close()


def render_scale(width_pt: float, height_pt: float) -> float:
    """150 dpi, lowered for oversized pages so no page renders above MAX_PAGE_PIXELS."""
    if width_pt <= 0 or height_pt <= 0:
        raise UnsupportedDocumentError("The PDF has a page without a size.")
    scale = RENDER_DPI / 72
    pixels = width_pt * height_pt * scale * scale
    if pixels > MAX_PAGE_PIXELS:
        scale *= math.sqrt(MAX_PAGE_PIXELS / pixels)
    return scale


def text_layer_words(page: pdfium.PdfPage, width: float, height: float) -> list[Word]:
    textpage = page.get_textpage()
    try:
        if textpage.count_chars() > MAX_CHARS_PER_PAGE:
            raise UnsupportedDocumentError("A page holds more text than a document of this kind can.")
        words: list[Word] = []
        chars: list[str] = []
        box: list[float] | None = None
        for index in range(textpage.count_chars()):
            char = textpage.get_text_range(index, 1)
            if not char or char.isspace() or char == "\x00":
                if chars and box is not None:
                    words.append(_word("".join(chars), box, width, height))
                chars, box = [], None
                continue
            left, bottom, right, top = textpage.get_charbox(index, loose=False)
            chars.append(char)
            box = (
                [left, bottom, right, top]
                if box is None
                else [min(box[0], left), min(box[1], bottom), max(box[2], right), max(box[3], top)]
            )
        if chars and box is not None:
            words.append(_word("".join(chars), box, width, height))
        return words
    finally:
        textpage.close()


def _word(text: str, box: list[float], width: float, height: float) -> Word:
    left, bottom, right, top = box
    return Word(
        text=text,
        x0=max(0.0, left / width),
        y0=max(0.0, (height - top) / height),
        x1=min(1.0, right / width),
        y1=min(1.0, (height - bottom) / height),
    )


def _load_image(data: bytes) -> Page:
    try:
        image = Image.open(io.BytesIO(data))  # reads the header only
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise UnsupportedDocumentError("The image is too large.")
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise UnsupportedDocumentError("The image cannot be decoded.") from exc
    declared = image.info.get("dpi", (RENDER_DPI, RENDER_DPI))[0] or RENDER_DPI
    dpi = min(MAX_DPI, max(MIN_DPI, float(declared)))
    gray = image.convert("L")
    return Page(1, gray.width * 72 / dpi, gray.height * 72 / dpi, gray, [], TextSource.NONE)


def _ocr_page(page: Page, ocr: OcrAdapter) -> None:
    try:
        page.words = ocr.recognize(page.image)
    except OcrUnavailableError:
        return
    if page.words:
        page.source = TextSource.OCR
