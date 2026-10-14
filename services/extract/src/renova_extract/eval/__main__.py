"""python -m renova_extract.eval TASK --data data/synth --out data/eval

TASK: classification | extraction | rules | all | ocr-bench | report.

Options: --ocr tesseract|none (default tesseract); --report PATH writes the Markdown report
(docs/EVAL_REPORT.md) from everything in --out after the task; ``ocr-bench`` runs the OCR benchmark
on --bench-data (--pages pages); ``report`` only re-renders the report.

Exit code 1 when an acceptance threshold is missed: document type accuracy, field precision and
recall on clean PDFs, or any false positive/negative of the rules on ground-truth fields. Scans
and the rules on extracted fields (pipeline mode) are measured and reported without a threshold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from renova_extract.classify.classifier import DocTypeClassifier
from renova_extract.core.config import Settings
from renova_extract.eval import classification, extraction, ocr_bench
from renova_extract.eval import report as markdown
from renova_extract.eval import rules as rules_eval
from renova_extract.fields.dictionary import FieldDictionary
from renova_extract.ocr.base import OcrAdapter
from renova_extract.ocr.tesseract import TesseractPol
from renova_extract.rules.loader import load_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="renova_extract.eval")
    parser.add_argument("task", choices=["classification", "extraction", "rules", "all", "ocr-bench", "report"])
    parser.add_argument("--data", type=Path, default=Path("data/synth"))
    parser.add_argument("--out", type=Path, default=Path("data/eval"))
    parser.add_argument("--ocr", choices=["tesseract", "none"], default="tesseract")
    parser.add_argument("--min-accuracy", type=float, default=0.95)
    parser.add_argument("--min-field-score", type=float, default=0.95, help="precision and recall on clean PDFs")
    parser.add_argument("--report", type=Path, help="write the Markdown report here")
    parser.add_argument("--bench-data", type=Path, default=Path("data/ocr_bench/synth"))
    parser.add_argument("--pages", type=int, default=200, help="OCR benchmark page budget")
    args = parser.parse_args(argv)

    settings = Settings()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.task == "report":
        return _write_report(args)
    if args.task == "ocr-bench":
        dictionary = FieldDictionary.from_yaml(settings.rules_dir / "fields.yaml")
        adapters = ocr_bench.providers_from(settings)
        started = time.perf_counter()
        result = ocr_bench.benchmark(args.bench_data, args.pages, adapters, dictionary, _progress)
        result["seconds"] = round(time.perf_counter() - started, 1)
        _write(args.out / "ocr_bench.json", result)
        for name, provider in result["providers"].items():
            print(f"OCR {name}: {provider['status']}")  # noqa: T201
        return _write_report(args)
    ocr: OcrAdapter | None = TesseractPol() if args.ocr == "tesseract" else None
    if isinstance(ocr, TesseractPol) and not ocr.available():
        print("tesseract is not installed; use --ocr none", file=sys.stderr)  # noqa: T201
        return 2
    summary = _load_summary(args.out)
    checks: dict[str, dict[str, Any]] = {c["name"]: c for c in summary.get("checks", [])}
    ok = True
    if args.task in ("classification", "all"):
        classifier = DocTypeClassifier.from_yaml(settings.rules_dir / "doc_types.yaml")
        started = time.perf_counter()
        result = classification.evaluate(args.data, classifier, ocr, settings.max_pages).as_dict()
        summary["task_seconds"]["classification"] = round(time.perf_counter() - started, 1)
        _write(args.out / "classification.json", result)
        print(_classification_text(result))  # noqa: T201
        passed = result["accuracy"] is not None and result["accuracy"] >= args.min_accuracy
        checks["document type accuracy"] = _check(
            "document type accuracy", f"≥ {args.min_accuracy:.0%}", _fmt_pct(result["accuracy"]), passed
        )
        ok &= passed
    if args.task in ("extraction", "all"):
        dictionary = FieldDictionary.from_yaml(settings.rules_dir / "fields.yaml")
        started = time.perf_counter()
        result = extraction.evaluate(args.data, dictionary, ocr, settings.max_pages).as_dict()
        summary["task_seconds"]["extraction"] = round(time.perf_counter() - started, 1)
        _write(args.out / "extraction.json", result)
        print(_extraction_text(result))  # noqa: T201
        clean = result["overall"]["clean"]
        for key in ("precision", "recall"):
            passed = clean[key] is not None and clean[key] >= args.min_field_score
            name = f"field {key} (clean PDFs)"
            checks[name] = _check(name, f"≥ {args.min_field_score:.0%}", _fmt_pct(clean[key]), passed)
            ok &= passed
    if args.task in ("rules", "all"):
        dictionary = FieldDictionary.from_yaml(settings.rules_dir / "fields.yaml")
        classifier = DocTypeClassifier.from_yaml(settings.rules_dir / "doc_types.yaml")
        rules = load_rules(settings.rules_dir)
        started = time.perf_counter()
        reports = {
            mode: rules_eval.evaluate(args.data, rules, dictionary, mode, classifier, ocr, settings.max_pages).as_dict()
            for mode in ("truth", "pipeline")
        }
        summary["task_seconds"]["rules (truth + pipeline)"] = round(time.perf_counter() - started, 1)
        _write(args.out / "rules.json", reports)
        print(_rules_text(reports))  # noqa: T201
        truth = reports["truth"]["total"]
        passed = truth["fp"] == 0 and truth["fn"] == 0
        name = "rule FP / FN on ground-truth fields"
        checks[name] = _check(name, "0 / 0", f"{truth['fp']} / {truth['fn']}", passed)
        ok &= passed
    summary.update(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        ocr=ocr.name if ocr else "none",
        dataset=_dataset(args.data, settings.rules_dir),
        checks=list(checks.values()),
    )
    _write(args.out / "summary.json", summary)
    if args.report:
        _write_report(args)
    return 0 if ok else 1


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)  # noqa: T201


def _write_report(args: argparse.Namespace) -> int:
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown.render(args.out))
        print(f"report written to {args.report}")  # noqa: T201
    return 0


def _load_summary(out: Path) -> dict[str, Any]:
    path = out / "summary.json"
    summary: dict[str, Any] = json.loads(path.read_text()) if path.exists() else {}
    summary.setdefault("task_seconds", {})
    return summary


def _check(name: str, target: str, value: str, ok: bool) -> dict[str, Any]:
    return {"name": name, "target": target, "value": value, "ok": ok}


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def _dataset(data: Path, rules_dir: Path) -> dict[str, Any]:
    documents: Counter[str] = Counter()
    pages: Counter[str] = Counter()
    cases = injected = expected = 0
    seeds = set()
    for truth_file in sorted(data.glob("SYN-*/ground_truth.json")):
        truth = json.loads(truth_file.read_text())
        cases += 1
        seeds.add(truth["seed"])
        injected += len(truth["injected_errors"])
        expected += len(truth["expected_findings"])
        for doc in truth["documents"]:
            documents[doc["quality"]] += 1
            pages[doc["quality"]] += doc["pages"]
    lock = (rules_dir / "rules.lock.json").read_bytes()
    fields_version = FieldDictionary.from_yaml(rules_dir / "fields.yaml").version
    return {
        "cases": cases,
        "seeds": sorted(seeds),
        "documents": dict(documents),
        "pages": dict(pages),
        "injected_errors": injected,
        "expected_findings": expected,
        "ruleset": len(json.loads(lock)),
        "ruleset_digest": hashlib.sha256(lock).hexdigest(),
        "fields_version": fields_version,
    }


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
