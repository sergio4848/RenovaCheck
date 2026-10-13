"""Keyword classifier for document types (packages/rules/doc_types.yaml)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from renova_extract.text.normalize import fold


@dataclass(frozen=True)
class Pattern:
    regex: re.Pattern[str]
    weight: int


@dataclass(frozen=True)
class Classification:
    doc_type: str | None
    confidence: float
    scores: dict[str, int]
    evidence: tuple[str, ...]


class DocTypeClassifier:
    def __init__(self, types: dict[str, list[Pattern]], min_score: int, min_margin: int) -> None:
        self.types = types
        self.min_score = min_score
        self.min_margin = min_margin

    @classmethod
    def from_yaml(cls, path: Path) -> DocTypeClassifier:
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        types = {
            name: [Pattern(re.compile(p["regex"]), int(p["weight"])) for p in spec["patterns"]]
            for name, spec in raw["types"].items()
        }
        return cls(types, int(raw["min_score"]), int(raw["min_margin"]))

    def classify(self, text: str) -> Classification:
        folded = fold(text)
        scores: dict[str, int] = {}
        evidence: dict[str, list[str]] = {}
        for name, patterns in self.types.items():
            for pattern in patterns:
                match = pattern.regex.search(folded)
                if match:
                    scores[name] = scores.get(name, 0) + pattern.weight
                    evidence.setdefault(name, []).append(match.group(0))
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        if not ranked:
            return Classification(None, 0.0, {}, ())
        best, best_score = ranked[0]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        confidence = round(best_score / (best_score + runner_up), 3)
        if best_score < self.min_score or best_score - runner_up < self.min_margin:
            return Classification(None, confidence, dict(ranked), ())
        return Classification(best, confidence, dict(ranked), tuple(evidence[best]))
