"""POST /v1/documents/analyze — called by the web application's queue job."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from renova_extract.api.deps import require_internal_token
from renova_extract.core.logging import get_logger
from renova_extract.documents.analyze import Analyzer, AnalyzeRequest, AnalyzeResponse
from renova_extract.documents.fetch import download

router = APIRouter(prefix="/v1/documents", tags=["documents"], dependencies=[Depends(require_internal_token)])
log = get_logger(__name__)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(body: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    # Sync handler: FastAPI runs it in the threadpool, keeping CPU-bound rendering off the event loop.
    analyzer: Analyzer = request.app.state.analyzer
    analyzer.check_request(body)
    data = download(body.source_url, analyzer.settings)
    result = analyzer.analyze(body, data)
    log.info(
        "document.analyzed",
        document_id=body.document_id,
        pages=result.page_count,
        doc_type=result.classification.doc_type,
        ocr=result.ocr_provider,
    )
    return result
