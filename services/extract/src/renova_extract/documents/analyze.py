"""Document analysis: load, render, read text (text layer or OCR), classify, store page images."""

from __future__ import annotations

import io
import re
import threading
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, Field

from renova_extract.classify.classifier import DocTypeClassifier
from renova_extract.core.config import Settings
from renova_extract.core.errors import DependencyUnavailableError, ValidationFailedError
from renova_extract.documents.loader import RENDER_DPI, load_document
from renova_extract.documents.storage import ObjectStore
from renova_extract.ocr.base import OcrAdapter
from renova_extract.ocr.tesseract import TesseractPol

# org/<uuid>/cases/<uuid>/documents/<uuid>/ — assigned by the web application.
OUTPUT_PREFIX = re.compile(r"^org/[0-9a-f-]{36}/cases/[0-9a-f-]{36}/documents/[0-9a-f-]{36}/$")


class AnalyzeRequest(BaseModel):
    document_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    source_url: str = Field(max_length=4096)
    output_prefix: str = Field(max_length=200)


class PageInfo(BaseModel):
    page_no: int
    width_pt: float
    height_pt: float
    image_key: str
    image_width_px: int
    image_height_px: int
    text_source: str
    word_count: int


class ClassificationInfo(BaseModel):
    doc_type: str | None
    confidence: float
    scores: dict[str, int]
    evidence: list[str]
    method: str = "keywords"


class AnalyzeResponse(BaseModel):
    document_id: str
    mime: str
    page_count: int
    pages: list[PageInfo]
    classification: ClassificationInfo
    ocr_provider: str


@dataclass
class Analyzer:
    settings: Settings
    classifier: DocTypeClassifier
    store: ObjectStore
    ocr: OcrAdapter | None
    slots: threading.BoundedSemaphore = field(default_factory=lambda: threading.BoundedSemaphore(2))
    slot_timeout_seconds: float = 30.0

    @classmethod
    def build(cls, settings: Settings, store: ObjectStore) -> Analyzer:
        classifier = DocTypeClassifier.from_yaml(settings.rules_dir / "doc_types.yaml")
        return cls(settings, classifier, store, ocr_adapter(settings))

    def check_request(self, request: AnalyzeRequest) -> None:
        """The prefix must be the document's own, and the source must live under that prefix."""
        prefix = request.output_prefix
        if not OUTPUT_PREFIX.fullmatch(prefix) or not prefix.endswith(f"/documents/{request.document_id}/"):
            raise ValidationFailedError("output_prefix does not match the document.")
        source_path = unquote(urlsplit(request.source_url).path)
        if not source_path.startswith(f"/{self.settings.s3_bucket}/{prefix}original."):
            raise ValidationFailedError("source_url does not belong to the output prefix.")

    def analyze(self, request: AnalyzeRequest, data: bytes) -> AnalyzeResponse:
        self.check_request(request)
        # Bounded concurrency: rendering and OCR are memory- and CPU-heavy; callers retry on 503.
        if not self.slots.acquire(timeout=self.slot_timeout_seconds):
            raise DependencyUnavailableError("The analysis service is busy.")
        try:
            return self._analyze(request, data)
        finally:
            self.slots.release()

    def _analyze(self, request: AnalyzeRequest, data: bytes) -> AnalyzeResponse:
        document = load_document(data, self.settings.max_pages, self.ocr, self.settings.ocr_budget_seconds)
        pages = []
        for page in document.pages:
            key = f"{request.output_prefix}pages/{page.number:03d}.png"
            buffer = io.BytesIO()
            page.image.save(buffer, "PNG", optimize=True, dpi=(RENDER_DPI, RENDER_DPI))
            self.store.put(key, buffer.getvalue(), "image/png")
            pages.append(
                PageInfo(
                    page_no=page.number,
                    width_pt=round(page.width_pt, 2),
                    height_pt=round(page.height_pt, 2),
                    image_key=key,
                    image_width_px=page.image.width,
                    image_height_px=page.image.height,
                    text_source=page.source.value,
                    word_count=len(page.words),
                )
            )
        result = self.classifier.classify(document.text)
        return AnalyzeResponse(
            document_id=request.document_id,
            mime=document.mime,
            page_count=len(pages),
            pages=pages,
            classification=ClassificationInfo(
                doc_type=result.doc_type,
                confidence=result.confidence,
                scores=result.scores,
                evidence=list(result.evidence),
            ),
            ocr_provider=self.ocr.name if self.ocr else "none",
        )


def ocr_adapter(settings: Settings) -> OcrAdapter | None:
    if settings.ocr_provider == "tesseract":
        return TesseractPol()
    # Cloud adapters (azure, google) arrive with phase 4; text_layer means no OCR fallback.
    return None
