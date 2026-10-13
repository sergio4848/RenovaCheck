"""python -m renova_extract.eval {classification|extraction|rules|all} --data data/synth --out data/eval

Options: --ocr tesseract|none (default tesseract).

Exit code 1 when an acceptance threshold is missed: document type accuracy, field precision and
recall on clean PDFs, or any false positive/negative of the rules on ground-truth fields. Scans
and the rules on extracted fields (pipeline mode) are measured and reported without a threshold.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from renova_extract.classify.classifier import DocTypeClassifier
from renova_extract.core.config import Settings
from renova_extract.eval import classification, extraction
from renova_extract.eval import rules as rules_eval
from renova_extract.fields.dictionary import FieldDictionary
from renova_extract.ocr.base import OcrAdapter
from renova_extract.ocr.tesseract import TesseractPol
from renova_extract.rules.loader import load_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="renova_extract.eval")
    parser.add_argument("task", choices=["classification", "extraction", "rules", "all"])
    parser.add_argument("--data", type=Path, default=Path("data/synth"))
    parser.add_argument("--out", type=Path, default=Path("data/eval"))
    parser.add_argument("--ocr", choices=["tesseract", "none"], default="tesseract")
    parser.add_argument("--min-accuracy", type=float, default=0.95)
    parser.add_argument("--min-field-score", type=float, default=0.95, help="precision and recall on clean PDFs")
    args = parser.parse_args(argv)

    settings = Settings()
    ocr: OcrAdapter | None = TesseractPol() if args.ocr == "tesseract" else None
    if isinstance(ocr, TesseractPol) and not ocr.available():
        print("tesseract is not installed; use --ocr none", file=sys.stderr)  # noqa: T201
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    ok = True
    if args.task in ("classification", "all"):
        classifier = DocTypeClassifier.from_yaml(settings.rules_dir / "doc_types.yaml")
        report = classification.evaluate(args.data, classifier, ocr, settings.max_pages).as_dict()
        _write(args.out / "classification.json", report)
        print(_classification_text(report))  # noqa: T201
        ok &= report["accuracy"] is not None and report["accuracy"] >= args.min_accuracy
    if args.task in ("extraction", "all"):
        dictionary = FieldDictionary.from_yaml(settings.rules_dir / "fields.yaml")
        report = extraction.evaluate(args.data, dictionary, ocr, settings.max_pages).as_dict()
        _write(args.out / "extraction.json", report)
        print(_extraction_text(report))  # noqa: T201
        clean = report["overall"]["clean"]
        ok &= all(clean[k] is not None and clean[k] >= args.min_field_score for k in ("precision", "recall"))
    if args.task in ("rules", "all"):
        dictionary = FieldDictionary.from_yaml(settings.rules_dir / "fields.yaml")
        classifier = DocTypeClassifier.from_yaml(settings.rules_dir / "doc_types.yaml")
        rules = load_rules(settings.rules_dir)
        reports = {
            mode: rules_eval.evaluate(args.data, rules, dictionary, mode, classifier, ocr, settings.max_pages).as_dict()
            for mode in ("truth", "pipeline")
        }
        _write(args.out / "rules.json", reports)
        print(_rules_text(reports))  # noqa: T201
        truth = reports["truth"]["total"]
        ok &= truth["fp"] == 0 and truth["fn"] == 0
    return 0 if ok else 1


def _write(path: Path, report: dict[str, Any]) -> None:
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")


def _classification_text(report: dict[str, Any]) -> str:
    lines = [
        f"Document type classification ({report['total']} documents, OCR: {report['ocr']})",
        f"  accuracy: {report['accuracy']:.2%}  ({report['correct']}/{report['total']})",
    ]
    for quality, counts in report["by_quality"].items():
        if counts["total"]:
            lines.append(f"  {quality:<6} {counts['correct']}/{counts['total']}")
    for error in report["errors"]:
        lines.append(f"  miss {error['doc_id']}: expected {error['expected']}, got {error['predicted']}")
    return "\n".join(lines)


def _pct(value: float | None) -> str:
    return "   —  " if value is None else f"{value:6.1%}"


def _extraction_text(report: dict[str, Any]) -> str:
    docs = report["documents"]
    lines = [
        f"Field extraction (clean: {docs.get('clean', 0)} documents, scan: {docs.get('scan', 0)}, "
        f"OCR: {report['ocr']})",
        f"  {'field':<24} {'clean P':>8} {'clean R':>8} {'bbox':>7}   {'scan P':>8} {'scan R':>8} {'unread':>6}",
    ]
    rows = [*report["fields"].items(), ("ALL", report["overall"])]
    for name, per_quality in rows:
        clean, scan = per_quality.get("clean", {}), per_quality.get("scan", {})
        lines.append(
            f"  {name:<24} {_pct(clean.get('precision'))}   {_pct(clean.get('recall'))} "
            f"{_pct(clean.get('bbox_hit_rate'))}"
            f"   {_pct(scan.get('precision'))}   {_pct(scan.get('recall'))} {scan.get('unreadable', 0):>6}"
        )
    clean_errors = [e for e in report["errors"] if e["quality"] == "clean"]
    for error in clean_errors[:20]:
        lines.append(
            f"  clean {error['kind']:<15} {error['doc_id']} {error['field']}: {error['expected']!r} -> {error['got']!r}"
        )
    return "\n".join(lines)


def _rules_text(reports: dict[str, dict[str, Any]]) -> str:
    truth, pipeline = reports["truth"], reports["pipeline"]
    lines = [
        f"Rules ({truth['cases']} cases; truth = ground-truth fields, pipeline = extracted fields)",
        f"  {'rule':<8} {'truth TP':>8} {'FP':>4} {'FN':>4}   {'pipeline TP':>11} {'FP':>4} {'FN':>4}",
    ]
    for rule in sorted(set(truth["rules"]) | set(pipeline["rules"])):
        t, p = truth["rules"].get(rule, {}), pipeline["rules"].get(rule, {})
        lines.append(
            f"  {rule:<8} {t.get('tp', 0):>8} {t.get('fp', 0):>4} {t.get('fn', 0):>4}"
            f"   {p.get('tp', 0):>11} {p.get('fp', 0):>4} {p.get('fn', 0):>4}"
        )
    tt, pt = truth["total"], pipeline["total"]
    lines.append(f"  {'ALL':<8} {tt['tp']:>8} {tt['fp']:>4} {tt['fn']:>4}   {pt['tp']:>11} {pt['fp']:>4} {pt['fn']:>4}")
    for mode, report in reports.items():
        for error in report["errors"]:
            detail = error.get("reason") or f"{error['outcome']} in {error.get('doc_id')}"
            lines.append(f"  {mode} {error['kind']} {error['rule']} {error['case_id']}: {detail}")
        for mismatch in report["severity_mismatches"]:
            lines.append(f"  {mode} severity {mismatch}")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
