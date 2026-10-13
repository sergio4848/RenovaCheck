"""renova-synth command line: generate | validate | schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from renova_synth.generate import generate
from renova_synth.validate import SCHEMA_PATH, schema, validate_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="renova-synth")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="generate cases and validate them")
    gen.add_argument("--out", type=Path, default=Path("data/synth"))
    gen.add_argument("--cases", type=int, default=20)
    gen.add_argument("--seed", type=int, default=2026)
    val = sub.add_parser("validate", help="validate an existing dataset")
    val.add_argument("root", type=Path)
    sch = sub.add_parser("schema", help="write the ground-truth JSON Schema")
    sch.add_argument("--out", type=Path, default=SCHEMA_PATH)
    args = parser.parse_args(argv)

    if args.command == "schema":
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(schema(), indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {args.out}")
        return 0
    if args.command == "generate":
        summary = generate(args.out, args.cases, args.seed)
        print(f"cases: {summary.cases}  documents: {summary.documents}  scanned: {summary.scans}")
        for doc_type, count in summary.by_type.items():
            print(f"  {doc_type:<22} {count}")
        print("injected errors: " + ", ".join(f"{k}={v}" for k, v in summary.errors.items()))
    root = args.out if args.command == "generate" else args.root
    report = validate_dataset(root)
    for problem in report.problems:
        print(f"INVALID {problem}", file=sys.stderr)
    print(f"validated {report.cases} cases, {report.documents} documents: {'OK' if report.ok else 'FAILED'}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
