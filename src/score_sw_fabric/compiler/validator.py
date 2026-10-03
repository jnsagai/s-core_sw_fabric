"""Isolated native Fabro validator invocation with pinned identity checks."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.models import CompilerSemanticError
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.storage import temporary_directory

Runner = Callable[..., subprocess.CompletedProcess[str]]
MAX_VALIDATOR_OUTPUT = 1024 * 1024


def _executable(profile: dict[str, Any], override: Path | None) -> Path:
    raw = str(override) if override is not None else os.environ.get("SCORE_FABRO_BIN", "")
    if not raw:
        raise InputError("VALIDATOR_UNAVAILABLE", "SCORE_FABRO_BIN is not set")
    try:
        path = Path(raw).resolve(strict=True)
    except OSError as exc:
        raise InputError("VALIDATOR_UNAVAILABLE", str(exc)) from exc
    if not path.is_file() or not os.access(path, os.X_OK):
        raise InputError("VALIDATOR_UNAVAILABLE", f"Validator is not executable: {path}")
    allowed_sha = profile.get("executable_sha256")
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if allowed_sha is not None and allowed_sha != actual_sha:
        raise InputError("VALIDATOR_IDENTITY", "Validator executable digest does not match profile")
    return path


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int,
    runner: Runner,
) -> subprocess.CompletedProcess[str]:
    try:
        return runner(
            command,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InputError("VALIDATOR_UNAVAILABLE", str(exc)) from exc


def _json_output(result: subprocess.CompletedProcess[str], code: str) -> dict[str, Any]:
    if len(result.stdout.encode()) + len(result.stderr.encode()) > MAX_VALIDATOR_OUTPUT:
        raise InputError("VALIDATOR_OUTPUT_LIMIT", "Validator output exceeds 1 MiB")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InputError(code, f"Validator returned malformed JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError(code, "Validator JSON result must be an object")
    return value


def validate_native(
    files: dict[str, str],
    entrypoint: str,
    profile: dict[str, Any],
    *,
    executable: Path | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Materialize and validate a declared source set without registration or execution."""

    binary = _executable(profile, executable)
    expected_commit = profile.get("source_commit")
    timeout = profile.get("timeout_seconds", 30)
    if type(timeout) is not int or timeout < 1 or timeout > 300:
        raise InputError("VALIDATOR_PROFILE", "Invalid validator timeout")
    clean_env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": "",
        "FABRO_NO_UPGRADE_CHECK": "true",
        "NO_COLOR": "1",
    }
    with temporary_directory(prefix="score-fabro-validate-") as raw_root:
        root = Path(raw_root)
        home = root / "home"
        home.mkdir()
        clean_env["HOME"] = str(home)
        clean_env["TMPDIR"] = str(root)
        for logical, content in sorted(files.items()):
            path = PurePosixPath(logical)
            if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
                raise InputError("PACKAGE_PATH", f"Unsafe package path: {logical}")
            target = root.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
        version_result = _run(
            [str(binary), "--json", "version"],
            cwd=root,
            env=clean_env,
            timeout=timeout,
            runner=runner,
        )
        if version_result.returncode != 0:
            raise InputError("VALIDATOR_UNAVAILABLE", "Validator version probe failed")
        version = _json_output(version_result, "VALIDATOR_IDENTITY")
        client = version.get("client")
        reported_commit = client.get("git_sha") if isinstance(client, dict) else None
        if (
            not isinstance(reported_commit, str)
            or len(reported_commit) < 7
            or not isinstance(expected_commit, str)
            or not expected_commit.startswith(reported_commit)
        ):
            raise InputError("VALIDATOR_IDENTITY", "Validator Git identity does not match profile")
        assert isinstance(client, dict)
        target = root.joinpath(*PurePosixPath(entrypoint).parts)
        result = _run(
            [str(binary), "--json", "validate", str(target)],
            cwd=root,
            env=clean_env,
            timeout=timeout,
            runner=runner,
        )
        payload = _json_output(result, "VALIDATOR_RESULT")
        if result.returncode < 0 or (result.returncode != 0 and "valid" not in payload):
            raise InputError("VALIDATOR_UNAVAILABLE", "Validator process failed")
        accepted = result.returncode == 0 and payload.get("valid") is True
        diagnostics = payload.get("diagnostics", [])
        if isinstance(diagnostics, list):
            diagnostics = [dict(item) for item in diagnostics if isinstance(item, dict)]
            for diagnostic in diagnostics:
                source_path = diagnostic.get("source_path")
                if isinstance(source_path, str):
                    diagnostic["source_path"] = PurePosixPath(source_path).name
        receipt = {
            "validator": {
                "source_commit": expected_commit,
                "executable_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                "version": client.get("version"),
                "profile": client.get("profile"),
            },
            "source_set_digest": hashlib.sha256(canonical(files)).hexdigest(),
            "workflow_name": payload.get("workflow_name"),
            "nodes": payload.get("nodes"),
            "edges": payload.get("edges"),
            "diagnostics": diagnostics,
            "accepted": accepted,
        }
        if not accepted:
            raise CompilerSemanticError(
                "NATIVE_REJECTED", "Selected native validator rejected the generated package"
            )
        return receipt
