"""Packaged scripts execute exact bytes; missing bindings never become no-op checks."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.ir import build_ir
from score_sw_fabric.compiler.mapping import project_mapping
from score_sw_fabric.compiler.models import CompilerSemanticError
from score_sw_fabric.compiler.package import compile_package, validate_package
from score_sw_fabric.compiler.reader import load_compiler_inputs, semantic_digest
from score_sw_fabric.compiler.render import render_native
from score_sw_fabric.process_source.reader import InputError
from tests.compiler_support import RecordingValidator, compiler_profile, mapping, plan, prepare_case


def bound_case(script: str = "printf 'measured\\n'\nexit 7\n") -> dict[str, Any]:
    selected = mapping()
    action = selected["rules"][0]["actions"][0]
    action["command_file"] = "commands/check.sh"
    action["support_files"] = ["commands/check.sh"]
    selected["support_files"] = [
        {"path": "commands/check.sh", "content": script, "origin": action["origin"]}
    ]
    return selected


def graph_for(selected: dict[str, Any]) -> dict[str, Any]:
    profile = compiler_profile()
    return build_ir(project_mapping(plan(), selected, profile), selected, profile)


def test_bound_script_executes_and_preserves_nonzero_exit(tmp_path: Path) -> None:
    selected = bound_case()
    graph = graph_for(selected)
    assert next(n for n in graph["nodes"] if n["ref"] == "prepare")["command_file"] == (
        "commands/check.sh"
    )
    files = render_native(graph, selected["support_files"])
    line = next(line for line in files["workflow.fabro"].splitlines() if 'label="Prepare"' in line)
    # Decode the native DOT string, then execute it independently of renderer internals.
    native_script = json.JSONDecoder().raw_decode(line.split("script=", 1)[1])[0]
    result = subprocess.run(
        ["/bin/sh", "-c", native_script], cwd=tmp_path, capture_output=True, check=False
    )
    assert result.returncode == 7
    assert result.stdout == b"measured\n"
    assert result.stderr == b""
    assert files["commands/check.sh"] == native_script


@pytest.mark.parametrize(
    "path", ["../check.sh", "/check.sh", "./check.sh", "commands//check.sh", ".", "", 7, None]
)
def test_unsafe_or_invalid_binding_refused(path: Any) -> None:
    selected = bound_case()
    selected["rules"][0]["actions"][0]["command_file"] = path
    with pytest.raises((InputError, CompilerSemanticError)):
        graph_for(selected)


def test_binding_must_be_declared_by_the_action() -> None:
    selected = bound_case()
    selected["rules"][0]["actions"][0]["support_files"] = []
    with pytest.raises(CompilerSemanticError, match="support"):
        graph_for(selected)


def test_missing_packaged_script_refused_instead_of_noop() -> None:
    graph = graph_for(bound_case())
    with pytest.raises(CompilerSemanticError, match="script"):
        render_native(graph, [])


@pytest.mark.parametrize("script", ["", "  \n", "exit 0\x00exit 7"])
def test_empty_or_nul_script_refused(script: str) -> None:
    selected = bound_case(script)
    with pytest.raises((InputError, CompilerSemanticError)):
        render_native(graph_for(selected), selected["support_files"])


def test_binding_on_noncommand_refused() -> None:
    selected = bound_case()
    selected["rules"][0]["actions"][0]["type"] = "human"
    with pytest.raises(CompilerSemanticError, match="command"):
        graph_for(selected)


def test_ir_binding_tampering_refused() -> None:
    selected = bound_case()
    graph = graph_for(selected)
    node = next(n for n in graph["nodes"] if n["ref"] == "prepare")
    node["command_file"] = "commands/other.sh"
    with pytest.raises(CompilerSemanticError):
        render_native(graph, selected["support_files"])


def test_script_content_changes_native_render_and_normalizes_newlines() -> None:
    selected = bound_case("printf 'first'\r\nexit 0\r\n")
    graph = graph_for(selected)
    first = render_native(graph, selected["support_files"])
    assert first["commands/check.sh"] == "printf 'first'\nexit 0\n"
    selected["support_files"][0]["content"] = "printf 'second'\nexit 3\n"
    second = render_native(graph, selected["support_files"])
    assert first["workflow.fabro"] != second["workflow.fabro"]


def test_resealed_ir_cannot_select_a_different_script(tmp_path: Path) -> None:
    request, _ = prepare_case(tmp_path)
    selected = bound_case()
    action = selected["rules"][0]["actions"][0]
    action["support_files"].append("commands/other.sh")
    selected["support_files"].append(
        {"path": "commands/other.sh", "content": "exit 0\n", "origin": action["origin"]}
    )
    inputs = replace(load_compiler_inputs(request), mapping=selected)
    package = compile_package(inputs, native_validator=RecordingValidator())
    assert validate_package(package, inputs.compiler_profile)["valid"] is True
    graph = package["manifest"]["ir"]
    node = next(n for n in graph["nodes"] if n["ref"] == "prepare")
    node["command_file"] = "commands/other.sh"
    package["manifest"]["ir_digest"] = hashlib.sha256(canonical(graph)).hexdigest()
    package["digest"] = semantic_digest(package)
    with pytest.raises(InputError, match="binding"):
        validate_package(package, inputs.compiler_profile)
