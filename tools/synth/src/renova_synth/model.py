"""Ground-truth model for one synthetic case.

Every value written into a document is recorded with the page and bounding box it was drawn
at, so extraction and provenance can be scored field by field. Bounding boxes are normalized to
the page ([0, 1], origin top-left, like page images). Models are frozen: a ground truth is built
once by the generator and only read afterwards.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"

Unit = Annotated[float, Field(ge=0.0, le=1.0)]
NormalizedValue = str | float | int | bool | None


class DocType(StrEnum):
    WNIOSEK_EKSTRAKT = "wniosek_ekstrakt"
    OFERTA = "oferta"
    UMOWA = "umowa"
    ANEKS = "aneks"
    FAKTURA = "faktura"
    FAKTURA_ZALICZKOWA = "faktura_zaliczkowa"
    FAKTURA_KORYGUJACA = "faktura_korygujaca"
    PROTOKOL_ODBIORU = "protokol_odbioru"
    KARTA_PRODUKTU = "karta_produktu"


class Quality(StrEnum):
    CLEAN = "clean"
    SCAN = "scan"


class ErrorType(StrEnum):
    ADDRESS_NUMBER_SWAP = "address_number_swap"
    STREET_SPELLING_VARIANT = "street_spelling_variant"
    MODEL_SWAP = "model_swap"
    POWER_MISMATCH = "power_mismatch"
    MISSING_PROTOCOL = "missing_protocol"
    NET_GROSS_CONFUSION = "net_gross_confusion"
    ADVANCE_PAYMENT = "advance_payment"
    CORRECTION_INVOICE = "correction_invoice"
    AGREED_CHANGE = "agreed_change"
    INVOICE_BEFORE_CONTRACT = "invoice_before_contract"
    MISSING_SIGNATURE = "missing_signature"
    LOW_QUALITY_SCAN = "low_quality_scan"


class Outcome(StrEnum):
    """What a correct reviewer concludes about an injected difference."""

    DISCREPANCY = "discrepancy"
    MATCH_AFTER_NORMALIZATION = "match_after_normalization"
    EXPLAINED_BY_ADVANCE = "explained_by_advance"
    EXPLAINED_BY_CORRECTION = "explained_by_correction"
    AGREED_CHANGE = "agreed_change"
    MISSING_DOCUMENT = "missing_document"
    UNREADABLE_SOURCE = "unreadable_source"


class RuleFamily(StrEnum):
    ADDRESS = "address"
    PRODUCT = "product"
    AMOUNT = "amount"
    COMPLETENESS = "completeness"
    NONE = "none"


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BBox(_Frozen):
    x0: Unit
    y0: Unit
    x1: Unit
    y1: Unit

    @model_validator(mode="after")
    def _ordered(self) -> BBox:
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bbox must have positive width and height")
        return self


class FieldTruth(_Frozen):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    text: str = Field(description="Exactly as printed in the document")
    value: NormalizedValue = Field(description="Canonical value used for comparison")
    page: int = Field(ge=1)
    bbox: BBox
    injected_error: str | None = Field(default=None, description="error_id when this value was altered")


class DocumentTruth(_Frozen):
    doc_id: str
    doc_type: DocType
    file: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pages: int = Field(ge=1)
    quality: Quality
    template: str
    issue_date: date
    fields: tuple[FieldTruth, ...]


class InjectedError(_Frozen):
    error_id: str
    type: ErrorType
    doc_id: str | None
    field: str | None
    true_value: NormalizedValue
    written_value: NormalizedValue
    description_pl: str


class ExpectedFinding(_Frozen):
    error_id: str
    family: RuleFamily
    outcome: Outcome
    severity: Severity
    fields: tuple[str, ...]
    doc_ids: tuple[str, ...]


class CaseFacts(_Frozen):
    """The true state of the project, before any error was injected."""

    investor_name: str
    address_street: str
    address_building_no: str
    address_postal_code: str
    address_city: str
    contractor_name: str
    contractor_nip: str
    product_manufacturer: str
    product_model: str
    product_power_kw: float
    amount_net: float
    amount_vat: float
    amount_gross: float
    application_date: date
    contract_date: date
    acceptance_date: date
    invoice_date: date


class CaseTruth(_Frozen):
    schema_version: Literal["1.0"] = "1.0"
    case_id: str = Field(pattern=r"^SYN-\d{4}-\d{3}$")
    seed: int
    program: Literal["czyste_powietrze"] = "czyste_powietrze"
    contract_kind: Literal["oferta", "umowa"]
    scenario: tuple[ErrorType, ...]
    facts: CaseFacts
    documents: tuple[DocumentTruth, ...]
    injected_errors: tuple[InjectedError, ...]
    expected_findings: tuple[ExpectedFinding, ...]

    @model_validator(mode="after")
    def _references_resolve(self) -> CaseTruth:
        doc_ids = {d.doc_id for d in self.documents}
        error_ids = {e.error_id for e in self.injected_errors}
        for err in self.injected_errors:
            if err.doc_id is not None and err.doc_id not in doc_ids:
                raise ValueError(f"{err.error_id}: unknown doc_id {err.doc_id}")
        for finding in self.expected_findings:
            if finding.error_id not in error_ids:
                raise ValueError(f"finding references unknown error {finding.error_id}")
            missing = set(finding.doc_ids) - doc_ids
            if missing:
                raise ValueError(f"finding {finding.error_id} references unknown docs {sorted(missing)}")
        return self
