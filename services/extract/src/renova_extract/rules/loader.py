"""Loads rule files and guards their versioning.

One file per published rule version: ``packages/rules/rules/<ID>@<version>.yaml``. A published
version never changes: ``packages/rules/rules.lock.json`` records each version's content hash,
and the tests fail when a file changes without a new version or a published version disappears.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from pydantic import TypeAdapter

from renova_extract.rules.model import Rule, RuleFile

RULE_ADAPTER: TypeAdapter[Rule] = TypeAdapter(Rule)


def rules_dir(root: Path) -> Path:
    return root / "rules"


def load_rule(path: Path) -> Rule:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    rule = RuleFile.model_validate({"rule": raw}).rule
    if path.name != f"{rule.key}.yaml":
        raise ValueError(f"{path.name}: file name must be {rule.key}.yaml")
    return rule


def load_rules(root: Path) -> list[Rule]:
    rules = [load_rule(p) for p in sorted(rules_dir(root).glob("*.yaml"))]
    keys = [r.key for r in rules]
    if len(keys) != len(set(keys)):
        raise ValueError("a rule version is defined twice")
    return rules


def content_hash(rule: Rule) -> str:
    canonical = json.dumps(RULE_ADAPTER.dump_python(rule, mode="json"), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def lock_entries(rules: list[Rule]) -> dict[str, str]:
    return {r.key: content_hash(r) for r in sorted(rules, key=lambda r: (r.id, r.version))}


def lock_path(root: Path) -> Path:
    return root / "rules.lock.json"


def schema_path(root: Path) -> Path:
    return root / "schema" / "rule.schema.json"


def rule_schema() -> dict[str, object]:
    schema = RuleFile.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "RenovaCheck rule file (the document is the value of `rule`)"
    return schema
