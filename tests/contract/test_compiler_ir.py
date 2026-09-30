from __future__ import annotations

import copy

import pytest

from score_sw_fabric.compiler.ir import build_ir
from score_sw_fabric.compiler.mapping import project_mapping
from score_sw_fabric.compiler.models import CompilerSemanticError
from tests.compiler_support import action, compiler_profile, mapping, plan


def test_stable_ids_and_explicit_deterministic_check_mapping() -> None:
    selected = mapping()
    selected["rules"][0]["actions"][0] = action(
        "prepare", ["obligation-a"], action_type="deterministic_check"
    )
    first = build_ir(
        project_mapping(plan(), selected, compiler_profile()), selected, compiler_profile()
    )
    second = build_ir(
        project_mapping(plan(), selected, compiler_profile()), selected, compiler_profile()
    )
    assert first == second
    check = next(node for node in first["nodes"] if node["ref"] == "prepare")
    assert check["action_type"] == "deterministic_check"
    assert check["native_type"] == "command"
    assert check["model_capability"] == "none"


@pytest.mark.parametrize(
    "action_type", ["agent", "prompt", "command", "deterministic_check", "human"]
)
def test_supported_actions_retain_authority_and_budget(action_type: str) -> None:
    selected = mapping()
    selected["rules"][0]["actions"][0] = action(
        "prepare", ["obligation-a"], action_type=action_type
    )
    projected = project_mapping(plan(), selected, compiler_profile())
    item = projected["actions"][0]
    assert item["allowed_paths"] and item["data_destinations"]
    assert item["budget"]["wall_time_seconds"] == 60
    assert "approval" in item["prohibited_authority"]


def test_mapping_gap_conflict_and_excess_budget_fail_closed() -> None:
    selected = mapping()
    selected["rules"][0]["actions"] = selected["rules"][0]["actions"][:1]
    with pytest.raises(CompilerSemanticError) as gap:
        project_mapping(plan(), selected, compiler_profile())
    assert gap.value.code == "MAPPING_GAP"

    selected = mapping()
    selected["rules"][0]["actions"][0]["budget"]["attempts"] = 21
    with pytest.raises(CompilerSemanticError) as budget:
        project_mapping(plan(), selected, compiler_profile())
    assert budget.value.code == "ACTION_BUDGET"

    selected = mapping()
    duplicate = copy.deepcopy(selected["rules"][0])
    duplicate["id"] = "conflict"
    selected["rules"].append(duplicate)
    with pytest.raises(CompilerSemanticError) as conflict:
        project_mapping(plan(), selected, compiler_profile())
    assert conflict.value.code == "MAPPING_CONFLICT"
