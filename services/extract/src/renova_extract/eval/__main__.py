"""python -m renova_extract.eval classification --data data/synth --out data/eval [--ocr tesseract|none]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from renova_extract.classify.classifier import DocTypeClassifier
from renova_extract.core.config import Settings
from renova_extract.eval.classification import evaluate
from renova_extract.ocr.tesseract import TesseractPol


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="renova_extract.eval")
    parser.add_argument("task", choices=["classification"])
    parser.add_argument("--data", type=Path, default=Path("data/synth"))
    parser.add_argument("--out", type=Path, default=Path("data/eval"))
    parser.add_argument("--ocr", choices=["tesseract", "none"], default="tesseract")
    parser.add_argument("--min-accuracy", type=float, default=0.95)
    args = parser.parse_args(argv)

    settings = Settings()
    classifier = DocTypeClassifier.from_yaml(settings.rules_dir / "doc_types.yaml")
    ocr = TesseractPol() if args.ocr == "tesseract" else None
    if ocr is not None and not ocr.available():
        print("tesseract is not installed; use --ocr none", file=sys.stderr)  # noqa: T201
        return 2
    report = evaluate(args.data, classifier, ocr, settings.max_pages).as_dict()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "classification.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    lines = [
        f"Document type classification ({report['total']} documents, OCR: {report['ocr']})",
        f"  accuracy: {report['accuracy']:.2%}  ({report['correct']}/{report['total']})",
    ]
    for quality, counts in report["by_quality"].items():
        if counts["total"]:
            lines.append(f"  {quality:<6} {counts['correct']}/{counts['total']}")
    for error in report["errors"]:
        lines.append(f"  miss {error['doc_id']}: expected {error['expected']}, got {error['predicted']}")
    print("\n".join(lines))  # noqa: T201
    return 0 if report["accuracy"] is not None and report["accuracy"] >= args.min_accuracy else 1


if __name__ == "__main__":
    sys.exit(main())
