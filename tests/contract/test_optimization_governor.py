"""Unknown telemetry, operational admission, routing and stop conditions."""

from __future__ import annotations

import pytest

from score_sw_fabric.optimization.common import OptimizationError, record
from score_sw_fabric.optimization.model_router import route
from score_sw_fabric.optimization.progress import progress
from score_sw_fabric.optimization.telemetry import aggregate, usage
from score_sw_fabric.optimization.token_governor import govern
from score_sw_fabric.optimization.workflow_modes import mode_plan
from score_sw_fabric.process_source.reader import InputError


def test_usage_unknowns_and_invalid_cache_split() -> None:
    value = usage(
        {"call": "c", "task": "t", "role": "r", "model": "m", "workflow": "w", "increment": "011"},
        {"input_tokens": 100},
    )
    assert value["metrics"]["cached_input_tokens"] is None
    assert value["metrics"]["cost_microusd"] is None
    assert aggregate([value])["metrics"]["cached_input_tokens"] is None
    with pytest.raises(OptimizationError, match="CACHE_SPLIT"):
        usage(
            value["dimensions"],
            {"input_tokens": 10, "cached_input_tokens": 9, "uncached_input_tokens": 9},
        )


def admission() -> dict:
    return record(
        "agent_admission",
        decision="admissible",
        call_authorized=False,
        remaining={"input_tokens": 2000000, "output_tokens": 200000, "calls": 6},
        profile={"id": "configured-profile", "max_output_tokens": 32000},
        provider_configured=True,
        offering={"id": "catalogue-id"},
    )


def test_governor_narrows_absolute_ceiling_and_stops_unknown_usage() -> None:
    result = govern("S1", admission(), 1000, [])
    assert result["limits"]["input_tokens"] <= 80000
    assert result["limits"]["output_tokens"] <= 10000
    assert result["call_authorized"] is False
    blocked = govern(
        "S1",
        admission(),
        1000,
        [
            usage(
                {
                    "call": "c",
                    "task": "t",
                    "role": "r",
                    "model": "m",
                    "workflow": "w",
                    "increment": "011",
                },
                {},
            )
        ],
    )
    assert blocked["decision"] == "refused"
    assert "USAGE_UNKNOWN" in blocked["reasons"]
    assert govern("S4", admission(), 1000, [])["decision"] == "refused"
    assert govern("S1", admission(), 1000, [], human_gate=True)["decision"] == "refused"


def test_escalation_and_critic_are_conditional() -> None:
    assert route("S1", gates_passed=True)["critic"]["required"] is False
    assert route("S3", gates_passed=True)["critic"]["required"] is True
    with pytest.raises(OptimizationError, match="ESCALATION_TRIGGER"):
        route("S1", gates_passed=True, request_stronger=True)
    assert (
        route("S2", gates_passed=False, corrections=1, request_stronger=True)["tier"] == "stronger"
    )


def test_progress_does_not_invent_correction_or_ignore_evidence_refresh() -> None:
    old = {"source": "a", "evidence": "a", "failures": 2}
    assert (
        progress(old, old, mode="correction", visits=1)["stop_reason"]
        == "NO_PROGRESS_AFTER_CORRECTION"
    )
    assert progress(old, {**old, "failures": 1}, mode="correction", visits=1)["made_progress"]
    assert progress(old, {**old, "evidence": "b"}, mode="evidence-refresh")["made_progress"]
    assert (
        progress(old, {**old, "evidence": "b"}, mode="correction", visits=1)["made_progress"]
        is False
    )


@pytest.mark.parametrize(
    "mode", ["full", "delta", "correction", "verification-only", "evidence-refresh"]
)
def test_all_modes_preserve_required_checks_and_human_gates(mode: str) -> None:
    plan = mode_plan(mode, ["build", "trace", "integration"], ["human-review"])
    assert plan["mandatory_checks"] == ["build", "integration", "trace"]
    assert plan["human_gates"] == ["human-review"]
    if mode in {"verification-only", "evidence-refresh"}:
        assert plan["agent_required"] is False


