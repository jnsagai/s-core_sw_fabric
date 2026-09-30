from __future__ import annotations

from score_sw_fabric.artifacts.trace import evaluate_trace


def test_missing_artifact_remains_in_denominator() -> None:
    obligation = {
        "id": "OBL-1",
        "kind": "artifact",
        "scope": "fixture",
        "path_rule_id": None,
        "classification": "native_artifact",
        "target_role": "comp_req",
        "required_native_id": "MISSING",
        "mandatory": True,
        "authority": {"fixture": True},
        "state": "expected",
        "findings": [],
    }
    index = {"wrappers": [], "needs": [], "relations": []}
    evaluated, coverage, _, valid = evaluate_trace([obligation], index, {"path_rules": []})
    assert valid is False
    assert evaluated[0]["state"] == "unresolved"
    assert coverage[0]["denominator"] == ["OBL-1"]
    assert coverage[0]["numerator"] == []


def test_wrong_native_type_does_not_satisfy_role() -> None:
    obligation = {
        "id": "OBL-2",
        "kind": "artifact",
        "scope": "fixture",
        "path_rule_id": None,
        "classification": "native_artifact",
        "target_role": "comp_req",
        "required_native_id": None,
        "mandatory": True,
        "authority": {"fixture": True},
        "state": "expected",
        "findings": [],
    }
    index = {"wrappers": [], "needs": [{"native_id": "X", "type": "feat_req"}], "relations": []}
    evaluated, _, _, valid = evaluate_trace([obligation], index, {"path_rules": []})
    assert valid is False
    assert evaluated[0]["state"] == "unresolved"
