from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from renova_extract.api.app import create_app
from renova_extract.core.config import Settings
from renova_extract.eval.rules import attribute
from renova_extract.rules import __main__ as rules_cli
from renova_extract.rules.engine import RuleEngine
from renova_extract.rules.loader import load_rule, load_rules, lock_entries, lock_path, rule_schema, schema_path
from renova_extract.rules.model import CaseIn
from tests.conftest import make_settings

ROOT = Settings().rules_dir
RULES = load_rules(ROOT)
ENGINE = RuleEngine(RULES)
FIXTURES = Path(__file__).parent / "fixtures" / "rules"
BASE = json.loads((FIXTURES / "_base_case.json").read_text())


# ---------------------------------------------------------------------------- building cases
def _fields(spec: dict[str, list[Any]]) -> list[dict[str, Any]]:
    fields = []
    for name, item in spec.items():
        value, raw = item[0], item[1]
        confidence = item[2] if len(item) > 2 else 1.0
        status = "ok" if value is not None else "unreadable"
        fields.append({"name": name, "value": value, "raw_text": raw, "status": status, "confidence": confidence})
    return fields


def build_case(patch: dict[str, Any]) -> CaseIn:
    case = copy.deepcopy(BASE)
    docs = {d["doc_id"]: d for d in case["documents"]}
    for doc in copy.deepcopy(patch.get("add", [])):
        docs[doc["doc_id"]] = doc
    for doc_id in patch.get("drop", []):
        docs.pop(doc_id)
    for doc_id, changes in patch.get("set", {}).items():
        docs[doc_id]["fields"].update(changes)
    for doc_id in patch.get("clear", []):
        docs[doc_id]["fields"] = {}
    for doc_id, attrs in patch.get("doc", {}).items():
        docs[doc_id].update(attrs)
    documents = [{**d, "fields": _fields(d["fields"])} for d in docs.values()]
    return CaseIn.model_validate({**case, "documents": documents})


def _summary(findings: Any, rule_id: str) -> list[tuple[str, tuple[str, ...], tuple[str, ...]]]:
    return sorted((f.outcome, f.subject_doc_ids, tuple(sorted(f.fields))) for f in findings if f.rule_id == rule_id)


FIXTURE_CASES = [
    pytest.param(path.stem, case, id=f"{path.stem}: {case['name']}")
    for path in sorted(FIXTURES.glob("*@*.json"))
    for case in json.loads(path.read_text())["cases"]
]


# ---------------------------------------------------------------------------- regression fixtures
@pytest.mark.parametrize(("key", "case"), FIXTURE_CASES)
def test_rule_regression_fixture(key: str, case: dict[str, Any]) -> None:
    rule_id = key.split("@")[0]
    findings = ENGINE.evaluate(build_case(case["patch"])).findings
    expected = sorted((e["outcome"], tuple(sorted(e["subjects"])), tuple(sorted(e["fields"]))) for e in case["expect"])
    assert _summary(findings, rule_id) == expected


def test_every_rule_version_has_a_regression_fixture_with_a_positive_case() -> None:
    for rule in RULES:
        path = FIXTURES / f"{rule.key}.json"
        assert path.exists(), f"missing regression fixture for {rule.key}"
        cases = json.loads(path.read_text())["cases"]
        assert any(c["expect"] for c in cases), f"{rule.key} has no case where it fires"
        assert any(not c["expect"] for c in cases), f"{rule.key} has no case where it stays silent"


def test_the_consistent_case_has_no_findings() -> None:
    assert ENGINE.evaluate(build_case({})).findings == ()


# ---------------------------------------------------------------------------- rule files
def test_rules_carry_the_required_metadata() -> None:
    assert len(RULES) >= 12
    for rule in RULES:
        assert str(rule.source_url).startswith("https://")
        assert rule.valid_from is not None
        assert rule.title_pl and rule.notes and rule.edition and rule.inputs.doc_types


