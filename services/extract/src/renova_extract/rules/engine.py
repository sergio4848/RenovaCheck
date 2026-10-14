"""Deterministic rule engine: selects the rules valid on the case's reference date and runs them.

Every finding is born ``do_sprawdzenia``; the engine never decides a case. Fields are always
selected by document type and name (``contract_date`` on an annex is the annex date, not the
contract date), and values read with low confidence or marked unreadable never vote and are
never flagged: the source-quality rule reports them instead.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from renova_extract.fields.normalize import street_core
from renova_extract.rules.model import (
    AdvanceSettlementRule,
    AnnexChangeRule,
    ArithmeticRule,
    CaseIn,
    CorrectionRule,
    DateOrderRule,
    DocumentIn,
    Evaluation,
    Evidence,
    FieldIn,
    Finding,
    InvoiceTotalRule,
    MajorityRule,
    Outcome,
    ReferenceSource,
    RequiredDocumentsRule,
    Rule,
    RuleRef,
    SignaturesRule,
    SourceQualityRule,
    StreetSpellingRule,
)

DOC_LABELS = {
    "wniosek_ekstrakt": "wyciąg z wniosku",
    "oferta": "oferta",
    "umowa": "umowa",
    "aneks": "aneks",
    "faktura": "faktura VAT",
    "faktura_zaliczkowa": "faktura zaliczkowa",
    "faktura_korygujaca": "faktura korygująca",
    "protokol_odbioru": "protokół odbioru",
    "karta_produktu": "karta produktu",
}
FIELD_LABELS = {
    "address_street": "ulica",
    "address_building_no": "numer budynku",
    "address_postal_code": "kod pocztowy",
    "address_city": "miejscowość",
    "investor_name": "inwestor",
    "contractor_name": "wykonawca",
    "contractor_nip": "NIP wykonawcy",
    "product_manufacturer": "producent",
    "product_model": "model",
    "product_power_kw": "moc grzewcza",
    "invoice_date": "data wystawienia faktury",
    "contract_date": "data umowy/oferty",
    "acceptance_date": "data odbioru",
    "signature_investor": "podpis inwestora",
    "signature_contractor": "podpis wykonawcy",
}
# Before an annex: the application and the original contract; after it: everything else.
BEFORE_ANNEX = {"wniosek_ekstrakt", "oferta", "umowa"}
CONTRACT_TYPES = ("umowa", "oferta")
# Outcomes that explain a difference rather than report one are informational.
EXPLANATORY: set[Outcome] = {"match_after_normalization", "explained_by_advance", "explained_by_correction"}
SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _pln(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    whole, frac = f"{abs(value):.2f}".split(".")
    groups: list[str] = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return f"{sign}{' '.join(groups)},{frac} zł"


MAX_SHOWN_CHARS = 80
MAX_REASON_CHARS = 1900


def _shown(field: FieldIn) -> str:
    text = field.raw_text or field.value or ""
    return text if len(text) <= MAX_SHOWN_CHARS else text[: MAX_SHOWN_CHARS - 1] + "…"


def _label(doc: DocumentIn) -> str:
    return DOC_LABELS.get(doc.doc_type or "", "dokument bez typu")


def _labels(docs: Iterable[DocumentIn]) -> str:
    return ", ".join(_label(d) for d in docs)


def _ocr_note(doc: DocumentIn) -> str:
    return (
        " Wartość odczytana przez OCR ze skanu — porównaj z oryginałem." if doc.text_source in ("ocr", "mixed") else ""
    )


def _hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


@dataclass
class _Case:
    case: CaseIn

    def docs(self, types: Iterable[str]) -> list[DocumentIn]:
        wanted = set(types)
        return [d for d in self.case.documents if d.doc_type in wanted]

    def first(self, types: Sequence[str]) -> DocumentIn | None:
        for doc_type in types:
            found = self.docs([doc_type])
            if found:
                return found[0]
        return None

    @staticmethod
    def field(doc: DocumentIn | None, name: str, min_confidence: float = 0.0) -> FieldIn | None:
        if doc is None:
            return None
        for f in doc.fields:
            if f.name == name and f.status == "ok" and f.confidence >= min_confidence:
                return f
        return None

    @classmethod
    def amount(cls, doc: DocumentIn | None, name: str, min_confidence: float) -> Decimal | None:
        f = cls.field(doc, name, min_confidence)
        if f is None or f.value is None:
            return None
        try:
            return Decimal(f.value)
        except InvalidOperation:
            return None

    @classmethod
    def day(cls, doc: DocumentIn | None, name: str, min_confidence: float) -> date | None:
        f = cls.field(doc, name, min_confidence)
        try:
            return date.fromisoformat(f.value) if f is not None and f.value else None
        except ValueError:
            return None


class _Builder:
    """Builds findings of one rule with consistent evidence, fingerprints and severity."""

    def __init__(self, rule: Rule, case: _Case) -> None:
        self.rule = rule
        self.case = case
        self.findings: list[Finding] = []

    def add(
        self,
        outcome: Outcome,
        reason: str,
        subjects: Sequence[DocumentIn],
        context: Sequence[DocumentIn] = (),
        fields: Sequence[str] = (),
        key: str = "",
    ) -> None:
        subject_ids = tuple(sorted(d.doc_id for d in subjects))
        context_ids = tuple(sorted(d.doc_id for d in context if d.doc_id not in subject_ids))
        evidence = tuple(
            Evidence(doc_id=d.doc_id, field=name, value=f.value, text=_shown(f))
            for d in (*subjects, *context)
            for name in fields
            if (f := _Case.field(d, name)) is not None
        )
        self.findings.append(
            Finding(
                rule_id=self.rule.id,
                rule_version=self.rule.version,
                family=self.rule.family,
                outcome=outcome,
                severity="info" if outcome in EXPLANATORY else self.rule.severity,
                title_pl=self.rule.title_pl,
                reason_pl=reason if len(reason) <= MAX_REASON_CHARS else reason[: MAX_REASON_CHARS - 1] + "…",
                subject_doc_ids=subject_ids,
                context_doc_ids=context_ids,
                fields=tuple(fields),
                evidence=evidence,
                fingerprint=_hash([self.rule.id, outcome, list(subject_ids), sorted(fields), key]),
                evidence_hash=_hash(sorted((e.doc_id, e.field, e.value) for e in evidence)),
                source_url=str(self.rule.source_url),
            )
        )


# --------------------------------------------------------------------------- comparators
def _majority(rule: MajorityRule, case: _Case, out: _Builder) -> None:
    docs = case.docs(rule.inputs.doc_types)
    min_conf = rule.threshold.min_confidence
    annex_changes = rule.threshold.split_on_annex and any(
        case.field(d, f, min_conf) for d in case.docs(["aneks"]) for f in rule.inputs.fields
    )
    groups = (
        [[d for d in docs if d.doc_type in BEFORE_ANNEX], [d for d in docs if d.doc_type not in BEFORE_ANNEX]]
        if annex_changes
        else [docs]
    )
    for group in groups:
        for name in rule.inputs.fields:
            votes = [(d, f) for d in group if (f := case.field(d, name, min_conf)) is not None]
            counts = Counter(f.value for _, f in votes)
            if len(counts) < 2:
                continue
            label = FIELD_LABELS.get(name, name)
            top, top_count = counts.most_common(1)[0]
            if top_count * 2 > len(votes):
                agree = [d for d, f in votes if f.value == top]
                shown = _shown(next(f for _, f in votes if f.value == top))
                for doc, f in votes:
                    if f.value != top:
                        reason = (
                            f"{label.capitalize()} „{_shown(f)}” w dokumencie {_label(doc)} różni się od wartości "
                            f"„{shown}” w pozostałych dokumentach ({_labels(agree)}).{_ocr_note(doc)}"
                        )
                        out.add("discrepancy", reason, [doc], agree, [name])
            else:
                listed = "; ".join(f"{_label(d)}: „{_shown(f)}”" for d, f in votes)
                reason = f"{label.capitalize()} różni się między dokumentami i żadna wartość nie przeważa ({listed})."
                out.add("discrepancy", reason, [d for d, _ in votes], [], [name], key="no_majority")


def _street_spelling(rule: StreetSpellingRule, case: _Case, out: _Builder) -> None:
    min_conf = rule.threshold.min_confidence
    reference = case.first(["wniosek_ekstrakt"])
    ref_field = case.field(reference, "address_street", min_conf)
    if reference is None or ref_field is None or not ref_field.raw_text:
        return
    ref_core = street_core(ref_field.raw_text)
    for doc in case.docs(rule.inputs.doc_types):
        if doc is reference:
            continue
        f = case.field(doc, "address_street", min_conf)
        if f is None or not f.raw_text or f.value != ref_field.value:
            continue
        if street_core(f.raw_text) != ref_core:
            reason = (
                f"Ulica zapisana jako „{f.raw_text}” ({_label(doc)}), we wniosku „{ref_field.raw_text}”. "
                "Po normalizacji to ta sama ulica."
            )
            out.add("match_after_normalization", reason, [doc], [reference], ["address_street"])


def _annex_change(rule: AnnexChangeRule, case: _Case, out: _Builder) -> None:
    min_conf = rule.threshold.min_confidence
    contract = case.first(CONTRACT_TYPES)
    if contract is None:
        return
    for annex in case.docs(["aneks"]):
        changed = []
        for name in rule.inputs.fields:
            before, after = case.field(contract, name, min_conf), case.field(annex, name, min_conf)
            if before is not None and after is not None and before.value != after.value:
                changed.append((name, before, after))
        if changed:
            parts = "; ".join(f"{FIELD_LABELS.get(n, n)}: „{_shown(b)}” → „{_shown(a)}”" for n, b, a in changed)
            reason = f"Aneks zmienia ustalenia umowy ({parts}). Do sprawdzenia, czy zmiana jest uzgodniona."
            context = [contract, *case.docs(["faktura"])]
            out.add("agreed_change", reason, [annex], context, [n for n, _, _ in changed])


def _reference_contract(case: _Case, min_conf: float) -> DocumentIn | None:
    for annex in case.docs(["aneks"]):
        if case.amount(annex, "amount_gross", min_conf) is not None:
            return annex
    return case.first(CONTRACT_TYPES)


def _invoice_total(rule: InvoiceTotalRule, case: _Case, out: _Builder) -> None:
    min_conf, tol = rule.threshold.min_confidence, Decimal(str(rule.threshold.tolerance_pln))
    reference = _reference_contract(case, min_conf)
    ref_gross = case.amount(reference, "amount_gross", min_conf)
    if reference is None or ref_gross is None:
        return
    for invoice in case.docs(["faktura"]):
        gross = case.amount(invoice, "amount_gross", min_conf)
        if gross is None or abs(gross - ref_gross) <= tol:
            continue
        net = case.amount(invoice, "amount_net", min_conf)
        if net is not None and abs(net - ref_gross) <= tol:
            reason = (
                f"Kwota netto faktury ({_pln(net)}) jest równa kwocie brutto z dokumentu {_label(reference)} "
                f"({_pln(ref_gross)}); faktura brutto wynosi {_pln(gross)}. Możliwe pomylenie netto z brutto."
            )
            out.add("discrepancy", reason, [invoice], [reference], ["amount_net", "amount_gross"])
        else:
            reason = (
                f"Kwota brutto faktury ({_pln(gross)}) różni się od kwoty z dokumentu {_label(reference)} "
                f"({_pln(ref_gross)}) o {_pln(gross - ref_gross)}."
            )
            out.add("discrepancy", reason, [invoice], [reference], ["amount_gross"])


def _advance_settlement(rule: AdvanceSettlementRule, case: _Case, out: _Builder) -> None:
    min_conf, tol = rule.threshold.min_confidence, Decimal(str(rule.threshold.tolerance_pln))
    advances = case.docs(["faktura_zaliczkowa"])
    advance_total = sum(
        (a for d in advances if (a := case.amount(d, "amount_gross", min_conf)) is not None), Decimal(0)
    )
    for invoice in case.docs(["faktura"]):
        settled = case.amount(invoice, "advance_amount", min_conf)
        gross = case.amount(invoice, "amount_gross", min_conf)
        due = case.amount(invoice, "amount_due", min_conf)
        if settled is None:
            if advances and gross is not None:
                reason = (
                    f"W sprawie jest faktura zaliczkowa ({_pln(advance_total)} brutto), ale faktura końcowa nie "
                    "rozlicza zaliczki."
                )
                out.add("discrepancy", reason, [invoice], advances, ["advance_amount"])
            continue
        problems = []
        if not advances:
            problems.append("brak faktury zaliczkowej w sprawie")
        elif abs(settled - advance_total) > tol:
            problems.append(f"zaliczka {_pln(settled)} różni się od faktur zaliczkowych ({_pln(advance_total)})")
        if gross is not None and due is not None and abs(due - (gross - settled)) > tol:
            problems.append(f"do zapłaty {_pln(due)} zamiast {_pln(gross - settled)}")
        if problems:
            reason = "Rozliczenie zaliczki się nie zgadza: " + "; ".join(problems) + "."
            out.add("discrepancy", reason, [invoice], advances, ["advance_amount", "amount_due"])
        else:
            reason = (
                f"Faktura końcowa rozlicza zaliczkę {_pln(settled)} z faktury zaliczkowej; "
                f"do zapłaty {_pln(due) if due is not None else '—'} przy kwocie brutto "
                f"{_pln(gross) if gross is not None else '—'}."
            )
            out.add("explained_by_advance", reason, [invoice], advances, ["amount_due", "advance_amount"])


def _correction(rule: CorrectionRule, case: _Case, out: _Builder) -> None:
    min_conf = rule.threshold.min_confidence
    invoices = case.docs(["faktura"])
    reference = _reference_contract(case, min_conf)
    for corr in case.docs(["faktura_korygujaca"]):
        related = case.field(corr, "related_document_number", min_conf)
        target = next(
            (
                i
                for i in invoices
                if related is not None and (n := case.field(i, "document_number")) and n.value == related.value
            ),
            None,
        )
        if related is not None and target is None:
            reason = f"Faktura korygująca dotyczy faktury „{_shown(related)}”, której nie ma w sprawie."
            out.add("discrepancy", reason, [corr], invoices, ["related_document_number"])
            continue
        target = target or (invoices[0] if invoices else None)
        correction = case.amount(corr, "amount_gross", min_conf)
        gross = case.amount(target, "amount_gross", min_conf)
        if target is None or correction is None or gross is None:
            continue
        corrected = gross + correction
        ref_gross = case.amount(reference, "amount_gross", min_conf)
        tail = f"; {_label(reference)}: {_pln(ref_gross)}" if reference is not None and ref_gross is not None else ""
        reason = (
            f"Faktura korygująca zmienia kwotę brutto o {_pln(correction)}: po korekcie {_pln(corrected)} "
            f"(faktura {_pln(gross)}{tail})."
        )
        context = [target, *([reference] if reference is not None else [])]
        out.add("explained_by_correction", reason, [corr], context, ["amount_gross"])


def _net_vat_gross(rule: ArithmeticRule, case: _Case, out: _Builder) -> None:
    min_conf, tol = rule.threshold.min_confidence, Decimal(str(rule.threshold.tolerance_pln))
    for doc in case.docs(rule.inputs.doc_types):
        net, vat, gross = (case.amount(doc, n, min_conf) for n in ("amount_net", "amount_vat", "amount_gross"))
        if net is None or vat is None or gross is None or abs(net + vat - gross) <= tol:
            continue
        reason = f"Netto {_pln(net)} + VAT {_pln(vat)} = {_pln(net + vat)}, a dokument podaje brutto {_pln(gross)}."
        out.add("discrepancy", reason, [doc], [], ["amount_net", "amount_vat", "amount_gross"])


def _required_documents(rule: RequiredDocumentsRule, case: _Case, out: _Builder) -> None:
    present = {d.doc_type for d in case.case.documents}
    for group in rule.threshold.required:
        if not present & set(group):
            names = " lub ".join(DOC_LABELS[t] for t in group)
            out.add("missing_document", f"Brak dokumentu: {names}.", [], [], [], key="|".join(group))


def _date_order(rule: DateOrderRule, case: _Case, out: _Builder) -> None:
    t = rule.threshold
    earlier_docs = [
        (d, day) for d in case.docs(t.earlier.doc_types) if (day := case.day(d, t.earlier.field, t.min_confidence))
    ]
    if not earlier_docs:
        return
    earlier_doc, earlier_day = min(earlier_docs, key=lambda pair: pair[1])
    for doc in case.docs(t.later.doc_types):
        later_day = case.day(doc, t.later.field, t.min_confidence)
        if later_day is None or (later_day - earlier_day).days >= t.min_days:
            continue
        reason = (
            f"{FIELD_LABELS.get(t.later.field, t.later.field).capitalize()} ({later_day:%d.%m.%Y}, {_label(doc)}) "
            f"jest wcześniejsza niż {FIELD_LABELS.get(t.earlier.field, t.earlier.field)} "
            f"({earlier_day:%d.%m.%Y}, {_label(earlier_doc)})."
        )
        out.add("discrepancy", reason, [doc], [earlier_doc], [t.later.field, t.earlier.field])


def _signatures(rule: SignaturesRule, case: _Case, out: _Builder) -> None:
    min_conf = rule.threshold.min_confidence
    for requirement in rule.threshold.required:
        for doc in case.docs([requirement.doc_type]):
            for name in requirement.fields:
                f = case.field(doc, name, min_conf)
                if f is not None and f.value == "false":
                    reason = f"Brak: {FIELD_LABELS.get(name, name)} na dokumencie {_label(doc)}."
                    out.add("discrepancy", reason, [doc], [], [name])


def _source_quality(rule: SourceQualityRule, case: _Case, out: _Builder) -> None:
    min_conf = rule.threshold.min_confidence
    for doc in case.case.documents:
        reasons = []
        if doc.status == "failed":
            reasons.append("dokumentu nie udało się przeanalizować")
        elif doc.text_source in ("ocr", "mixed"):
            reasons.append("tekst odczytano przez OCR ze skanu")
        elif doc.text_source == "none":
            reasons.append("dokument nie zawiera tekstu do odczytu")
        weak = sorted(f.name for f in doc.fields if f.status == "unreadable" or f.confidence < min_conf)
        if weak:
            reasons.append("nieczytelne lub niepewne pola: " + ", ".join(FIELD_LABELS.get(n, n) for n in weak))
        if reasons:
            reason = f"{_label(doc).capitalize()}: " + "; ".join(reasons) + ". Wartości sprawdzić z oryginałem."
            out.add("unreadable_source", reason, [doc], [], weak)


COMPARATORS: dict[str, Callable[[Any, _Case, _Builder], None]] = {
    "majority": _majority,
    "street_spelling": _street_spelling,
    "annex_change": _annex_change,
    "invoice_total": _invoice_total,
    "advance_settlement": _advance_settlement,
    "correction": _correction,
    "net_vat_gross": _net_vat_gross,
    "required_documents": _required_documents,
    "date_order": _date_order,
    "signatures": _signatures,
    "source_quality": _source_quality,
}


# --------------------------------------------------------------------------- engine
class RuleEngine:
    def __init__(self, rules: Sequence[Rule]) -> None:
        self.rules = list(rules)

    def select(self, day: date) -> list[Rule]:
        """The highest version of each rule valid on ``day``."""
        chosen: dict[str, Rule] = {}
        for rule in self.rules:
            if rule.valid_on(day) and (rule.id not in chosen or rule.version > chosen[rule.id].version):
                chosen[rule.id] = rule
        return [chosen[k] for k in sorted(chosen)]

    @staticmethod
    def reference_date(case: CaseIn) -> tuple[date, ReferenceSource]:
        view = _Case(case)
        application = view.day(view.first(["wniosek_ekstrakt"]), "application_date", 0.0)
        if application is not None:
            return application, "application_date"
        contract = view.day(view.first(CONTRACT_TYPES), "contract_date", 0.0)
        if contract is not None:
            return contract, "contract_date"
        return case.fallback_reference_date, "fallback"

    def evaluate(self, case: CaseIn) -> Evaluation:
        # Canonical document order (type, then id): the result never depends on upload order.
        order = {t: i for i, t in enumerate(DOC_LABELS)}
        documents = sorted(case.documents, key=lambda d: (order.get(d.doc_type or "", len(order)), d.doc_id))
        case = case.model_copy(update={"documents": tuple(documents)})
        day, source = self.reference_date(case)
        selected = self.select(day)
        view = _Case(case)
        findings: list[Finding] = []
        for rule in selected:
            builder = _Builder(rule, view)
            COMPARATORS[rule.comparator](rule, view, builder)
            findings.extend(builder.findings)
        if not selected:
            findings.append(_no_rules(day))
        unique = {f.fingerprint: f for f in reversed(findings)}
        ordered = sorted(unique.values(), key=lambda f: (SEVERITY_ORDER[f.severity], f.rule_id, f.subject_doc_ids))
        return Evaluation(
            case_id=case.case_id,
            reference_date=day,
            reference_source=source,
            ruleset=tuple(RuleRef(id=r.id, version=r.version) for r in selected),
            findings=tuple(ordered),
        )


def _no_rules(day: date) -> Finding:
    reason = f"Brak reguł obowiązujących w dniu {day:%d.%m.%Y}; sprawa wymaga ręcznej weryfikacji."
    return Finding(
        rule_id="SYS-00",
        rule_version=0,
        family="quality",
        outcome="no_rules",
        severity="warning",
        title_pl="Brak obowiązujących reguł",
        reason_pl=reason,
        subject_doc_ids=(),
        context_doc_ids=(),
        fields=(),
        evidence=(),
        fingerprint=_hash(["SYS-00", "no_rules"]),
        evidence_hash=_hash([day.isoformat()]),
    )
