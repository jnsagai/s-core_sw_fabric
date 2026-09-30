from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.artifacts.diff import CATEGORIES, compare_artifacts
from score_sw_fabric.artifacts.drift import inspect_drift
from score_sw_fabric.artifacts.impact import analyze_impact
from score_sw_fabric.artifacts.models import unevaluated_capabilities
from score_sw_fabric.artifacts.package import candidate_request, load_profile
from score_sw_fabric.compiler.reader import semantic_digest
from tests.artifact_support import prepare_artifact_case


def _review_candidate(tmp_path: Path) -> dict[str, Any]:
    request, output = prepare_artifact_case(tmp_path, operation="candidate")
    candidate = candidate_request(request, output)
    candidate["report"] = {
        "obligations": [{"id": "OBL-1", "state": "satisfied"}],
        "coverage": [{"metric_id": "fixture", "valid": True}],
        "impact": {"state": "complete", "subjects": []},
    }
    candidate["trace_validation"] = "passed"
    candidate["digest"] = semantic_digest(candidate)
    return candidate


def _reseal(candidate: dict[str, Any]) -> None:
    candidate["index"]["digest"] = semantic_digest(candidate["index"])
    candidate["digest"] = semantic_digest(candidate)


Mutation = Callable[[dict[str, Any]], None]


def _mutations() -> list[tuple[str, Mutation]]:
    return [
        ("baseline", lambda x: x["index"]["snapshot"].__setitem__("snapshot_id", "changed")),
        ("wrapper", lambda x: x["index"]["wrappers"].pop()),
        ("need", lambda x: x["index"]["needs"].pop()),
        (
            "option_status_classification",
            lambda x: x["index"]["needs"][0].__setitem__("status", "invalid"),
        ),
        ("content", lambda x: x["index"]["needs"][0].__setitem__("title", "Changed")),
        (
            "relation",
            lambda x: x["index"]["relations"][0].__setitem__("raw_selector", "CHANGED"),
        ),
        (
            "containment",
            lambda x: x["index"]["needs"][0].__setitem__("wrapper_key", "changed"),
        ),
        (
            "obligation",
            lambda x: x["report"]["obligations"][0].__setitem__("state", "unresolved"),
        ),
        ("coverage", lambda x: x["report"]["coverage"][0].__setitem__("valid", False)),
        ("impact", lambda x: x["report"]["impact"].__setitem__("state", "blocked")),
        (
            "template_profile",
            lambda x: x["index"]["profile"].__setitem__("digest", "0" * 64),
        ),
        (
            "native_validator",
            lambda x: x["index"]["native_receipt"]["validator"].__setitem__(
                "id", "changed-validator"
            ),
        ),
        (
            "file_bytes",
            lambda x: x["base_files"][0].__setitem__("sha256", "0" * 64),
        ),
    ]


@pytest.mark.parametrize(("expected", "mutate"), _mutations(), ids=[x[0] for x in _mutations()])
def test_single_mutation_isolated_to_exact_semantic_category(
    tmp_path: Path, expected: str, mutate: Mutation
) -> None:
    before = _review_candidate(tmp_path)
    after = copy.deepcopy(before)
    mutate(after)
    _reseal(after)
    result = compare_artifacts(before, after)
    changed = {
        name
        for name, values in result["categories"].items()
        if any(values[field] for field in ("added", "removed", "modified"))
    }
    assert changed == {expected}
    assert result["equivalent"] is False


def test_impact_is_transitive_cycle_safe_blocking_and_history_immutable() -> None:
    before = {
        "digest": "before",
        "wrappers": [],
        "needs": [
            {"key": "A", "fingerprint": "old", "origins": []},
            {"key": "B", "fingerprint": "same", "origins": []},
        ],
        "relations": [],
    }
    after = {
        "digest": "after",
        "wrappers": [],
        "needs": [
            {
                "key": "A",
                "fingerprint": "new",
                "origins": [{"plan_instance": "instance-a"}],
            },
            {"key": "B", "fingerprint": "same", "origins": []},
            {"key": "C", "fingerprint": "new", "origins": []},
        ],
        "relations": [
            {"source": "B", "target": "A", "external": False},
            {"source": "A", "target": "B", "external": False},
            {"source": "B", "target": None, "external": False},
        ],
    }
    historical = copy.deepcopy(before)
    current = copy.deepcopy(after)
    result = analyze_impact(before, after, {"impact_rules": [{"id": "conservative"}]})
    paths = {item["subject"]: item["path"] for item in result["dependency_paths"]}
    assert paths["A"] == ["A"]
    assert paths["B"] == ["A", "B"]
    assert result["newly_unlinked"] == ["C"]
    assert result["unknown_dependencies"] == ["B"]
    assert result["blockers"] == ["B", "C"]
    assert result["state"] == "blocked"
    assert result["affected_plan_instances"] == ["instance-a"]
    assert before == historical
    assert after == current


def test_direct_drift_and_relocation_have_no_authority_side_effect(
    tmp_path: Path,
) -> None:
    first = _review_candidate(tmp_path / "first")
    second = _review_candidate(tmp_path / "second")
    assert first == second
    tampered = copy.deepcopy(first)
    tampered["overlay_files"][0]["content"] += "direct edit"
    profile = load_profile(Path("profiles/s_core_native_artifacts_v1.yaml"))
    result = inspect_drift(tampered, profile)
    assert result["clean"] is False
    assert result["direct_output_drift"] is True
    assert result["findings"][0]["code"] == "GENERATED_DRIFT"
    assert first["capabilities"] == unevaluated_capabilities()
    assert set(first["capabilities"]) == {
        "registration",
        "execution",
        "evidence",
        "acceptance",
        "engineering_readiness",
        "release",
    }
    assert set(CATEGORIES) == {name for name, _ in _mutations()}