def test_committed_schema_matches_the_model() -> None:
    committed = json.loads(schema_path(ROOT).read_text())
    assert committed == json.loads(json.dumps(rule_schema()))


def test_published_rule_versions_are_immutable() -> None:
    published = json.loads(lock_path(ROOT).read_text())
    current = lock_entries(RULES)
    assert set(published) == set(current), (
        "rules.lock.json is out of date: run python -m renova_extract.rules lock --write"
    )
    changed = [k for k in current if published[k] != current[k]]
    assert not changed, f"published rules changed without a new version: {changed}"


def test_lock_command_refuses_a_changed_published_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "rules-root"
    (root / "rules").mkdir(parents=True)
    source = ROOT / "rules" / "CMP-03@1.yaml"
    (root / "rules" / source.name).write_text(source.read_text())
    monkeypatch.setenv("RENOVA_RULES_DIR", str(root))
    assert rules_cli.main(["lock", "--write"]) == 0
    raw = yaml.safe_load(source.read_text())
    raw["severity"] = "critical"
    (root / "rules" / source.name).write_text(yaml.safe_dump(raw, allow_unicode=True))
    assert rules_cli.main(["lock"]) == 1
    assert rules_cli.main(["lock", "--write"]) == 1


def test_file_name_must_match_id_and_version(tmp_path: Path) -> None:
    source = ROOT / "rules" / "CMP-03@1.yaml"
    wrong = tmp_path / "CMP-03@2.yaml"
    wrong.write_text(source.read_text())
    with pytest.raises(ValueError, match="file name"):
        load_rule(wrong)


def test_threshold_shape_depends_on_the_comparator(tmp_path: Path) -> None:
    raw = yaml.safe_load((ROOT / "rules" / "CMP-02@1.yaml").read_text())
    raw["threshold"] = {"tolerance_pln": 1}
    path = tmp_path / "CMP-02@1.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True))
    with pytest.raises(ValueError):
        load_rule(path)