def test_structured_stage_preserves_rationale_inside_artifact_contract() -> None:
    from score_sw_fabric.optimization.common import OptimizationError
    from score_sw_fabric.optimization.prompts import render_prompt, stage_result

    context = record("optimized_context_bundle", task="t")
    valid = {
        "schema_version": 1,
        "kind": "agent_result",
        "role_id": "r",
        "context_digest": context["digest"],
        "changed_paths": ["design.rst"],
        "native_ids_affected": ["native-id"],
        "evidence_refs": [],
        "unresolved_assumptions": ["draft rationale needs human review"],
        "proposed_next_action": "human-review",
        "self_reported_checks": [],
    }
    assert stage_result(valid, context)["unresolved_assumptions"] == valid["unresolved_assumptions"]
    with pytest.raises(InputError):
        stage_result({**valid, "narration": "Let me inspect"}, context)
    with pytest.raises(OptimizationError, match="CONTEXT_DRIFT"):
        stage_result({**valid, "context_digest": "0" * 64}, context)
    left = render_prompt("role", ["constraint"], "tools", "component", {"task": "a"}, {})
    right = render_prompt("role", ["constraint"], "tools", "component", {"task": "b"}, {})
    assert left.split('{"task"')[0] == right.split('{"task"')[0]


def test_critic_receives_bounded_review_pack() -> None:
    from score_sw_fabric.optimization.review_pack import review_pack

    context = record(
        "optimized_context_bundle", l0={"constraints": ["safety"]}, l1={"a.cpp": "source"}, l2={}
    )
    pack = review_pack(
        context,
        ["a.cpp"],
        {"path": "diff.patch", "sha256": "0" * 64},
        [record("fixture_test_summary", status="pass")],
        ["human-review"],
    )
    assert pack["human_review"] == "pending"
    with pytest.raises(OptimizationError, match="REVIEW_OUT_OF_SCOPE"):
        review_pack(context, ["b.cpp"], {}, [], [])


def test_governor_refuses_unconfigured_provider_and_absolute_budget() -> None:
    from score_sw_fabric.assurance.models import seal

    raw = admission()
    raw["remaining"]["calls"] = 0
    assert "BUDGET_EXHAUSTED" in govern("S1", seal(raw), 1, [])["reasons"]
    raw["provider_configured"] = False
    assert "PROVIDER_UNAVAILABLE" in govern("S1", seal(raw), 1, [])["reasons"]
    assert "CONTEXT_BUDGET" in govern("S1", admission(), 100000, [])["reasons"]


def test_all_hard_stop_reasons_are_explicit() -> None:
    state = {"source": "s", "evidence": "e", "failures": 1}
    for field, reason in [
        ("repeated_query", "REPEATED_QUERY"),
        ("repeated_failure", "REPEATED_FAILURE"),
        ("budget_exhausted", "BUDGET_EXHAUSTED"),
        ("usage_unknown", "USAGE_UNKNOWN"),
        ("human_gate", "HUMAN_GATE"),
    ]:
        assert progress(state, state, **{field: True})["stop_reason"] == reason
    assert progress(state, state, visits=2)["stop_reason"] == "CORRECTION_LIMIT"


def test_benchmark_measures_actual_impact_context_pipeline(tmp_path) -> None:
    from score_sw_fabric.optimization.benchmark import run_benchmark

    result = run_benchmark(tmp_path)
    assert len(result["comparisons"]) == 5
    for comparison in result["comparisons"]:
        assert comparison["baseline_outcome"] == comparison["optimized_outcome"]
        assert comparison["provider_metrics"]["uncached_input_tokens"] is None
        assert comparison["estimated_reduction_percent"] >= 60
        assert comparison["context_digest"]


def test_mode_does_not_invent_human_gates() -> None:
    assert mode_plan("delta", ["mandatory-test"], [])["human_gates"] == []


