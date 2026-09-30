from __future__ import annotations

import copy
from pathlib import Path

import pytest

from score_sw_fabric.compiler.models import CompilerSemanticError
from score_sw_fabric.compiler.package import (
    compile_package,
    validate_package,
    write_package,
)
from score_sw_fabric.compiler.reader import load_compiler_inputs
from score_sw_fabric.process_source.reader import InputError
from tests.compiler_support import RecordingValidator, prepare_case, sentinel


def test_package_has_total_provenance_and_unevaluated_boundary(tmp_path: Path) -> None:
    request, output = prepare_case(tmp_path)
    inputs = load_compiler_inputs(request)
    validator = RecordingValidator()
    package = compile_package(inputs, native_validator=validator)
    assert validate_package(package, inputs.compiler_profile)["valid"] is True
    assert len(validator.calls) == 1
    assert set(package["compile_report"]["capabilities"].values()) == {"not_evaluated"}
    semantic = package["manifest"]["ir"]
    covered = {(item["kind"], str(item["id"])) for item in package["source_map"]}
    assert all(("node", node["id"]) in covered for node in semantic["nodes"])
    write_package(output, package, inputs)
    assert output.read_bytes().endswith(b"\n")


@pytest.mark.parametrize("mutation", ["content", "missing", "extra", "traversal", "case"])
def test_closure_mutations_are_rejected(tmp_path: Path, mutation: str) -> None:
    request, _ = prepare_case(tmp_path)
    inputs = load_compiler_inputs(request)
    package = compile_package(inputs, native_validator=RecordingValidator())
    changed = copy.deepcopy(package)
    if mutation == "content":
        changed["files"]["workflow.fabro"] += "// drift\n"
    elif mutation == "missing":
        del changed["files"]["workflow.fabro"]
    elif mutation == "extra":
        changed["files"]["extra.txt"] = "undeclared"
    elif mutation == "traversal":
        changed["files"]["../escape"] = "bad"
    else:
        changed["files"]["WORKFLOW.FABRO"] = "collision"
    with pytest.raises(InputError):
        validate_package(changed, inputs.compiler_profile)


def test_failed_compile_preserves_prior_output(tmp_path: Path) -> None:
    request, output = prepare_case(tmp_path)
    before = sentinel(output)
    inputs = load_compiler_inputs(request)
    inputs.mapping["rules"][0]["actions"][0]["budget"]["attempts"] = 0
    with pytest.raises(CompilerSemanticError):
        package = compile_package(inputs, native_validator=RecordingValidator())
        write_package(output, package, inputs)
    assert output.read_bytes() == before
