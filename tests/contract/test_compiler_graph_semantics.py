from __future__ import annotations

import copy

import pytest

from score_sw_fabric.compiler.graph_validation import validate_graph
from score_sw_fabric.compiler.ir import build_ir
from score_sw_fabric.compiler.mapping import project_mapping
from score_sw_fabric.compiler.models import CompilerSemanticError
from tests.compiler_support import compiler_profile, mapping, plan


def _graph() -> dict[str, object]:
    selected = mapping("shared-parallel-review")
    return build_ir(
        project_mapping(plan(), selected, compiler_profile()), selected, compiler_profile()
    )


def test_valid_shared_gate_dominates_subject_work() -> None:
    receipt = validate_graph(_graph(), compiler_profile())
    assert receipt["valid"] is True
    assert receipt["counts"]["gates"] == 1


def test_gate_bypass_reports_concrete_path() -> None:
    graph = _graph()
    nodes = {node["ref"]: node["id"] for node in graph["nodes"]}
    template = copy.deepcopy(graph["edges"][0])
    template["id"] = "bypass"
    template["source"] = nodes["prepare"]
    template["target"] = nodes["package"]
    graph["edges"].append(template)
    with pytest.raises(CompilerSemanticError) as caught:
        validate_graph(graph, compiler_profile())
    finding = next(item for item in caught.value.findings if item["code"] == "GATE_BYPASS")
    assert finding["path"][0] == "start"
    assert finding["path"][-1] == "exit"


def test_unrouted_outcome_and_unbounded_cycle_are_rejected() -> None:
    graph = _graph()
    work = next(node for node in graph["nodes"] if node["ref"] == "prepare")
    work["fallible_outcomes"].append("failure")
    with pytest.raises(CompilerSemanticError) as outcome:
        validate_graph(graph, compiler_profile())
    assert any(item["code"] == "OUTCOME_GAP" for item in outcome.value.findings)

    graph = _graph()
    nodes = {node["ref"]: node["id"] for node in graph["nodes"]}
    template = copy.deepcopy(graph["edges"][0])
    template.update({"id": "cycle", "source": nodes["package"], "target": nodes["prepare"]})
    graph["edges"].append(template)
    with pytest.raises(CompilerSemanticError) as cycle:
        validate_graph(graph, compiler_profile())
    assert any(item["code"] == "UNBOUNDED_CYCLE" for item in cycle.value.findings)
