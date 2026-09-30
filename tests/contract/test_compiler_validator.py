from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from score_sw_fabric.compiler.validator import validate_native
from score_sw_fabric.process_source.reader import InputError
from tests.compiler_support import validator_profile


def _binary(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)
    return path


def test_adapter_invokes_only_version_and_validate_in_disposable_tree(tmp_path: Path) -> None:
    commands: list[list[str]] = []
    roots: list[Path] = []

    def runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        commands.append(command)
        roots.append(Path(str(kwargs["cwd"])))
        payload = (
            {
                "client": {
                    "git_sha": validator_profile()["source_commit"],
                    "version": "fixture",
                    "profile": "test",
                }
            }
            if command[-1] == "version"
            else {
                "workflow_name": "Fixture",
                "nodes": 2,
                "edges": 1,
                "valid": True,
                "diagnostics": [],
            }
        )
        return CompletedProcess(command, 0, json.dumps(payload), "")

    receipt = validate_native(
        {
            "workflow.toml": '_version = 1\n[workflow]\ngraph = "workflow.fabro"\n',
            "workflow.fabro": (
                'digraph X { start [type="start"]; exit [type="exit"]; start -> exit; }\n'
            ),
        },
        "workflow.toml",
        validator_profile(),
        executable=_binary(tmp_path / "fabro"),
        runner=runner,
    )
    assert receipt["accepted"] is True
    assert [item[2] for item in commands] == ["version", "validate"]
    assert all(not root.exists() for root in roots)


def test_adapter_rejects_malformed_or_identity_mismatched_output(tmp_path: Path) -> None:
    def malformed(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(command, 0, "not-json", "")

    with pytest.raises(InputError) as caught:
        validate_native(
            {"workflow.toml": "x", "workflow.fabro": "x"},
            "workflow.toml",
            validator_profile(),
            executable=_binary(tmp_path / "fabro"),
            runner=malformed,
        )
    assert caught.value.code == "VALIDATOR_IDENTITY"
