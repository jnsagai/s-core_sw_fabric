from __future__ import annotations

from pathlib import Path

import pytest

from score_sw_fabric.compiler.graph_validation import validate_cyclic_component_count
from score_sw_fabric.compiler.ir import validate_ir_counts
from score_sw_fabric.compiler.mapping import project_mapping
from score_sw_fabric.compiler.models import CompilerSemanticError
from score_sw_fabric.compiler.package import validate_package_byte_count
from score_sw_fabric.compiler.reader import validate_mapping_rule_count
from score_sw_fabric.process_source.reader import InputError, read_bytes
from tests.compiler_support import action, compiler_profile, mapping, plan


def _sparse(path: Path, size: int) -> None:
    with path.open("wb") as stream:
        stream.seek(size - 1)
        stream.write(b" ")


def test_input_and_package_byte_limits_exact_maximum_and_one_over(tmp_path: Path) -> None:
    maximum = 64 * 1024 * 1024
    input_path = tmp_path / "maximum.input"
    _sparse(input_path, maximum)
    assert len(read_bytes(input_path)) == maximum
    _sparse(input_path, maximum + 1)
    with pytest.raises(InputError) as input_error:
        read_bytes(input_path)
    assert input_error.value.code == "INPUT_TOO_LARGE"

    profile = compiler_profile()
    validate_package_byte_count(maximum, profile)
    with pytest.raises(InputError) as package_error:
        validate_package_byte_count(maximum + 1, profile)
    assert package_error.value.code == "PACKAGE_SIZE"


def test_mapping_ir_and_cycle_count_limits_exact_maximum_and_one_over() -> None:
    profile = compiler_profile()
    validate_mapping_rule_count([None] * 50_000)
    with pytest.raises(InputError) as rules:
        validate_mapping_rule_count([None] * 50_001)
    assert rules.value.code == "MAPPING_RULE_LIMIT"

    validate_ir_counts(50_000, 200_000, profile)
    with pytest.raises(CompilerSemanticError) as nodes:
        validate_ir_counts(50_001, 200_000, profile)
    assert nodes.value.code == "NODE_LIMIT"
    with pytest.raises(CompilerSemanticError) as edges:
        validate_ir_counts(50_000, 200_001, profile)
    assert edges.value.code == "EDGE_LIMIT"

    validate_cyclic_component_count(10_000, profile)
    with pytest.raises(CompilerSemanticError) as cycles:
        validate_cyclic_component_count(10_001, profile)
    assert cycles.value.code == "CYCLE_LIMIT"


@pytest.mark.parametrize(
    "field",
    [
        "wall_time_seconds",
        "attempts",
        "tool_calls",
        "input_tokens",
        "output_tokens",
        "cost_microunits",
    ],
)
def test_each_action_budget_ceiling_is_inclusive_and_one_over_fails(field: str) -> None:
    profile = compiler_profile()
    ceilings = profile["limits"]["action_budget"]
    selected = mapping()
    selected["rules"][0]["actions"][0] = action("prepare", ["obligation-a"], action_type="agent")
    selected["rules"][0]["actions"][0]["budget"] = dict(ceilings)
    project_mapping(plan(), selected, profile)
    selected["rules"][0]["actions"][0]["budget"][field] += 1
    with pytest.raises(CompilerSemanticError) as caught:
        project_mapping(plan(), selected, profile)
    assert caught.value.code == "ACTION_BUDGET"
