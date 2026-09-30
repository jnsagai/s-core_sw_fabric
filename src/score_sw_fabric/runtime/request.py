"""Exact version-1 runtime operation requests with confined, digest-bound local inputs."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric.assurance.models import exact, nonempty, sha, stable_id, version
from score_sw_fabric.process_source.reader import (
    InputError,
    _pairs,
    _reject_constant,
    _UniqueSafeLoader,
    read_bytes,
)
from score_sw_fabric.runtime.models import validate_baseline, validate_intent

REQUEST_FIELDS = {
    "runtime_commit",
    "intent",
    "package",
    "compiler_profile",
    "runtime_profile",
    "candidate",
    "credential_file",
    "ledger_root",
    "target",
    "baseline_now",
    "evidence",
    "effects",
    "subject",
    "protected_roots",
}
MAX_REQUEST_BYTES = 1024 * 1024
MAX_CREDENTIAL_BYTES = 4096


def parse_json(data: bytes, pointer: str) -> Any:
    try:
        return json.loads(data, object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError("INVALID_JSON", f"Invalid JSON at {pointer}", pointer) from exc


def parse_yaml(data: bytes, pointer: str) -> Any:
    try:
        return yaml.load(data, Loader=_UniqueSafeLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise InputError("INVALID_YAML", f"Invalid YAML at {pointer}", pointer) from exc


def _no_links(path: Path, pointer: str) -> Path:
    selected = path.absolute()
    # Read-only inputs are digest-bound, so matching hard links are accepted; outputs,
    # ledger records and the credential file check link counts where they are opened.
    for item in (selected, *selected.parents):
        if item.is_symlink():
            raise InputError("INPUT_ALIAS", f"Symbolic path at {pointer}", pointer)
    return selected


def _local(base: Path, raw: Any, pointer: str) -> Path:
    text = nonempty(raw, pointer, max_length=1024)
    candidate = Path(text)
    if ".." in candidate.parts or "\x00" in text:
        raise InputError("INPUT_PATH", f"Unsafe path at {pointer}", pointer)
    return _no_links(candidate if candidate.is_absolute() else base / candidate, pointer)


def _file(base: Path, value: Any, pointer: str) -> tuple[Path, bytes]:
    record = exact(value, {"path", "sha256"}, pointer)
    path = _local(base, record["path"], pointer + "/path")
    data = read_bytes(path)
    if hashlib.sha256(data).hexdigest() != sha(record["sha256"], pointer + "/sha256"):
        raise InputError("PACKAGE_DRIFT", f"Input bytes changed at {pointer}", pointer)
    return path, data


def protected_credential(path: Path) -> Callable[[], str]:
    """Read a disposable token from an owner-only regular file at request time."""

    def provider() -> str:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            details = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(details.st_mode)
                or details.st_mode & 0o077
                or details.st_uid != os.getuid()
                or details.st_nlink != 1
            ):
                raise InputError("RUNTIME_AUTH_UNAVAILABLE", "Credential file is not protected")
            data = stream.read(MAX_CREDENTIAL_BYTES + 1)
        if len(data) > MAX_CREDENTIAL_BYTES:
            raise InputError("RUNTIME_AUTH_UNAVAILABLE", "Credential file is too large")
        return data.decode("ascii").strip()

    return provider


@dataclass(frozen=True)
class RuntimeRequest:
    path: Path
    runtime_commit: str
    intent: dict[str, Any]
    intent_path: Path
    package: dict[str, Any]
    package_path: Path
    package_bytes: bytes
    compiler_profile: dict[str, Any]
    compiler_profile_path: Path
    compiler_profile_bytes: bytes
    runtime_profile: dict[str, Any]
    runtime_profile_path: Path
    executable: Path
    source_api: Path
    credential: Callable[[], str]
    credential_path: Path
    ledger_root: Path
    target: Path
    disposable_root: Path
    environment_id: str
    baseline_now: dict[str, Any] | None
    evidence: list[tuple[Path, bytes, Path, bytes]]
    effects: list[dict[str, Any]]
    subject: dict[str, Any] | None
    protected_roots: list[Path]

    def inputs(self) -> list[Path]:
        paths = [
            self.path,
            self.intent_path,
            self.package_path,
            self.compiler_profile_path,
            self.runtime_profile_path,
            self.credential_path,
            self.executable,
            self.source_api,
        ]
        for assessment, _, context, _ in self.evidence:
            paths.extend([assessment, context])
        return paths


def load_request(path: Path) -> RuntimeRequest:
    selected = _no_links(path, "/request")
    data = read_bytes(selected)
    if len(data) > MAX_REQUEST_BYTES:
        raise InputError("LIMIT_EXCEEDED", "Runtime request exceeds 1 MiB")
    raw = parse_yaml(data, "/runtime_request")
    record = version(raw, "runtime_request", REQUEST_FIELDS, "/runtime_request")
    base = selected.parent
    commit = record["runtime_commit"]
    if not isinstance(commit, str) or len(commit) != 40 or set(commit) - set("0123456789abcdef"):
        raise InputError("HASH_FORMAT", "Expected full runtime commit", "/runtime_commit")
    intent_path, intent_bytes = _file(base, record["intent"], "/intent")
    intent = validate_intent(parse_json(intent_bytes, "/intent"))
    package_path, package_bytes = _file(base, record["package"], "/package")
    package = parse_json(package_bytes, "/package")
    if (
        intent["package_ref"]["sha256"] != hashlib.sha256(package_bytes).hexdigest()
        or not isinstance(package, dict)
        or intent["package_ref"]["semantic_digest"] != package.get("digest")
    ):
        raise InputError("PACKAGE_DRIFT", "Intent does not bind the selected package")
    profile_path, profile_bytes = _file(base, record["compiler_profile"], "/compiler_profile")
    compiler_profile = parse_yaml(profile_bytes, "/compiler_profile")
    if not isinstance(compiler_profile, dict):
        raise InputError("YAML_ROOT", "Compiler profile must be a mapping")
    runtime_path, runtime_bytes = _file(base, record["runtime_profile"], "/runtime_profile")
    runtime_profile = parse_json(runtime_bytes, "/runtime_profile")
    if (
        intent["runtime_profile_ref"]["sha256"] != hashlib.sha256(runtime_bytes).hexdigest()
        or not isinstance(runtime_profile, dict)
        or intent["runtime_profile_ref"]["semantic_digest"] != runtime_profile.get("digest")
    ):
        raise InputError("RUNTIME_IDENTITY_MISMATCH", "Intent does not bind the runtime profile")
    candidate = exact(record["candidate"], {"executable", "source_api"}, "/candidate")
    target = exact(record["target"], {"path", "disposable_root", "environment_id"}, "/target")
    if target["environment_id"] != intent["start_args"]["target_id"]:
        raise InputError("RUNTIME_TARGET", "Target differs from the intent start arguments")
    baseline = record["baseline_now"]
    evidence = []
    raw_evidence = record["evidence"]
    if not isinstance(raw_evidence, list) or len(raw_evidence) > 100:
        raise InputError("LIMIT_EXCEEDED", "Too many evidence selections", "/evidence")
    for index, item in enumerate(raw_evidence):
        pointer = f"/evidence/{index}"
        pair = exact(item, {"assessment", "trust_context"}, pointer)
        assessment_path, assessment_bytes = _file(base, pair["assessment"], pointer + "/assessment")
        context_path, context_bytes = _file(base, pair["trust_context"], pointer + "/trust_context")
        evidence.append((assessment_path, assessment_bytes, context_path, context_bytes))
    effects = record["effects"]
    if not isinstance(effects, list):
        raise InputError("FIELD_TYPE", "Effects must be a list", "/effects")
    subject = None
    if record["subject"] is not None:
        _, subject_bytes = _file(base, record["subject"], "/subject")
        subject = parse_json(subject_bytes, "/subject")
    roots = record["protected_roots"]
    if not isinstance(roots, list) or len(roots) > 100:
        raise InputError("LIMIT_EXCEEDED", "Too many protected roots", "/protected_roots")
    credential_path = _local(base, record["credential_file"], "/credential_file")
    stable_id(intent["intent_id"], "/intent/intent_id")
    return RuntimeRequest(
        path=selected,
        runtime_commit=commit,
        intent=intent,
        intent_path=intent_path,
        package=package,
        package_path=package_path,
        package_bytes=package_bytes,
        compiler_profile=compiler_profile,
        compiler_profile_path=profile_path,
        compiler_profile_bytes=profile_bytes,
        runtime_profile=runtime_profile,
        runtime_profile_path=runtime_path,
        executable=_local(base, candidate["executable"], "/candidate/executable"),
        source_api=_local(base, candidate["source_api"], "/candidate/source_api"),
        credential=protected_credential(credential_path),
        credential_path=credential_path,
        ledger_root=_local(base, record["ledger_root"], "/ledger_root"),
        target=_local(base, target["path"], "/target/path"),
        disposable_root=_local(base, target["disposable_root"], "/target/disposable_root"),
        environment_id=nonempty(target["environment_id"], "/target/environment_id", max_length=128),
        baseline_now=None if baseline is None else validate_baseline(baseline, "/baseline_now"),
        evidence=evidence,
        effects=effects,
        subject=subject if isinstance(subject, dict) or subject is None else {},
        protected_roots=[
            _local(base, item, f"/protected_roots/{index}") for index, item in enumerate(roots)
        ],
    )
