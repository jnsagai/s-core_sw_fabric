"""Impact, lazy context and procedural Skill trust boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

from score_sw_fabric.optimization.common import OptimizationError, canonical, record
from score_sw_fabric.optimization.context_budget import build_bundle
from score_sw_fabric.optimization.context_manifest import manifest
from score_sw_fabric.optimization.impact import freshness, impact
from score_sw_fabric.optimization.skill_selection import registry, render, select
from score_sw_fabric.optimization.task_classification import classify


def index(nodes: list[dict], relations: list[dict]) -> dict:
    return record("artifact_index", wrappers=[], needs=nodes, relations=relations)


def test_removed_dependency_and_cycles_preserved() -> None:
    nodes = [{"key": "a", "fingerprint": "1"}, {"key": "b", "fingerprint": "1"}]
    old = index(nodes, [{"source": "b", "target": "a"}])
    new = index(nodes, [{"source": "a", "target": "b"}])
    result = impact(old, new)
    assert result["affected"] == ["a", "b"]
    assert result["relation_changes"]


def test_unknown_new_dependencies_fail_closed_and_widen() -> None:
    old = index([], [])
    new = index([{"key": "new", "fingerprint": "1"}], [{"source": "new", "target": None}])
    result = impact(old, new)
    assert result["state"] == "blocked"
    with pytest.raises(OptimizationError, match="IMPACT_BLOCKED"):
        manifest("task", "baseline", result, new, {"new": ["a.cpp"]})


def test_transitive_manifest_and_stale_baseline() -> None:
    old = index(
        [{"key": "a", "fingerprint": "1"}, {"key": "b", "fingerprint": "1"}],
        [{"source": "b", "target": "a"}],
    )
    new = index(
        [{"key": "a", "fingerprint": "2"}, {"key": "b", "fingerprint": "1"}], old["relations"]
    )
    changes = impact(old, new)
    result = manifest("task", "baseline", changes, new, {"b": ["b.cpp"], "a": ["a.cpp"]})
    assert result["native_ids"] == ["a", "b"]
    assert result["primary"] == ["a.cpp"]
    assert result["related"] == ["b.cpp"]
    assert result == manifest("task", "baseline", changes, new, {"a": ["a.cpp"], "b": ["b.cpp"]})
    with pytest.raises(OptimizationError, match="BASELINE_DRIFT"):
        build_bundle(result, "changed", {"constraints": "mandatory"}, {"a.cpp": "content"})


def test_required_safety_and_l0_never_trim_optional_context() -> None:
    new = index([{"key": "a", "fingerprint": "1"}], [{"source": "a", "target": "a"}])
    scope = manifest("t", "base", impact(index([], []), new), new, {"a": ["a.cpp"]})
    bundle = build_bundle(
        scope,
        "base",
        {"constraints": "safety", "output_contract": "json"},
        {"a.cpp": "required safety"},
        optional={"other": "x" * 10000},
        max_tokens=2000,
    )
    assert bundle["l0"]["constraints"] == "safety"
    assert bundle["l1"]["a.cpp"] == "required safety"
    assert bundle["omissions"]
    with pytest.raises(OptimizationError, match="REQUIRED_CONTEXT_LIMIT"):
        build_bundle(
            scope, "base", {"constraints": "x" * 10000}, {"a.cpp": "required"}, max_tokens=100
        )
    with pytest.raises(OptimizationError, match="REQUIRED_CONTEXT_MISSING"):
        build_bundle(scope, "base", {"constraints": "safety"}, {})


@pytest.mark.parametrize(
    "facts, expected",
    [
        ({"metadata_only": True}, "S0"),
        ({}, "S1"),
        ({"feature_change": True}, "S2"),
        ({"safety": True}, "S3"),
        ({"architecture": True}, "S3"),
        ({"modules": 5}, "S4"),
        ({"unknown_dependencies": True}, "unknown"),
    ],
)
def test_deterministic_classification(facts: dict, expected: str) -> None:
    result = classify("t", {"modules": 1, "paths": 2, "requirements": 1, **facts})
    assert result["class"] == expected
    assert result["confidence"] == "deterministic"


def test_baseline_vector_changes_invalidate_history_without_mutation() -> None:
    evidence = [{"id": "e1", "baseline": {"source": "old", "tool": "tool1"}}]
    decisions = [{"id": "d1", "baseline": {"source": "old", "tool": "tool1"}}]
    result = freshness({"source": "new", "tool": "tool1"}, evidence, decisions)
    assert result["stale_evidence"] == ["e1"]
    assert result["stale_decisions"] == ["d1"]
    assert evidence[0]["baseline"]["source"] == "old"


def test_skill_lazy_rendering_and_byte_drift(tmp_path: Path) -> None:
    folder = tmp_path / "score-implementation"
    (folder / "references").mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        "---\nname: score-implementation\ndescription: Draft code\n---\nNever approve.\n"
    )
    (folder / "references/detail.md").write_text("extended details")
    definitions = {
        "score-implementation": {"version": "1", "files": ["SKILL.md", "references/detail.md"]}
    }
    registered = registry(tmp_path, definitions)
    selection = select(
        registered, "implementation", {"implementation": ["score-implementation"]}, "base"
    )
    rendered = render(tmp_path, registered, selection, "base")
    assert "extended details" not in rendered["text"]
    assert (
        render(
            tmp_path,
            registered,
            selection,
            "base",
            reference="score-implementation/references/detail.md",
        )["text"]
        == "extended details"
    )
    with pytest.raises(OptimizationError, match="SKILL_MAPPING_UNKNOWN"):
        select(registered, "unknown", {}, "base")
    (folder / "references/detail.md").write_text("modified")
    with pytest.raises(OptimizationError, match="SKILL_DRIFT"):
        render(tmp_path, registered, selection, "base")


def test_opt_in_agent_context_uses_real_legacy_source_baseline(tmp_path: Path) -> None:
    from score_sw_fabric.agents.context import build_optimized_context
    from tests.agent_support import Scenario, git, ref, write_json, write_yaml

    scenario = Scenario(tmp_path)
    legacy = scenario.context()
    old = index(
        [{"key": "COMP_REQ_1", "fingerprint": "old"}],
        [{"source": "COMP_REQ_1", "target": "COMP_REQ_1"}],
    )
    new = index([{"key": "COMP_REQ_1", "fingerprint": "current"}], old["relations"])
    scope = manifest(
        "task.1",
        git(scenario.workspace, "rev-parse", "HEAD"),
        impact(old, new),
        new,
        {"COMP_REQ_1": ["docs/req.rst"]},
    )
    path = tmp_path / "control/optimized.yaml"
    write_yaml(
        path,
        {
            "schema_version": 1,
            "kind": "optimized_agent_context_request",
            "legacy_request": ref(legacy),
            "manifest": write_json(tmp_path / "control/manifest.json", scope),
            "constraints": ["preserve native requirements"],
            "max_tokens": 24000,
        },
    )
    status, bundle, _, _ = build_optimized_context(path)
    assert status == 0
    assert bundle["l1"]["docs/req.rst"] == (scenario.workspace / "docs/req.rst").read_text()
    assert bundle["l0"]["baseline"] == scope["baseline"]
    assert bundle["context_accounting"]["estimated_tokens"]["total"] >= len(canonical(bundle))


def test_broad_sensitive_work_cannot_bypass_s4_scope_authorization() -> None:
    result = classify("broad-safety", {"modules": 4, "paths": 8, "requirements": 2, "safety": True})
    assert result["class"] == "S4"
