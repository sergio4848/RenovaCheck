"""Optional LLM helper for fields the deterministic extractors did not find.

The helper only *proposes* text spans. A proposal is kept when (1) it names a field that was
asked for, (2) its text occurs verbatim (up to whitespace) on the page it names, and (3) the
text parses as a value of the field's type. Everything else is discarded, so the model can
never introduce a value that is not printed in the document. Kept values carry method ``llm``
and a capped confidence, and like all findings they go to a person for review.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from renova_extract.core.config import Settings
from renova_extract.core.logging import get_logger
from renova_extract.fields import normalize as norm
from renova_extract.fields.dictionary import FieldSpec
from renova_extract.fields.extractors import METHOD_CONFIDENCE, ExtractedField
from renova_extract.fields.layout import PageLayout, Span

log = get_logger("renova_extract.fields.llm")

MAX_PAGE_CHARS = 12_000
MAX_PROPOSALS = 50


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=64)
    text: str = Field(min_length=1, max_length=200)
    page: int = Field(ge=1, le=500)


class Proposals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[Proposal] = Field(max_length=MAX_PROPOSALS)


class FieldHelper(Protocol):
    name: str

    def propose(self, specs: list[FieldSpec], pages: list[tuple[int, str]]) -> list[Proposal]: ...


@dataclass
class FakeFieldHelper:
    """Returns fixed proposals; for tests and local runs without network access."""

    proposals: list[Proposal]
    name: str = "fake"

    def propose(self, specs: list[FieldSpec], pages: list[tuple[int, str]]) -> list[Proposal]:
        return list(self.proposals)


SYSTEM_PROMPT = (
    "You read Polish building-renovation documents (offers, contracts, invoices, acceptance protocols, "
    "product cards). For each requested field, copy the value exactly as it is printed in the page text, "
    "character for character, or leave the field out when it is not printed. Never compute, translate, "
    "reformat or guess values. Answer with JSON only: "
    '{"fields": [{"name": "<field name>", "text": "<verbatim text>", "page": <page number>}]}'
)


@dataclass
class AnthropicFieldHelper:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float
    name: str = "anthropic"

    def propose(self, specs: list[FieldSpec], pages: list[tuple[int, str]]) -> list[Proposal]:
        requested = "\n".join(f"- {s.name}: {s.label_pl}" for s in specs)
        text = "\n\n".join(f"<page number={n}>\n{t[:MAX_PAGE_CHARS]}\n</page>" for n, t in pages)
        body = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": 0,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": f"Fields:\n{requested}\n\nDocument:\n{text}"}],
        }
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/v1/messages",
                json=body,
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            content = response.json()["content"]
            answer = "".join(block.get("text", "") for block in content if block.get("type") == "text")
            return Proposals.model_validate(json.loads(_json_object(answer))).fields
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
            # The helper is optional: a failure leaves the fields missing, it never fails the analysis.
            log.warning("llm.proposal_failed", provider=self.name, error=type(exc).__name__)
            return []


def _json_object(answer: str) -> str:
    start, end = answer.find("{"), answer.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the answer")
    return answer[start : end + 1]


def build_helper(settings: Settings) -> FieldHelper | None:
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key is not None:
        return AnthropicFieldHelper(
            settings.anthropic_api_key.get_secret_value(),
            settings.llm_model,
            settings.anthropic_base_url,
            settings.llm_timeout_seconds,
        )
    if settings.llm_provider == "fake":
        return FakeFieldHelper([])
    return None


_WS = re.compile(r"\s+")


def accept(proposals: list[Proposal], specs: list[FieldSpec], pages: list[PageLayout]) -> list[ExtractedField]:
    """Proposals that pass the verbatim, field and type checks, at most one per field."""
    by_name = {s.name: s for s in specs}
    by_page = {p.page.number: p for p in pages}
    accepted: dict[str, ExtractedField] = {}
    for proposal in proposals:
        spec = by_name.get(proposal.name)
        page = by_page.get(proposal.page)
        if spec is None or page is None or spec.name in accepted:
            continue
        located = _locate(_WS.sub(" ", proposal.text).strip(), page)
        if located is None:
            log.info("llm.proposal_rejected", field=spec.name, reason="not_in_page")
            continue
        span, start, end = located
        value = norm.normalize(spec.type, span.text[start:end])
        if value is None:
            log.info("llm.proposal_rejected", field=spec.name, reason="not_a_value")
            continue
        box, ocr_confidence = span.sub(start, end)
        accepted[spec.name] = ExtractedField(
            spec.name,
            value,
            span.text[start:end],
            page.page.number,
            box,
            "llm",
            METHOD_CONFIDENCE["llm"] * ocr_confidence,
        )
    return list(accepted.values())


def _locate(text: str, page: PageLayout) -> tuple[Span, int, int] | None:
    if not text:
        return None
    for line in page.lines:
        span = line.span
        start = span.text.find(text)
        if start >= 0:
            return span, start, start + len(text)
    return None
