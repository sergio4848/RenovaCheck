"""Rule evaluation against the expected findings of the synthetic ground truth.

Two modes:

* ``truth``: the rules read the ground-truth fields (normalized like extraction output), so the
  numbers measure the rules alone.
* ``pipeline``: the rules read what classification and extraction produced from the PDFs, so the
  numbers measure the whole chain.

An engine finding matches an expected finding when the family (ground truth ``none`` = rule
family ``quality``) and outcome agree, their fields overlap (or the expected one lists none), and
the document the error was injected into is one of the finding's subject documents (when the error
has a document). Matching is one-to-one. Unmatched findings are false positives of their rule;
unmatched expected findings are false negatives of the rule that declares that outcome and those
fields in ``emits``.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from renova_extract.classify.classifier import DocTypeClassifier
from renova_extract.documents.loader import load_document
from renova_extract.documents.models import TextSource
from renova_extract.fields.dictionary import FieldDictionary
from renova_extract.fields.extractors import FieldExtractor
from renova_extract.fields.normalize import normalize
from renova_extract.ocr.base import OcrAdapter
from renova_extract.rules.engine import RuleEngine
from renova_extract.rules.model import CaseIn, DocumentIn, FieldIn, Finding, Rule

FAMILY = {"none": "quality"}
UNASSIGNED = "(none)"


@dataclass
class RuleCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def as_dict(self) -> dict[str, int]:
        return {"tp": self.tp, "fp": self.fp, "fn": self.fn}


@dataclass
class RulesReport:
    mode: str
    counts: dict[str, RuleCounts] = field(default_factory=lambda: defaultdict(RuleCounts))
    errors: list[dict[str, Any]] = field(default_factory=list)
    severity_mismatches: list[dict[str, Any]] = field(default_factory=list)
    cases: int = 0
    seconds: float = 0.0

    @property
    def total(self) -> RuleCounts:
        total = RuleCounts()
        for c in self.counts.values():
            total.tp, total.fp, total.fn = total.tp + c.tp, total.fp + c.fp, total.fn + c.fn
        return total

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "cases": self.cases,
            "total": self.total.as_dict(),
            "rules": {k: v.as_dict() for k, v in sorted(self.counts.items())},
            "severity_mismatches": self.severity_mismatches,
            "errors": self.errors,
            "seconds": round(self.seconds, 1),
        }


def attribute(rules: list[Rule], family: str, outcome: str, fields: tuple[str, ...]) -> str:
    """The rule that should have reported this expected finding: same family and outcome, whose
    declared fields cover the expected ones most narrowly."""
    candidates = [
        (len(emit.fields), rule.id)
        for rule in rules
        if rule.family == FAMILY.get(family, family)
        for emit in rule.emits
        if emit.outcome == outcome and set(fields) <= set(emit.fields)
    ]
    return min(candidates)[1] if candidates else UNASSIGNED


def score_case(report: RulesReport, rules: list[Rule], truth: dict[str, Any], findings: tuple[Finding, ...]) -> None:
    errors = {e["error_id"]: e for e in truth["injected_errors"]}
    unused = list(findings)
    report.cases += 1
    for expected in sorted(truth["expected_findings"], key=lambda e: e["error_id"]):
        target = errors[expected["error_id"]]["doc_id"]
        family = FAMILY.get(expected["family"], expected["family"])
        match = next(
            (
                f
                for f in unused
                if f.family == family
                and f.outcome == expected["outcome"]
                and (not expected["fields"] or set(expected["fields"]) & set(f.fields))
                and (target is None or target in f.subject_doc_ids)
            ),
            None,
        )
        if match is None:
            rule_id = attribute(rules, expected["family"], expected["outcome"], tuple(expected["fields"]))
            report.counts[rule_id].fn += 1
            report.errors.append(
                {
                    "case_id": truth["case_id"],
                    "kind": "fn",
                    "rule": rule_id,
                    "error_id": expected["error_id"],
                    "outcome": expected["outcome"],
                    "doc_id": target,
                }
            )
            continue
        unused.remove(match)
        report.counts[match.rule_id].tp += 1
        if match.severity != expected["severity"]:
            report.severity_mismatches.append(
                {
                    "case_id": truth["case_id"],
                    "rule": match.rule_id,
                    "expected": expected["severity"],
                    "got": match.severity,
                }
            )
    for finding in unused:
        report.counts[finding.rule_id].fp += 1
        report.errors.append(
            {
                "case_id": truth["case_id"],
                "kind": "fp",
                "rule": finding.rule_id,
                "outcome": finding.outcome,
                "docs": list(finding.subject_doc_ids),
                "reason": finding.reason_pl,
            }
        )


def _stored(value: str | float | bool | None) -> str | None:
    if isinstance(value, bool):
        return "true" if value else "false"
    return None if value is None else str(value)


def truth_case(truth: dict[str, Any], dictionary: FieldDictionary) -> CaseIn:
    documents = []
    for doc in truth["documents"]:
        fields: dict[str, FieldIn] = {}
        for item in doc["fields"]:
            if item["name"] in fields:
                continue  # printed twice (the protocol repeats the address); the first one is read
            value = _stored(normalize(dictionary.get(item["name"]).type, item["value"]))
            fields[item["name"]] = FieldIn(
                name=item["name"],
                value=value,
                raw_text=item["text"],
                status="ok" if value is not None else "unreadable",
            )
        documents.append(
            DocumentIn(
                doc_id=doc["doc_id"],
                doc_type=doc["doc_type"],
                text_source="ocr" if doc["quality"] == "scan" else "text_layer",
                fields=tuple(fields.values()),
            )
        )
    return CaseIn(case_id=truth["case_id"], fallback_reference_date=date(2026, 1, 1), documents=tuple(documents))


def pipeline_case(
    truth: dict[str, Any],
    root: Path,
    classifier: DocTypeClassifier,
    extractor: FieldExtractor,
    ocr: OcrAdapter | None,
    max_pages: int,
) -> CaseIn:
    documents = []
    for doc in truth["documents"]:
        loaded = load_document((root / doc["file"]).read_bytes(), max_pages, ocr)
        doc_type = classifier.classify(loaded.text).doc_type
        sources = {p.source for p in loaded.pages}
        text_source = (
            "mixed"
            if len(sources) > 1
            else {TextSource.OCR: "ocr", TextSource.NONE: "none"}.get(sources.pop(), "text_layer")
        )
        fields = tuple(
            FieldIn(
                name=f.name,
                value=_stored(f.value),
                raw_text=f.text[:500],
                status=f.status,
                confidence=round(f.confidence, 3),
            )
            for f in extractor.extract(loaded.pages, doc_type)
        )
        documents.append(DocumentIn(doc_id=doc["doc_id"], doc_type=doc_type, text_source=text_source, fields=fields))
    return CaseIn(case_id=truth["case_id"], fallback_reference_date=date(2026, 1, 1), documents=tuple(documents))


def evaluate(
    dataset: Path,
    rules: list[Rule],
    dictionary: FieldDictionary,
    mode: str,
    classifier: DocTypeClassifier | None = None,
    ocr: OcrAdapter | None = None,
    max_pages: int = 50,
) -> RulesReport:
    engine = RuleEngine(rules)
    extractor = FieldExtractor(dictionary)
    report = RulesReport(mode=mode)
    for rule in engine.select(date.max):
        report.counts[rule.id]  # list every rule, also those with nothing to find in this dataset
    for rule in rules:
        report.counts.setdefault(rule.id, RuleCounts())
    started = time.perf_counter()
    for truth_file in sorted(dataset.glob("SYN-*/ground_truth.json")):
        truth = json.loads(truth_file.read_text())
        if mode == "truth":
            case = truth_case(truth, dictionary)
        else:
            if classifier is None:
                raise ValueError("pipeline mode needs a classifier")
            case = pipeline_case(truth, truth_file.parent, classifier, extractor, ocr, max_pages)
        score_case(report, rules, truth, engine.evaluate(case).findings)
    report.seconds = time.perf_counter() - started
    return report