# ---------------------------------------------------------------------------- selection by date
def _versioned(tmp_path: Path) -> RuleEngine:
    raw = yaml.safe_load((ROOT / "rules" / "CMP-03@1.yaml").read_text())
    first = {**raw, "valid_to": date(2026, 3, 31)}
    second = {**raw, "version": 2, "valid_from": date(2026, 4, 1), "title_pl": "Odbiór po zawarciu umowy (wersja 2)"}
    (tmp_path / "rules").mkdir()
    for spec in (first, second):
        (tmp_path / "rules" / f"CMP-03@{spec['version']}.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True))
    return RuleEngine(load_rules(tmp_path))


def test_rules_are_selected_by_the_case_date(tmp_path: Path) -> None:
    engine = _versioned(tmp_path)
    assert [r.version for r in engine.select(date(2026, 3, 1))] == [1]
    assert [r.version for r in engine.select(date(2026, 6, 1))] == [2]
    assert engine.select(date(2025, 1, 1)) == []


def test_reference_date_prefers_application_then_contract_then_fallback() -> None:
    case = build_case({})
    assert RuleEngine.reference_date(case) == (date(2026, 3, 2), "application_date")
    assert RuleEngine.reference_date(build_case({"drop": ["D1"]})) == (date(2026, 3, 20), "contract_date")
    assert RuleEngine.reference_date(build_case({"drop": ["D1", "D2"]})) == (date(2026, 1, 1), "fallback")


def test_no_valid_rule_is_a_finding_not_silence() -> None:
    case = build_case({"set": {"D1": {"application_date": ["2024-01-10", "10.01.2024"]}}})
    evaluation = ENGINE.evaluate(case)
    assert evaluation.ruleset == ()
    assert [f.outcome for f in evaluation.findings] == ["no_rules"]


# ---------------------------------------------------------------------------- invariants
def test_document_order_does_not_change_findings() -> None:
    patch = {"set": {"D3": {"address_building_no": ["52", "52"]}, "D5": {"product_model": ["TVX10B", "TVX-10B"]}}}
    case = build_case(patch)
    reordered = case.model_copy(update={"documents": tuple(reversed(case.documents))})
    assert ENGINE.evaluate(case).findings == ENGINE.evaluate(reordered).findings


def test_fingerprint_is_stable_when_values_change_but_evidence_hash_is_not() -> None:
    one = ENGINE.evaluate(build_case({"set": {"D3": {"address_building_no": ["52", "52"]}}})).findings
    two = ENGINE.evaluate(build_case({"set": {"D3": {"address_building_no": ["53", "53"]}}})).findings
    assert one[0].fingerprint == two[0].fingerprint
    assert one[0].evidence_hash != two[0].evidence_hash


def test_findings_are_born_to_be_checked_with_reasons_and_evidence() -> None:
    findings = ENGINE.evaluate(build_case({"set": {"D3": {"address_building_no": ["52", "52"]}}})).findings
    finding = findings[0]
    assert finding.status == "do_sprawdzenia"
    assert "„52”" in finding.reason_pl and "„25”" in finding.reason_pl
    assert {(e.doc_id, e.value) for e in finding.evidence} >= {("D3", "52"), ("D1", "25")}


@pytest.mark.parametrize(
    ("family", "outcome", "fields", "rule"),
    [
        ("address", "discrepancy", ("address_building_no",), "ADR-01"),
        ("address", "match_after_normalization", ("address_street",), "ADR-02"),
        ("product", "discrepancy", ("product_model",), "PRD-01"),
        ("product", "discrepancy", ("product_power_kw",), "PRD-02"),
        ("product", "agreed_change", ("product_model", "product_power_kw"), "PRD-03"),
        ("amount", "discrepancy", ("amount_net", "amount_gross"), "AMT-01"),
        ("amount", "explained_by_advance", ("amount_due", "advance_amount"), "AMT-02"),
        ("amount", "explained_by_correction", ("amount_gross",), "AMT-03"),
        ("completeness", "missing_document", (), "CMP-01"),
        ("completeness", "discrepancy", ("invoice_date", "contract_date"), "CMP-02"),
        ("completeness", "discrepancy", ("signature_investor",), "CMP-04"),
        ("none", "unreadable_source", (), "QLT-01"),
    ],
)
def test_every_expected_finding_kind_belongs_to_exactly_one_rule(
    family: str, outcome: str, fields: tuple[str, ...], rule: str
) -> None:
    assert attribute(RULES, family, outcome, fields) == rule


# ---------------------------------------------------------------------------- API
TOKEN = "test-token-0123456789"


@pytest.fixture
def api() -> Any:
    with TestClient(create_app(make_settings(internal_token=TOKEN))) as client:
        yield client


def _payload(patch: dict[str, Any]) -> dict[str, Any]:
    return build_case(patch).model_dump(mode="json")


def test_evaluate_endpoint_returns_findings(api: TestClient) -> None:
    response = api.post(
        "/v1/cases/evaluate",
        json=_payload({"drop": ["D4"]}),
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reference_date"] == "2026-03-02" and body["reference_source"] == "application_date"
    assert {r["id"] for r in body["ruleset"]} == {r.id for r in RULES}
    assert [(f["rule_id"], f["outcome"], f["status"]) for f in body["findings"]] == [
        ("CMP-01", "missing_document", "do_sprawdzenia")
    ]


def test_evaluate_requires_the_token(api: TestClient) -> None:
    assert api.post("/v1/cases/evaluate", json=_payload({})).status_code == 401


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p["documents"].append(p["documents"][0]),
        lambda p: p["documents"][0]["fields"].append(p["documents"][0]["fields"][0]),
        lambda p: p["documents"][0].update(doc_type="paragon"),
        lambda p: p["documents"][0]["fields"][0].update(value=None),
        lambda p: p.update(documents=p["documents"] * 11),
    ],
)
def test_evaluate_rejects_inputs_outside_the_contract(api: TestClient, mutate: Any) -> None:
    payload = _payload({})
    mutate(payload)
    response = api.post("/v1/cases/evaluate", json=payload, headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 422
