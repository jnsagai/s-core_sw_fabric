from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from score_sw_fabric.artifacts.index import build_index
from score_sw_fabric.artifacts.models import ArtifactSemanticError
from score_sw_fabric.artifacts.native import _fixture_export, validate_native
from score_sw_fabric.artifacts.reader import load_artifact_inputs, read_snapshot_files
from score_sw_fabric.compiler.reader import semantic_digest
from score_sw_fabric.process_source.reader import InputError
from tests.artifact_support import prepare_artifact_case, snapshot


def test_fixture_native_boundary_is_explicit_and_bounded(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path)
    inputs = load_artifact_inputs(request)
    receipt, export = validate_native(
        read_snapshot_files(inputs), inputs.artifact_profile, inputs.local_paths
    )
    assert receipt["accepted"] is True
    assert receipt["validator"]["fixture_only"] is True
    assert export["needs"]
    assert all("/tmp/" not in str(value) for value in receipt.values())


def _real_boundary(tmp_path: Path) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    request, _ = prepare_artifact_case(tmp_path / "case")
    inputs = load_artifact_inputs(request)
    files = read_snapshot_files(inputs)
    profile = copy.deepcopy(inputs.artifact_profile)
    profile["native_validator"].pop("argv", None)
    profile["limits"]["native_output_bytes"] = 128
    profile["limits"]["native_timeout_seconds"] = 7
    profile["digest"] = semantic_digest(profile)

    binary = tmp_path / "bazel"
    binary.write_bytes(b"pinned-test-validator")
    binary.chmod(0o755)
    build_profile = {
        "schema_version": 1,
        "id": profile["native_validator"]["profile"],
        "version": 1,
        "commands": {
            "needs_json": ["--batch", "build", "//:needs_json"],
            "docs_check": ["--batch", "run", "//:docs_check"],
        },
    }
    build_profile["digest"] = semantic_digest(build_profile)
    build_profile_path = tmp_path / "build-profile.yaml"
    build_profile_path.write_text(yaml.safe_dump(build_profile, sort_keys=False))
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    local = {
        "bazel": str(binary),
        "build_profile": str(build_profile_path),
        "native_consumer": str(consumer),
        "native_export_result": "needs.json",
    }
    return files, profile, local


def _success_runner(files: dict[str, str], profile: dict[str, Any], calls: list[dict[str, Any]]):
    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"argv": argv, **kwargs})
        if len(calls) == 2:
            export = _fixture_export(files, profile)
            (Path(kwargs["cwd"]) / "needs.json").write_text(json.dumps(export))
        return subprocess.CompletedProcess(argv, 0, "ok", "")

    return run


def test_real_boundary_uses_fixed_argv_isolated_environment_and_cleans_up(
    tmp_path: Path,
) -> None:
    files, profile, local = _real_boundary(tmp_path)
    calls: list[dict[str, Any]] = []
    receipt, export = validate_native(
        files, profile, local, runner=_success_runner(files, profile, calls)
    )
    roots = {Path(call["cwd"]) for call in calls}
    assert len(roots) == 1
    assert all(not root.exists() for root in roots)
    assert [call["argv"][1:] for call in calls] == [
        ["--batch", "build", "//:needs_json"],
        ["--batch", "run", "//:docs_check"],
    ]
    assert all("shell" not in call for call in calls)
    assert all(call["timeout"] == 7 for call in calls)
    assert all(set(call["env"]) == {"PATH", "HOME", "XDG_CACHE_HOME", "NO_COLOR"} for call in calls)
    assert all(str(call["cwd"]) not in json.dumps(receipt) for call in calls)
    assert receipt["validator"]["profile_digest"]
    assert receipt["validator"]["executable_sha256"]
    assert receipt["cleanup"] == "complete"
    assert export["needs"]


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("missing-binary", "NATIVE_UNAVAILABLE"),
        ("profile-mismatch", "NATIVE_PROFILE_MISMATCH"),
        ("tool-mismatch", "NATIVE_TOOL_MISMATCH"),
        ("lock-drift", "NATIVE_LOCK_DRIFT"),
    ],
)
def test_native_identity_failures_are_closed(tmp_path: Path, mutation: str, code: str) -> None:
    files, profile, local = _real_boundary(tmp_path)
    build_path = Path(local["build_profile"])
    build = yaml.safe_load(build_path.read_text())
    if mutation == "missing-binary":
        local["bazel"] = str(tmp_path / "absent")
    elif mutation == "profile-mismatch":
        build["id"] = "another-profile"
    elif mutation == "tool-mismatch":
        build["bazel"] = {"sha256": "0" * 64}
    else:
        build["lock_file"] = {"path": "MODULE.bazel.lock", "sha256": "0" * 64}
        (Path(local["native_consumer"]) / "MODULE.bazel.lock").write_text("drift")
    if mutation != "missing-binary":
        build["digest"] = semantic_digest(build)
        build_path.write_text(yaml.safe_dump(build, sort_keys=False))
    with pytest.raises(InputError) as caught:
        validate_native(files, profile, local)
    assert caught.value.code == code


