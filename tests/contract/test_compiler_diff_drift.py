from __future__ import annotations

import copy
from pathlib import Path

from score_sw_fabric.compiler.diff import compare_packages
from score_sw_fabric.compiler.drift import inspect_drift
from score_sw_fabric.compiler.package import compile_package
from score_sw_fabric.compiler.reader import load_compiler_inputs, semantic_digest
from tests.compiler_support import RecordingValidator, prepare_case


def test_equivalent_packages_have_no_semantic_diff(tmp_path: Path) -> None:
    request, _ = prepare_case(tmp_path)
    inputs = load_compiler_inputs(request)
    first = compile_package(inputs, native_validator=RecordingValidator())
    second = compile_package(inputs, native_validator=RecordingValidator())
    result = compare_packages(first, second, inputs.compiler_profile)
    assert result["equivalent"] is True
    assert not result["changes"]


def test_generated_file_change_is_classified_after_resealing(tmp_path: Path) -> None:
    request, _ = prepare_case(tmp_path)
    inputs = load_compiler_inputs(request)
    first = compile_package(inputs, native_validator=RecordingValidator())
    inputs.mapping["support_files"] = [
        {
            "path": "policy/note.txt",
            "content": "reviewed note\n",
            "origin": inputs.mapping["rules"][0]["actions"][0]["origin"],
        }
    ]
    inputs.mapping["digest"] = semantic_digest(inputs.mapping)
    second = compile_package(inputs, native_validator=RecordingValidator())
    result = compare_packages(first, second, inputs.compiler_profile)
    assert any(item["category"] == "generated_file" for item in result["changes"])


def test_drift_is_read_only_and_reports_integrity_damage(tmp_path: Path) -> None:
    request, _ = prepare_case(tmp_path)
    inputs = load_compiler_inputs(request)
    package = compile_package(inputs, native_validator=RecordingValidator())
    damaged = copy.deepcopy(package)
    damaged["files"]["workflow.fabro"] += "// direct edit\n"
    before = copy.deepcopy(damaged)
    result = inspect_drift(damaged, inputs.compiler_profile)
    assert result["integrity"] == "invalid"
    assert result["clean"] is False
    assert damaged == before
