"""Rule definitions (packages/rules/rules/*.yaml), the case the rules read and the findings they produce.

A rule file carries the fields the product requires of every rule (id, title_pl, program,
edition, valid_from, valid_to, severity, inputs, comparator, threshold, source_url, notes) plus
``version``, ``family`` and ``emits`` (the outcomes and fields it can report, used to attribute
missed findings in the evaluation). ``threshold`` holds the comparator's parameters; its shape
depends on the comparator, so the generated JSON Schema checks it too.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

DocType = Literal[
    "wniosek_ekstrakt",
    "oferta",
    "umowa",
    "aneks",
    "faktura",
    "faktura_zaliczkowa",
    "faktura_korygujaca",
    "protokol_odbioru",
    "karta_produktu",
]
Family = Literal["address", "product", "amount", "completeness", "quality"]
Severity = Literal["critical", "warning", "info"]
Outcome = Literal[
    "discrepancy",
    "match_after_normalization",
    "agreed_change",
    "explained_by_advance",
    "explained_by_correction",
    "missing_document",
    "unreadable_source",
    "no_rules",
]
ReferenceSource = Literal["application_date", "contract_date", "fallback"]
FieldName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------- rule parameters
class Inputs(_Frozen):
    doc_types: tuple[DocType, ...] = Field(min_length=1)
    fields: tuple[FieldName, ...] = ()


class Emits(_Frozen):
    outcome: Outcome
    fields: tuple[FieldName, ...] = ()


class ConfidenceThreshold(_Frozen):
    # Values read with less confidence neither vote nor get flagged; the quality rule reports them.
    min_confidence: float = Field(default=0.5, ge=0, le=1)


class MajorityThreshold(ConfidenceThreshold):
    # Compare documents before and after an annex separately (the annex legitimately changes them).
    split_on_annex: bool = False


class AmountThreshold(ConfidenceThreshold):
    tolerance_pln: float = Field(default=0.01, ge=0, le=100)


class FieldRef(_Frozen):
    doc_types: tuple[DocType, ...] = Field(min_length=1)
    field: FieldName


class DateOrderThreshold(ConfidenceThreshold):
    later: FieldRef
    earlier: FieldRef
    min_days: int = Field(default=0, ge=0, le=3650)


class RequiredDocumentsThreshold(_Frozen):
    # Each group is satisfied by any one of its document types.
    required: tuple[tuple[DocType, ...], ...] = Field(min_length=1)


class SignatureRequirement(_Frozen):
    doc_type: DocType
    fields: tuple[FieldName, ...] = Field(min_length=1)


class SignaturesThreshold(ConfidenceThreshold):
    required: tuple[SignatureRequirement, ...] = Field(min_length=1)


# --------------------------------------------------------------------------- rules
class _RuleBase(_Frozen):
    id: str = Field(pattern=r"^[A-Z]{3}-\d{2}$")
    version: int = Field(ge=1)
    title_pl: str = Field(min_length=5, max_length=200)
    program: Literal["czyste_powietrze"]
    edition: str = Field(min_length=1, max_length=40)
    family: Family
    valid_from: date
    valid_to: date | None = None
    severity: Severity
    inputs: Inputs
    emits: tuple[Emits, ...] = Field(min_length=1)
    source_url: HttpUrl
    notes: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def _valid_range(self) -> _RuleBase:
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to is before valid_from")
        return self

    @property
    def key(self) -> str:
        return f"{self.id}@{self.version}"

    def valid_on(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day <= self.valid_to)


class MajorityRule(_RuleBase):
    comparator: Literal["majority"]
    threshold: MajorityThreshold = MajorityThreshold()


class StreetSpellingRule(_RuleBase):
    comparator: Literal["street_spelling"]
    threshold: ConfidenceThreshold = ConfidenceThreshold()


class AnnexChangeRule(_RuleBase):
    comparator: Literal["annex_change"]
    threshold: ConfidenceThreshold = ConfidenceThreshold()


class InvoiceTotalRule(_RuleBase):
    comparator: Literal["invoice_total"]
    threshold: AmountThreshold = AmountThreshold()


class AdvanceSettlementRule(_RuleBase):
    comparator: Literal["advance_settlement"]
    threshold: AmountThreshold = AmountThreshold()


class CorrectionRule(_RuleBase):
    comparator: Literal["correction"]
    threshold: AmountThreshold = AmountThreshold()


class ArithmeticRule(_RuleBase):
    comparator: Literal["net_vat_gross"]
    threshold: AmountThreshold = AmountThreshold()


class RequiredDocumentsRule(_RuleBase):
    comparator: Literal["required_documents"]
    threshold: RequiredDocumentsThreshold


class DateOrderRule(_RuleBase):
    comparator: Literal["date_order"]
    threshold: DateOrderThreshold


class SignaturesRule(_RuleBase):
    comparator: Literal["signatures"]
    threshold: SignaturesThreshold


class SourceQualityRule(_RuleBase):
    comparator: Literal["source_quality"]
    threshold: ConfidenceThreshold = ConfidenceThreshold()


Rule = Annotated[
    MajorityRule
    | StreetSpellingRule
    | AnnexChangeRule
    | InvoiceTotalRule
    | AdvanceSettlementRule
    | CorrectionRule
    | ArithmeticRule
    | RequiredDocumentsRule
    | DateOrderRule
    | SignaturesRule
    | SourceQualityRule,
    Field(discriminator="comparator"),
]


class RuleFile(_Frozen):
    """Root of one rule file; exported as packages/rules/schema/rule.schema.json."""

    rule: Rule


# --------------------------------------------------------------------------- case input
class FieldIn(_Frozen):
    name: FieldName
    # Normalized comparison form from extraction ("39350.00", "2026-06-05", "kosciuszki", "true").
    value: str | None = Field(default=None, max_length=500)
    raw_text: str = Field(default="", max_length=500)
    status: Literal["ok", "unreadable"] = "ok"
    confidence: float = Field(default=1.0, ge=0, le=1)

    @model_validator(mode="after")
    def _value_iff_ok(self) -> FieldIn:
        if (self.status == "ok") != (self.value is not None):
            raise ValueError("a readable field has a value, an unreadable one has none")
        return self


class DocumentIn(_Frozen):
    doc_id: str = Field(pattern=r"^[A-Za-z0-9-]{1,64}$")
    doc_type: DocType | None = None
    text_source: Literal["text_layer", "ocr", "none", "mixed"] = "text_layer"
    status: Literal["processed", "failed"] = "processed"
    fields: tuple[FieldIn, ...] = Field(default=(), max_length=200)

    @model_validator(mode="after")
    def _unique_fields(self) -> DocumentIn:
        names = [f.name for f in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("a field occurs twice in one document")
        return self


class CaseIn(_Frozen):
    case_id: str = Field(pattern=r"^[A-Za-z0-9-]{1,64}$")
    # Used to select rules when no application or contract date was read (e.g. case creation date).
    fallback_reference_date: date
    documents: tuple[DocumentIn, ...] = Field(max_length=50)

    @model_validator(mode="after")
    def _unique_documents(self) -> CaseIn:
        ids = [d.doc_id for d in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("a document occurs twice in the case")
        return self


# --------------------------------------------------------------------------- findings
class Evidence(_Frozen):
    doc_id: str
    field: str
    value: str | None
    text: str


class Finding(_Frozen):
    rule_id: str
    rule_version: int
    family: Family
    outcome: Outcome
    severity: Severity
    title_pl: str
    reason_pl: str
    # Documents the finding is about (where the deviation is); context documents are the reference.
    subject_doc_ids: tuple[str, ...]
    context_doc_ids: tuple[str, ...]
    fields: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    # Stable across re-evaluation and reprocessing: rule, outcome, subject documents, fields, key.
    fingerprint: str
    # Changes when the values behind the finding change (a past decision may need a second look).
    evidence_hash: str
    status: Literal["do_sprawdzenia"] = "do_sprawdzenia"


class RuleRef(_Frozen):
    id: str
    version: int


class Evaluation(_Frozen):
    case_id: str
    reference_date: date
    reference_source: ReferenceSource
    ruleset: tuple[RuleRef, ...]
    findings: tuple[Finding, ...]