@pytest.mark.parametrize(
    ("mode", "code", "error_type"),
    [
        ("timeout", "NATIVE_UNAVAILABLE", InputError),
        ("output", "NATIVE_OUTPUT_LIMIT", InputError),
        ("reject", "NATIVE_REJECTED", ArtifactSemanticError),
        ("missing-export", "NATIVE_EXPORT_MISSING", InputError),
        ("invalid-export", "NATIVE_EXPORT_INVALID", InputError),
    ],
)
def test_native_execution_failures_are_stable_and_cleanup(
    tmp_path: Path, mode: str, code: str, error_type: type[Exception]
) -> None:
    files, profile, local = _real_boundary(tmp_path)
    stale = Path(local["native_consumer"]) / "needs.json"
    stale.write_text('{"stale": true}')
    roots: list[Path] = []
    count = 0

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal count
        count += 1
        root = Path(kwargs["cwd"])
        roots.append(root)
        assert not (root / "needs.json").exists()
        if mode == "timeout":
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if mode == "output":
            return subprocess.CompletedProcess(argv, 0, "x" * 129, "")
        if mode == "reject":
            return subprocess.CompletedProcess(argv, 9, "", "rejected")
        if count == 2 and mode == "invalid-export":
            (root / "needs.json").write_text("{")
        return subprocess.CompletedProcess(argv, 0, "", "")

    with pytest.raises(error_type) as caught:
        validate_native(files, profile, local, runner=runner)
    assert caught.value.code == code
    assert roots and all(not root.exists() for root in roots)


def test_output_limit_is_cumulative_across_commands(tmp_path: Path) -> None:
    files, profile, local = _real_boundary(tmp_path)
    profile["limits"]["native_output_bytes"] = 7
    profile["digest"] = semantic_digest(profile)
    calls = 0

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        if calls == 2:
            (Path(kwargs["cwd"]) / "needs.json").write_text('{"needs": []}')
        return subprocess.CompletedProcess(argv, 0, "1234", "")

    with pytest.raises(InputError) as caught:
        validate_native(files, profile, local, runner=runner)
    assert caught.value.code == "NATIVE_OUTPUT_LIMIT"


def test_command_injection_shaped_content_is_copied_as_data(tmp_path: Path) -> None:
    files, profile, local = _real_boundary(tmp_path)
    marker = tmp_path / "executed"
    logical = next(iter(files))
    files[logical] += f"\n$(touch {marker})\n; touch {marker}\n"
    calls: list[dict[str, Any]] = []

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(kwargs)
        copied = (Path(kwargs["cwd"]) / logical).read_text()
        assert "$(touch" in copied and "; touch" in copied
        if len(calls) == 2:
            (Path(kwargs["cwd"]) / "needs.json").write_text(
                json.dumps(_fixture_export(files, profile))
            )
        return subprocess.CompletedProcess(argv, 0, "", "")

    validate_native(files, profile, local, runner=runner)
    assert not marker.exists()


def test_source_export_mismatch_is_rejected_by_index(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path)
    inputs = load_artifact_inputs(request)
    files = read_snapshot_files(inputs)
    export = _fixture_export(files, inputs.artifact_profile)
    export["needs"][0]["title"] = "stale title"
    index = build_index(
        files,
        inputs.snapshot,
        inputs.artifact_profile,
        export,
        {"accepted": True},
    )
    assert index["valid"] is False
    assert any(item["code"] == "SOURCE_EXPORT_MISMATCH" for item in index["findings"])


def test_failure_does_not_change_protected_source_or_prior_output(tmp_path: Path) -> None:
    request, output = prepare_artifact_case(tmp_path)
    output.write_bytes(b"prior-output")
    source_before = snapshot(tmp_path / "target")
    request_value = yaml.safe_load(request.read_text())
    request_value["local_paths"] = {
        "snapshot_root": "target",
        "protected_roots": ["target"],
        "bazel": "absent-bazel",
        "build_profile": "absent-profile.yaml",
        "native_export_result": "needs.json",
    }
    request.write_text(yaml.safe_dump(request_value, sort_keys=False))
    from score_sw_fabric.artifacts.package import index_request

    with pytest.raises(InputError):
        index_request(request, output)
    assert output.read_bytes() == b"prior-output"
    assert snapshot(tmp_path / "target") == source_before
