"""Isolated native validation and exact fresh-export receipts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from score_sw_fabric.artifacts.models import enforce_limit
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.reader import verify_self_digest
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml
from score_sw_fabric.storage import temporary_directory

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _bounded_output(
    result: subprocess.CompletedProcess[str], limit: int, consumed: int = 0
) -> tuple[str, str, int]:
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    size = len(stdout.encode()) + len(stderr.encode())
    enforce_limit(
        {"native_output_bytes": limit},
        "native_output_bytes",
        consumed + size,
        "NATIVE_OUTPUT_LIMIT",
        "Native validator output exceeded its limit",
    )
    return stdout, stderr, consumed + size


def _load_build_profile(path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    try:
        value = read_json(path) if path.suffix == ".json" else read_yaml(path)
    except OSError as exc:
        raise InputError("NATIVE_PROFILE", str(exc)) from exc
    verify_self_digest(value, "/native_build_profile")
    expected = profile.get("native_validator", {}).get("profile")
    if value.get("id") != expected:
        raise InputError(
            "NATIVE_PROFILE_MISMATCH",
            "Artifact and native-build profiles do not identify the same validator",
        )
    return value


def _verify_binary(binary: Path, build_profile: dict[str, Any]) -> str:
    actual_sha = hashlib.sha256(binary.read_bytes()).hexdigest()
    expected_sha = build_profile.get("bazel", {}).get("sha256")
    if expected_sha is not None and actual_sha != expected_sha:
        raise InputError("NATIVE_TOOL_MISMATCH", "Native validator executable hash differs")
    return actual_sha


def _verify_lock(root: Path, build_profile: dict[str, Any]) -> None:
    lock = build_profile.get("lock_file")
    if lock is None:
        return
    if not isinstance(lock, dict) or set(lock) != {"path", "sha256"}:
        raise InputError("NATIVE_PROFILE", "Invalid native dependency lock declaration")
    candidate = root / str(lock["path"])
    if not candidate.is_file() or candidate.is_symlink():
        raise InputError("NATIVE_LOCK_DRIFT", "Pinned native dependency lock is unavailable")
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != lock["sha256"]:
        raise InputError("NATIVE_LOCK_DRIFT", "Pinned native dependency lock differs")


def _fixture_export(files: dict[str, str], profile: dict[str, Any]) -> dict[str, Any]:
    from score_sw_fabric.artifacts.rst import scan_rst

    needs: list[dict[str, Any]] = []
    supported = set(profile["directives"])
    for path, content in sorted(files.items()):
        scanned = scan_rst(path, content, supported)
        for item in scanned["directives"]:
            needs.append(
                {
                    "id": item["native_id"],
                    "type": item["name"],
                    "title": item["title"],
                    "content": item["content"].strip(),
                    "status": item["option_values"].get("status"),
                    "version": item["native_version"],
                    "options": dict(sorted(item["option_values"].items())),
                    "path": path,
                    "line": item["start_line"],
                }
            )
    return {"schema_version": 1, "needs": needs}


def validate_native(
    files: dict[str, str],
    profile: dict[str, Any],
    local_paths: dict[str, Any],
    *,
    runner: Runner = subprocess.run,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate in a disposable tree; fixture emulation remains visibly fixture-only."""

    limits = profile["limits"]
    source_digest = hashlib.sha256(canonical(files)).hexdigest()
    started = time.monotonic()
    fixture_mode = local_paths.get("fixture_native") is True
    if fixture_mode:
        fixture_export = _fixture_export(files, profile)
        receipt = {
            "validator": {"id": "fixture-native-adapter", "fixture_only": True},
            "source_set_digest": source_digest,
            "commands": ["fixture-needs-json", "fixture-docs-check"],
            "exit_classes": [0, 0],
            "elapsed_milliseconds": int((time.monotonic() - started) * 1000),
            "export_digest": hashlib.sha256(canonical(fixture_export)).hexdigest(),
            "log_digest": hashlib.sha256(b"fixture-native-adapter\n").hexdigest(),
            "accepted": True,
            "cleanup": "complete",
            "limitations": [
                "Fixture-only native adapter; production Bazel validation is not claimed."
            ],
        }
        return receipt, fixture_export

    raw_binary = local_paths.get("bazel") or os.environ.get("SCORE_BAZEL_BIN")
    if not isinstance(raw_binary, str) or not raw_binary:
        raise InputError("NATIVE_UNAVAILABLE", "SCORE_BAZEL_BIN or local_paths.bazel is required")
    try:
        binary = Path(raw_binary).resolve(strict=True)
    except OSError as exc:
        raise InputError("NATIVE_UNAVAILABLE", str(exc)) from exc
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise InputError("NATIVE_UNAVAILABLE", f"Native validator is not executable: {binary}")
    build_profile_path = local_paths.get("build_profile")
    if not isinstance(build_profile_path, str):
        raise InputError("NATIVE_PROFILE", "A pinned build_profile path is required")
    build_profile = _load_build_profile(Path(build_profile_path), profile)
    binary_sha256 = _verify_binary(binary, build_profile)
    commands = profile["native_validator"].get("argv")
    if commands is None:
        commands = list(build_profile["commands"].values())
    if not isinstance(commands, list) or len(commands) != 2:
        raise InputError("NATIVE_PROFILE", "Exactly two fixed native commands are required")
    stdout_parts: list[str] = []
    exit_classes: list[int] = []
    export: dict[str, Any] | None = None
    output_bytes = 0
    with temporary_directory(prefix="score-artifact-native-") as raw_root:
        root = Path(raw_root)
        source = local_paths.get("native_consumer")
        if isinstance(source, str):
            shutil.copytree(
                Path(source),
                root,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(
                    ".git",
                    ".home",
                    ".cache",
                    "_build",
                    "bazel-*",
                    "ubproject.toml",
                ),
            )
        _verify_lock(root, build_profile)
        for logical, content in sorted(files.items()):
            target = root / logical
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="")
        home = root / ".home"
        cache = root / ".cache"
        home.mkdir()
        cache.mkdir()
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(home),
            "XDG_CACHE_HOME": str(cache),
            "TMPDIR": str(root),
            "BAZELISK_HOME": str(cache / "bazelisk"),
            "TEST_TMPDIR": str(cache / "bazel"),
            "NO_COLOR": "1",
        }
        timeout = limits["native_timeout_seconds"]
        export_path = local_paths.get("native_export_result")
        if not isinstance(export_path, str):
            raise InputError("NATIVE_EXPORT_MISSING", "A native_export_result path is required")
        candidate = root / export_path
        if candidate.exists():
            if candidate.is_dir() or candidate.is_symlink():
                raise InputError("NATIVE_EXPORT_STALE", "Declared native export is unsafe")
            candidate.unlink()
        for raw_command in commands:
            if not isinstance(raw_command, list) or any(
                not isinstance(arg, str) for arg in raw_command
            ):
                raise InputError("NATIVE_PROFILE", "Native command argv must be a string array")
            try:
                result = runner(
                    [str(binary), *raw_command],
                    cwd=root,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=timeout,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise InputError("NATIVE_UNAVAILABLE", str(exc)) from exc
            stdout, stderr, output_bytes = _bounded_output(
                result, limits["native_output_bytes"], output_bytes
            )
            stdout_parts.extend([stdout, stderr])
            exit_classes.append(result.returncode)
            if result.returncode != 0:
                from score_sw_fabric.artifacts.models import ArtifactSemanticError

                detail = (stderr or stdout).strip()[-4000:]
                message = "Pinned native documentation validation failed"
                if detail:
                    message += f": {detail}"
                raise ArtifactSemanticError("NATIVE_REJECTED", message)
        try:
            export = json.loads(candidate.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise InputError(
                "NATIVE_EXPORT_MISSING", "Native validation did not produce the declared export"
            ) from exc
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InputError("NATIVE_EXPORT_INVALID", str(exc)) from exc
    if export is None:
        raise InputError(
            "NATIVE_EXPORT_MISSING", "Native validation did not produce the declared export"
        )
    log = "".join(stdout_parts).encode()
    receipt = {
        "validator": {
            "id": profile["native_validator"]["profile"],
            "profile_digest": build_profile["digest"],
            "executable_sha256": binary_sha256,
            "fixture_only": False,
        },
        "source_set_digest": source_digest,
        "commands": ["needs_json", "docs_check"],
        "exit_classes": exit_classes,
        "elapsed_milliseconds": int((time.monotonic() - started) * 1000),
        "export_digest": hashlib.sha256(canonical(export)).hexdigest(),
        "log_digest": hashlib.sha256(log).hexdigest(),
        "accepted": True,
        "cleanup": "complete",
        "limitations": [],
    }
    return receipt, export
