from __future__ import annotations

import json
from pathlib import Path

from score_sw_fabric.cli import main
from score_sw_fabric.compiler.package import compile_package, write_package
from score_sw_fabric.compiler.reader import load_compiler_inputs
from tests.compiler_support import RecordingValidator, prepare_case, sentinel


def _published(root: Path) -> tuple[Path, Path, Path]:
    request, output = prepare_case(root)
    inputs = load_compiler_inputs(request)
    package = compile_package(inputs, native_validator=RecordingValidator())
    write_package(output, package, inputs)
    profile = root / "compiler_profile.yaml"
    return request, output, profile


def test_diff_and_drift_public_commands_have_exact_exit_classes(
    tmp_path: Path, capsys: object
) -> None:
    _, package, profile = _published(tmp_path)
    assert (
        main(
            [
                "workflow",
                "diff",
                "--before",
                str(package),
                "--after",
                str(package),
                "--profile",
                str(profile),
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(["workflow", "drift", "--package", str(package), "--profile", str(profile), "--json"])
        == 0
    )
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert '"equivalent": true' in output
    assert '"clean": true' in output


def test_malformed_compile_request_is_exit_2_and_preserves_output(
    tmp_path: Path, capsys: object
) -> None:
    request, output = prepare_case(tmp_path)
    before = sentinel(output)
    request.write_text("schema_version: nope\n")
    assert (
        main(["workflow", "compile", "--request", str(request), "--out", str(output), "--json"])
        == 2
    )
    error = json.loads(capsys.readouterr().err)  # type: ignore[attr-defined]
    assert error["code"] == "COMPILER_FIELDS"
    assert output.read_bytes() == before
