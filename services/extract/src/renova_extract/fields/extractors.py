"""Deterministic field extraction with provenance.

Each field in ``packages/rules/fields.yaml`` lists extraction methods; they run in order and
the first one that finds the field decides it. A value is either ``ok`` (parsed and normalized)
or ``unreadable`` (the label was found but the text next to it is not a value of the field's
type, typically on a poor scan). A field that is not found at all is simply absent.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from renova_extract.documents.models import Page, Word
from renova_extract.fields import normalize as norm
from renova_extract.fields.dictionary import ExtractRule, FieldDictionary, FieldSpec
from renova_extract.fields.layout import (
    SEGMENT_GAP,
    Box,
    Line,
    PageLayout,
    Span,
    anchor_tokens,
    find_anchor,
    layout,
    segment_is,
)
from renova_extract.fields.signature import region_box, signature_region

Status = Literal["ok", "unreadable"]

# Method weights for confidence; OCR word confidence multiplies in.
METHOD_CONFIDENCE = {
    "label": 0.98,
    "title_number": 0.95,
    "address": 0.95,
    "block": 0.9,
    "above": 0.85,
    "signature": 0.9,
    "llm": 0.5,
}
ADDRESS = re.compile(
    r"^(?P<street>\S.*?)\s+(?P<building_no>\d{1,4}[A-Za-z]?(?:/\d{1,4}[A-Za-z]?)?)\s*,\s*"
    r"(?P<postal_code>\d{2}\s?-\s?\d{3})\s+(?P<city>\S.*?)\s*$"
)
ADDRESS_PARTS = {
    "street": "address_street",
    "building_no": "address_building_no",
    "postal_code": "address_postal_code",
    "city": "address_city",
}
HEADER_AREA = 0.25  # document numbers sit in the top quarter of page 1
BLOCK_COLUMN_TOLERANCE = 0.03
BLOCK_MAX_LINES_BELOW = 4.0


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: norm.Normalized | None
    text: str
    page: int
    bbox: Box
    method: str
    confidence: float
    status: Status = "ok"

    def as_dict(self, doc_id: str) -> dict[str, object]:
        return {
            "name": self.name,
            "value": self.value,
            "text": self.text,
            "doc_id": doc_id,
            "page": self.page,
            "bbox": self.bbox.as_dict(),
            "method": self.method,
            "confidence": round(self.confidence, 3),
            "status": self.status,
        }


@dataclass
class _Context:
    pages: list[PageLayout]
    address: dict[str, ExtractedField] | None = None
    address_done: bool = False


class FieldExtractor:
    def __init__(self, dictionary: FieldDictionary) -> None:
        self.dictionary = dictionary
        self._methods: dict[str, Callable[[FieldSpec, ExtractRule, _Context], ExtractedField | None]] = {
            "label": self._label,
            "block": self._block,
            "above": self._above,
            "title_number": self._title_number,
            "address": self._address,
            "signature": self._signature,
        }

    def extract(self, pages: list[Page], doc_type: str | None) -> list[ExtractedField]:
        return self.extract_layout(layout(pages), doc_type)

    def extract_layout(self, pages: list[PageLayout], doc_type: str | None) -> list[ExtractedField]:
        context = _Context(pages)
        results: list[ExtractedField] = []
        for spec in self.dictionary.fields_for(doc_type):
            found: ExtractedField | None = None
            for rule in spec.extract:
                candidate = self._methods[rule.method](spec, rule, context)
                if candidate is None:
                    continue
                if candidate.status == "ok":
                    found = candidate
                    break
                found = found or candidate  # keep the first unreadable one, look for a readable one
            if found is not None:
                results.append(found)
        return results

    # ------------------------------------------------------------------ methods
    def _label(self, spec: FieldSpec, rule: ExtractRule, context: _Context) -> ExtractedField | None:
        unreadable: ExtractedField | None = None
        for anchor in rule.anchors:
            tokens = anchor_tokens(anchor)
            for page in context.pages:
                for line in page.lines:
                    start = 0
                    while (end := find_anchor(line.words, tokens, start)) is not None:
                        start = end
                        rest = line.span.after(end) or _continuation(page.lines, line, line.words[end - 1])
                        if rest is None:
                            continue
                        candidate = _value_in(spec, rest, line, page.page.number, "label")
                        if candidate is None:
                            continue
                        if candidate.status == "ok":
                            return candidate
                        # A bare word ("VAT" in "Faktura VAT nr") is not a label; only a phrase or
                        # a word ending in ':' promises a value, and only then is a miss unreadable.
                        if len(tokens) > 1 or line.words[end - 1].text.endswith(":"):
                            unreadable = unreadable or candidate
        return unreadable

    def _block(self, spec: FieldSpec, rule: ExtractRule, context: _Context) -> ExtractedField | None:
        for anchor in rule.anchors:
            tokens = anchor_tokens(anchor)
            for page in context.pages:
                for index, line in enumerate(page.lines):
                    for heading in line.segments:
                        if not segment_is(heading, tokens):
                            continue
                        below = _segment_below(page.lines, index, heading)
                        if below is not None:
                            return _whole(spec, below, page.page.number, "block")
        return None

    def _above(self, spec: FieldSpec, rule: ExtractRule, context: _Context) -> ExtractedField | None:
        for anchor in rule.anchors:
            tokens = anchor_tokens(anchor)
            for page in context.pages:
                for index, line in enumerate(page.lines):
                    if index == 0 or find_anchor(line.words, tokens) is None:
                        continue
                    x0 = line.words[0].x0
                    for segment in page.lines[index - 1].segments:
                        if abs(segment.x0 - x0) <= BLOCK_COLUMN_TOLERANCE:
                            return _whole(spec, segment, page.page.number, "above")
        return None

    def _title_number(self, spec: FieldSpec, rule: ExtractRule, context: _Context) -> ExtractedField | None:
        if not context.pages:
            return None
        page = context.pages[0]
        for line in page.lines:
            if line.y0 > HEADER_AREA:
                break
            end = find_anchor(line.words, ["nr"])
            if end is not None and end < len(line.words):
                return _token_value(spec, line.span.after(end), page.page.number, "title_number")
        return None

    def _address(self, spec: FieldSpec, rule: ExtractRule, context: _Context) -> ExtractedField | None:
        if not context.address_done:
            context.address = _find_address(context.pages)
            context.address_done = True
        return (context.address or {}).get(spec.name)

    def _signature(self, spec: FieldSpec, rule: ExtractRule, context: _Context) -> ExtractedField | None:
        caption: tuple[PageLayout, Span] | None = None
        for page in context.pages:
            for line in page.lines:
                for segment in line.segments:
                    if any(segment_is(segment, anchor_tokens(a)) for a in rule.anchors):
                        caption = (page, segment)  # the last caption in reading order is the signature one
        if caption is None:
            return None
        page, segment = caption
        region = signature_region(page.page, segment.box)
        if region is None:
            return None
        signed, certainty = region
        box = region_box(page.page, segment.box)
        return ExtractedField(
            spec.name,
            signed,
            segment.text,
            page.page.number,
            box,
            "signature",
            METHOD_CONFIDENCE["signature"] * certainty,
        )


# ---------------------------------------------------------------------- helpers
def _value_in(spec: FieldSpec, rest: Span, line: Line, page_no: int, method: str) -> ExtractedField | None:
    """The value of spec's type at the start of ``rest`` (the line after the anchor)."""
    finder = _PATTERN_FINDERS.get(spec.type)
    if finder is not None:
        match = finder(rest.text)
        if match is None:
            return _unreadable(spec, rest, page_no, method)
        return _from_match(spec, rest, match.start(), match.end(), page_no, method)
    if spec.type in ("identifier", "model"):
        return _token_value(spec, rest, page_no, method)
    return _whole(spec, _phrase(rest, line), page_no, method)