def test_compiler_projection_preserves_all_mandatory_actions() -> None:
    from score_sw_fabric.compiler.optimization import narrow_projection

    context = record(
        "optimized_context_bundle",
        manifest_digest="0" * 64,
        l0={"task": "t", "constraints": ["safety"]},
        l1={"a.cpp": "source"},
        skills=[],
    )
    decision = govern("S1", admission(), 1000, [], manifest_digest="0" * 64)
    projection = {
        "actions": [
            {
                "ref": "implement",
                "type": "agent",
                "purpose": "Implement bounded task",
                "prohibited_authority": ["no acceptance"],
                "budget": {"input_tokens": 2000000, "output_tokens": 100000, "attempts": 6},
            },
            {"ref": "tests", "type": "deterministic_check"},
            {"ref": "review", "type": "human"},
        ],
        "edges": ["unchanged-edges"],
        "loop_policies": ["unchanged-loops"],
    }
    bindings = {"implement": {"context": context, "governor": decision}}
    narrowed, receipt = narrow_projection(
        projection, bindings, mode_plan("delta", ["tests"], ["review"])
    )
    assert narrowed["actions"][1:] == projection["actions"][1:]
    assert narrowed["edges"] == projection["edges"]
    assert narrowed["loop_policies"] == projection["loop_policies"]
    assert narrowed["actions"][0]["budget"]["output_tokens"] == 10000
    assert receipt["execution_authorized"] is False
    with pytest.raises(OptimizationError, match="MODE_REQUIRES_COMMAND_ONLY"):
        narrow_projection(
            projection, bindings, mode_plan("verification-only", ["tests"], ["review"])
        )


def test_original_role_ledger_cannot_be_reset_by_empty_optimization_usage() -> None:
    from score_sw_fabric.assurance.models import seal

    old = admission()
    old["used"] = {"calls": 2, "input_tokens": 80000, "output_tokens": 10000}
    result = govern("S1", seal(old), 1000, [])
    assert "BUDGET_EXHAUSTED" in result["reasons"]
    assert result["limits"]["calls"] == 0


def test_self_audit_detects_policy_and_symbol_drift(tmp_path) -> None:
    import shutil
    from pathlib import Path

    import yaml

    from score_sw_fabric.optimization.audit import audit

    root = Path(__file__).resolve().parents[2]
    feature = "specs/011-change-impact-and-freshness"
    coverage = yaml.safe_load((root / feature / "coverage.yaml").read_text())
    paths = {path for entry in coverage.values() for path in entry["code"] + entry["tests"]}
    paths.update(
        {
            "policies/optimization-v1.yaml",
            "profiles/optimization-skills-v1.yaml",
            "docs/backlog/roadmap.md",
            *(
                feature + "/" + file
                for file in [
                    "spec.md",
                    "tasks.md",
                    "coverage.yaml",
                    "contracts/optimization.md",
                    "schemas/README.md",
                    "acceptance.md",
                    "quickstart.md",
                ]
            ),
        }
    )
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / path, target)
    for skill in (root / ".agents/skills").glob("score-*"):
        shutil.copytree(skill, tmp_path / ".agents/skills" / skill.name)
    assert audit(tmp_path)["failures"] == []
    policy_path = tmp_path / "policies/optimization-v1.yaml"
    policy = yaml.safe_load(policy_path.read_text())
    policy["operational"]["S1"]["input_tokens"] += 1
    policy["classification"]["broad_paths"] += 1
    policy_path.write_text(yaml.safe_dump(policy))
    coverage["FR-001"]["symbols"]["src/score_sw_fabric/optimization/evidence_query.py"] = [
        "missing_query"
    ]
    (tmp_path / feature / "coverage.yaml").write_text(yaml.safe_dump(coverage))
    report = audit(tmp_path)
    assert report["state"] == "blocked"
    assert set(report["failures"]) == {
        "POLICY_ENVELOPE_DRIFT",
        "CLASSIFICATION_POLICY_DRIFT",
        "FR-001:SYMBOL_LINK",
    }
