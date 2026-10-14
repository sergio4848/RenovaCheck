"""Validates a generated dataset against the committed JSON Schema and the cross-reference rules."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from renova_synth.model import CaseTruth

# In the repository the schema sits under packages/rules; containers point RENOVA_SCHEMA_PATH at it.
_REPO_SCHEMA = Path(__file__).resolve().parents[4] / "packages" / "rules" / "schema" / "ground_truth.schema.json"
SCHEMA_PATH = Path(os.environ.get("RENOVA_SCHEMA_PATH", str(_REPO_SCHEMA)))


@dataclass
class ValidationReport:
    cases: int = 0
    documents: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems and self.cases > 0


def schema() -> dict[str, Any]:
    """The JSON Schema generated from the model; committed to SCHEMA_PATH for other consumers."""
    generated = CaseTruth.model_json_schema()
    generated["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    generated["$id"] = "https://renovacheck.invalid/schema/ground_truth.schema.json"
    return generated


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(path.read_text())
    return loaded


def validate_dataset(root: Path, schema_path: Path = SCHEMA_PATH) -> ValidationReport:
    validator = Draft202012Validator(load_schema(schema_path))
    report = ValidationReport()
    for truth_file in sorted(root.glob("SYN-*/ground_truth.json")):
        report.cases += 1
        raw = json.loads(truth_file.read_text())
        for error in validator.iter_errors(raw):
            location = "/".join(str(p) for p in error.absolute_path)
            report.problems.append(f"{truth_file.parent.name}: schema: {location}: {error.message}")
        try:
            truth = CaseTruth.model_validate(raw)
        except ValueError as exc:
            report.problems.append(f"{truth_file.parent.name}: model: {exc}")
            continue
        for doc in truth.documents:
            report.documents += 1
            pdf = truth_file.parent / doc.file
            if not pdf.is_file():
                report.problems.append(f"{doc.doc_id}: missing file {doc.file}")
            elif hashlib.sha256(pdf.read_bytes()).hexdigest() != doc.sha256:
                report.problems.append(f"{doc.doc_id}: sha256 mismatch for {doc.file}")
    if report.cases == 0:
        report.problems.append(f"no cases found under {root}")
    return report