def _from_match(spec: FieldSpec, span: Span, start: int, end: int, page_no: int, method: str) -> ExtractedField:
    text = span.text[start:end].strip()
    box, ocr_confidence = span.sub(start, end)
    value = norm.normalize(spec.type, text)
    if value is None:
        return ExtractedField(spec.name, None, text, page_no, box, method, 0.0, "unreadable")
    return ExtractedField(spec.name, value, text, page_no, box, method, METHOD_CONFIDENCE[method] * ocr_confidence)


def _token_value(spec: FieldSpec, rest: Span | None, page_no: int, method: str) -> ExtractedField | None:
    if rest is None:
        return None
    first = rest.words[0].text
    text = norm.strip_punct(first)
    return _from_match(spec, rest, 0, len(text), page_no, method)


def _whole(spec: FieldSpec, span: Span, page_no: int, method: str) -> ExtractedField:
    # Names keep a final period ("Sp. j."); a separating comma or colon is not part of them.
    text = span.text.rstrip(",;:") if spec.type in ("text", "name") else norm.strip_punct(span.text)
    return _from_match(spec, span, 0, len(text), page_no, method)


def _unreadable(spec: FieldSpec, rest: Span, page_no: int, method: str) -> ExtractedField:
    return ExtractedField(spec.name, None, rest.text[:120], page_no, rest.box, method, 0.0, "unreadable")


