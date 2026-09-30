from __future__ import annotations

import copy

import pytest

from score_sw_fabric.compiler.mapping import project_mapping
from score_sw_fabric.compiler.models import CompilerSemanticError
from score_sw_fabric.compiler.package import validate_closure
from score_sw_fabric.compiler.reader import _validate_plan
from score_sw_fabric.process_source.reader import InputError
from tests.compiler_support import compiler_profile, mapping, plan


def test_native_file_count_exact_maximum_and_one_over() -> None:
    profile = compiler_profile()
    files = {"workflow.toml": "", "workflow.fabro": ""}
    files.update({f"support/{index:03d}.txt": "" for index in range(510)})
    validate_closure(files, "workflow.toml", profile)
    files["support/overflow.txt"] = ""
    with pytest.raises(InputError) as caught:
        validate_closure(files, "workflow.toml", profile)
    assert caught.value.code == "PACKAGE_FILE_LIMIT"


def test_per_file_and_total_bytes_exact_maximum_and_one_over() -> None:
    profile = compiler_profile()
    unit = "x" * 524_288
    validate_closure({"workflow.toml": "", "workflow.fabro": unit}, "workflow.toml", profile)
    with pytest.raises(InputError) as per_file:
        validate_closure(
            {"workflow.toml": "", "workflow.fabro": unit + "x"},
            "workflow.toml",
            profile,
        )
    assert per_file.value.code == "PACKAGE_FILE_SIZE"

    files = {
        "workflow.toml": unit,
        "workflow.fabro": unit,
        "support/a": unit,
        "support/b": unit,
    }
    validate_closure(files, "workflow.toml", profile)
    files["support/over"] = "x"
    with pytest.raises(InputError) as total:
        validate_closure(files, "workflow.toml", profile)
    assert total.value.code == "PACKAGE_SOURCE_SIZE"


def test_plan_instance_and_dependency_exact_maximum_and_one_over() -> None:
    selected = plan(tuple(f"instance-{index:05d}" for index in range(10_000)))
    instances = selected["instances"]
    for index, item in enumerate(instances):
        width = 11 if 11 <= index < 66 else 10
        item["dependency_ids"] = [
            instances[index - offset]["instance_id"] for offset in range(1, min(index, width) + 1)
        ]
    assert sum(len(item["dependency_ids"]) for item in instances) == 100_000
    _validate_plan(selected)
    over = copy.deepcopy(selected)
    over["instances"][-1]["dependency_ids"].append(instances[0]["instance_id"])
    with pytest.raises(InputError) as dependencies:
        _validate_plan(over)
    assert dependencies.value.code == "PLAN_DEPENDENCY_LIMIT"

    extra = copy.deepcopy(selected)
    extra["instances"].append(
        {
            "instance_id": "overflow",
            "applicability": "required",
            "effective_disposition": "create",
            "dependency_ids": [],
        }
    )
    with pytest.raises(InputError) as count:
        _validate_plan(extra)
    assert count.value.code == "PLAN_INSTANCE_LIMIT"


def test_action_budget_exact_maximum_and_one_over() -> None:
    selected = mapping()
    action = selected["rules"][0]["actions"][0]
    ceilings = compiler_profile()["limits"]["action_budget"]
    action["budget"].update(
        {
            "wall_time_seconds": ceilings["wall_time_seconds"],
            "attempts": ceilings["attempts"],
            "tool_calls": ceilings["tool_calls"],
        }
    )
    project_mapping(plan(), selected, compiler_profile())
    action["budget"]["tool_calls"] += 1
    with pytest.raises(CompilerSemanticError) as caught:
        project_mapping(plan(), selected, compiler_profile())
    assert caught.value.code == "ACTION_BUDGET"
