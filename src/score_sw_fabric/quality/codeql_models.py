"""Strict, bounded controls for unexecuted CodeQL prerequisite inspection."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import local_dir, relative_path
from score_sw_fabric.assurance.models import bounded_list, exact, nonempty, sha, stable_id, version
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.import_models import bounded_tree, native_root
from score_sw_fabric.quality.profile import load_toolchain
from score_sw_fabric.runtime.request import _local, parse_yaml

MAX_CONTROL = 1024 * 1024
FIELDS = {
    "id",
    "status",
    "source_lock",
    "source_root",
    "build_source_root",
    "compiled_pack_root",
    "suite",
    "scan_config",
    "report_patch",
    "native_sources",
    "reporting_toolchain",
    "eligibility",
}


def parse_control(data: bytes, pointer: str) -> Any:
    try:
        parsed = parse_yaml(data, pointer)
    except RecursionError as exc:
        raise InputError("LIMIT_EXCEEDED", "Native control nesting exceeds its bound") from exc
    bounded_tree(parsed)
    return parsed


def read_control(path: Path, pointer: str) -> bytes:
    selected = _local(path.parent, str(path.absolute()), pointer)
    try:
        if not selected.is_file():
            raise InputError("INPUT_NOT_FILE", "Selected control must be regular", pointer)
        if selected.stat().st_size > MAX_CONTROL:
            raise InputError("LIMIT_EXCEEDED", "Control exceeds 1 MiB", pointer)
        with selected.open("rb") as stream:
            data = stream.read(MAX_CONTROL + 1)
        if len(data) > MAX_CONTROL:
            raise InputError("LIMIT_EXCEEDED", "Control grew past 1 MiB", pointer)
        return data
    except OSError as exc:
        raise InputError("INPUT_UNAVAILABLE", "Cannot read selected control", pointer) from exc


def selection(base: Path, value: Any, pointer: str) -> tuple[Path, bytes]:
    ref = exact(value, {"path", "sha256"}, pointer)
    path = _local(base, ref["path"], pointer + "/path")
    data = read_control(path, pointer)
    if hashlib.sha256(data).hexdigest() != sha(ref["sha256"], pointer + "/sha256"):
        raise InputError("INPUT_DRIFT", "Selected control differs from its hash", pointer)
    return path, data


def request(path: Path, kind: str, fields: set[str]) -> tuple[dict[str, Any], Path]:
    selected = _local(path.parent, str(path.absolute()), "/request")
    return version(
        parse_control(read_control(selected, "/request"), "/request"), kind, fields, "/request"
    ), selected.parent


def _root(base: Path, raw: Any, pointer: str, *, optional: bool = False) -> str | None:
    if optional and raw is None:
        return None
    text = nonempty(raw, pointer, max_length=1024)
    if not text.startswith("/") or any(ord(character) < 32 for character in text):
        raise InputError("INPUT_PATH", "Native inspection roots must be absolute", pointer)
    path = _local(base, text, pointer)
    if optional:
        if path.exists() and not path.is_dir():
            raise InputError("INPUT_NOT_DIRECTORY", "Native root must be a directory", pointer)
        return str(path)
    return str(local_dir(base, text, pointer))


def _locked(lock: Any, identifier: str) -> dict[str, Any]:
    if (
        not isinstance(lock, dict)
        or type(lock.get("schema_version")) is not int
        or lock["schema_version"] != 1
    ):
        raise InputError("SCHEMA_VERSION", "Source lock must be version 1")
    sources = lock.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 64:
        raise InputError("LIMIT_EXCEEDED", "Source lock entries must be bounded")
    found = [row for row in sources if isinstance(row, dict) and row.get("id") == identifier]
    if len(found) != 1:
        raise InputError("SOURCE_LOCK", "Exactly one selected native lock entry is required")
    row = found[0]
    if not isinstance(row.get("commit"), str) or not re.fullmatch(r"[a-f0-9]{40}", row["commit"]):
        raise InputError("HASH_FORMAT", "Source lock commit must be full")
    hashes = row.get("source_file_sha256")
    if not isinstance(hashes, dict) or len(hashes) > 500:
        raise InputError("SOURCE_LOCK", "Native source hashes must be bounded")
    if identifier == "codeql-coding-standards" and not {
        "LICENSE.md",
        "docs/user_manual.md",
        "supported_codeql_configs.json",
    }.issubset(hashes):
        raise InputError("SOURCE_LOCK", "Native lock omits required inspected controls")
    for path, digest in hashes.items():
        relative_path(path, "/source_lock/path")
        sha(digest, "/source_lock/sha256")
    return row


def reference(value: Any, pointer: str) -> dict[str, Any]:
    """Validate retained selection metadata without probing the original host."""
    ref = exact(value, {"path", "sha256"}, pointer)
    text = nonempty(ref["path"], pointer + "/path", max_length=1024)
    if ".." in Path(text).parts or "\x00" in text:
        raise InputError("INPUT_PATH", "Unsafe retained selection path", pointer)
    sha(ref["sha256"], pointer + "/sha256")
    return ref


def validate_configuration(value: Any) -> dict[str, Any]:
    """Pure shape validation shared by live selection and offline inspection replay."""
    c = version(value, "quality_codeql_configuration", FIELDS, "/config")
    stable_id(c["id"], "/config/id")
    nonempty(c["status"], "/config/status", max_length=64)
    native_root(c["source_root"])
    for key in ("build_source_root", "compiled_pack_root"):
        if c[key] is not None:
            native_root(c[key])
    suite = relative_path(c["suite"], "/suite")
    if not re.fullmatch(r"codeql-suites/[A-Za-z0-9][A-Za-z0-9_.-]*\.qls", suite):
        raise InputError("INPUT_PATH", "Select an explicit native suite path")
    for key in ("source_lock", "scan_config", "report_patch", "reporting_toolchain", "eligibility"):
        if c[key] is not None or key not in {"reporting_toolchain", "eligibility"}:
            reference(c[key], "/" + key)
    labels = set()
    for raw in bounded_list(c["native_sources"], 2, "/native_sources"):
        row = exact(
            raw,
            {"id", "repository", "commit", "path", "sha256", "native_status", "license", "notice"},
            "/native_sources",
        )
        label = stable_id(row["id"], "/native_sources/id")
        if label not in {"scan_config", "report_patch"} or label in labels:
            raise InputError(
                "NATIVE_POLICY_IDENTITY_MISMATCH", "Native input labels must be unique"
            )
        labels.add(label)
        for key in ("repository", "native_status", "license", "notice"):
            nonempty(row[key], "/native_sources/" + key, max_length=1024)
        if not isinstance(row["commit"], str) or not re.fullmatch(r"[a-f0-9]{40}", row["commit"]):
            raise InputError("HASH_FORMAT", "Native commit must be full")
        relative_path(row["path"], "/native_sources/path")
        sha(row["sha256"], "/native_sources/sha256")
    if len(labels) != 2:
        raise InputError(
            "NATIVE_POLICY_IDENTITY_MISMATCH", "Two native time descriptors are required"
        )
    return c


def configuration(data: bytes, base: Path) -> tuple[dict[str, Any], dict[str, bytes], list[Path]]:
    c = validate_configuration(parse_control(data, "/config"))
    for key in ("source_root", "build_source_root", "compiled_pack_root"):
        c[key] = _root(base, c[key], "/" + key, optional=key != "source_root")
    suite = relative_path(c["suite"], "/suite")
    if not re.fullmatch(r"codeql-suites/[A-Za-z0-9][A-Za-z0-9_.-]*\.qls", suite):
        raise InputError("INPUT_PATH", "Select an explicit native suite path")
    assets, paths = {}, []
    for key in ("source_lock", "scan_config", "report_patch", "reporting_toolchain", "eligibility"):
        if c[key] is not None:
            path, content = selection(base, c[key], "/" + key)
            assets[key] = content
            paths.append(path)
        elif key not in {"reporting_toolchain", "eligibility"}:
            raise InputError("FIELD_TYPE", "Mandatory native control cannot be null")
    lock = parse_control(assets["source_lock"], "/source_lock")
    source = _locked(lock, "codeql-coding-standards")
    time = _locked(lock, "time")
    if (
        source.get("repository") != "https://github.com/github/codeql-coding-standards"
        or time.get("repository") != "https://github.com/eclipse-score/time"
    ):
        raise InputError(
            "SOURCE_LOCK", "Native repository identity differs from the selected baseline"
        )
    descriptors = c["native_sources"]
    if not isinstance(descriptors, list) or len(descriptors) != 2:
        raise InputError(
            "NATIVE_POLICY_IDENTITY_MISMATCH", "Two native time descriptors are required"
        )
    labels = set()
    native_roots = []
    for raw in descriptors:
        row = exact(
            raw,
            {"id", "repository", "commit", "path", "sha256", "native_status", "license", "notice"},
            "/native_sources",
        )
        identifier = stable_id(row["id"], "/native_sources/id")
        if identifier not in {"scan_config", "report_patch"} or identifier in labels:
            raise InputError(
                "NATIVE_POLICY_IDENTITY_MISMATCH", "Native input labels must be unique"
            )
        labels.add(identifier)
        relative_path(row["path"], "/native_sources/path")
        expected_path = {
            "scan_config": "tools/static_analysis/config.yaml",
            "report_patch": "third_party/codeql/codeql_coding_standards_misra.patch",
        }[identifier]
        if row["path"] != expected_path:
            raise InputError(
                "NATIVE_POLICY_IDENTITY_MISMATCH", "Native path differs from inspected input"
            )
        for key in ("native_status", "license", "notice"):
            nonempty(row[key], "/native_sources/" + key, max_length=1024)
        if (
            row["repository"] != time["repository"]
            or row["commit"] != time["commit"]
            or row["sha256"] != c[identifier]["sha256"]
        ):
            raise InputError(
                "NATIVE_POLICY_IDENTITY_MISMATCH",
                "Native control does not bind the selected source lock",
            )
        sha(row["sha256"], "/native_sources/sha256")
        selected_path = _local(base, c[identifier]["path"], "/native_sources/path")
        native_parts = Path(row["path"]).parts
        if selected_path.parts[-len(native_parts) :] == native_parts:
            native_roots.append(str(selected_path.parents[len(native_parts) - 1]))
    reporting = None
    if c["reporting_toolchain"] is not None:
        reporting = load_toolchain(
            assets["reporting_toolchain"], "quality_codeql_reporting_toolchain_profile"
        )
        if not re.fullmatch(r"Python 3\.9\.[0-9]+", reporting["tool"]["version"]):
            raise InputError("REPORTING_UNSUPPORTED", "The native manual declares Python 3.9")
        paths.extend(Path(row["path"]) for row in [reporting["tool"], *reporting["dependencies"]])
    return (
        {
            "effective": c,
            "source": source,
            "time": time,
            "reporting": reporting,
            "native_roots": native_roots,
        },
        assets,
        paths,
    )