def _phrase(rest: Span, line: Line) -> Span:
    """Free text after a label: up to a comma or a column gap."""
    height = max(line.y1 - line.y0, 1e-6)
    words: list[Word] = []
    for word in rest.words:
        if words and word.x0 - words[-1].x1 > height * SEGMENT_GAP:
            break
        words.append(word)
        if word.text.endswith((",", ";")):
            break
    return Span(words)


def _continuation(lines: list[Line], line: Line, last: Word) -> Span | None:
    """Words right after ``last`` that line grouping put on a neighbouring line.

    On a skewed scan a long printed line drifts vertically and splits in two; a label then ends
    its line while its value starts the next one at the same height.
    """
    height = last.y1 - last.y0
    centre = (last.y0 + last.y1) / 2
    for other in lines:
        if other is line:
            continue
        following = [w for w in other.words if w.x0 >= last.x1 - height * 0.5]
        if not following:
            continue
        first = following[0]
        if abs((first.y0 + first.y1) / 2 - centre) <= height and first.x0 - last.x1 <= height * SEGMENT_GAP:
            return Span(following)
    return None


def _segment_below(lines: list[Line], index: int, heading: Span) -> Span | None:
    line_height = max(lines[index].y1 - lines[index].y0, 1e-6)
    for line in lines[index + 1 :]:
        if line.y0 - lines[index].y1 > line_height * BLOCK_MAX_LINES_BELOW:
            return None
        for segment in line.segments:
            if abs(segment.x0 - heading.x0) <= BLOCK_COLUMN_TOLERANCE:
                return segment
    return None


def _find_address(pages: list[PageLayout]) -> dict[str, ExtractedField] | None:
    for page in pages:
        for line in page.lines:
            for segment in line.segments:
                match = ADDRESS.match(segment.text)
                if match is None:
                    continue
                fields = {}
                for group, name in ADDRESS_PARTS.items():
                    start, end = match.span(group)
                    box, ocr_confidence = segment.sub(start, end)
                    text = match.group(group)
                    value = norm.normalize(group, text)
                    status: Status = "ok" if value is not None else "unreadable"
                    confidence = METHOD_CONFIDENCE["address"] * ocr_confidence if value is not None else 0.0
                    fields[name] = ExtractedField(
                        name, value, text, page.page.number, box, "address", confidence, status
                    )
                return fields
    return None


def _search(pattern: re.Pattern[str]) -> Callable[[str], re.Match[str] | None]:
    return pattern.search


_PATTERN_FINDERS: dict[str, Callable[[str], re.Match[str] | None]] = {
    "money": norm.money_in,
    "date": _search(norm.DATE),
    "power_kw": _search(norm.POWER),
    "nip": _search(norm.NIP_DIGITS),
}
