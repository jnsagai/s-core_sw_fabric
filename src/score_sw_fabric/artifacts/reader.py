"""Bounded duplicate-safe artifact request and immutable snapshot loading."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
from typing import Any

from score_sw_fabric.artifacts.models import (
    DEFAULT_LIMITS,
    ArtifactInputs,
    ArtifactSemanticError,
    enforce_limit,
)
from score_sw_fabric.compiler.package import validate_package as validate_workflow_package
from score_sw_fabric.compiler.reader import verify_self_digest
from score_sw_fabric.process_source.reader import InputError, read_bytes, read_json, read_yaml

REQUEST_FIELDS = {
    "schema_version",
    "operation",
    "target_snapshot",
    "artifact_profile",
    "trace_profile",
    "plan",
    "workflow_package",
    "operations",
    "local_paths",
    "output_root",
}
REFERENCE_FIELDS = {"path", "sha256", "semantic_digest"}
SHA = set("0123456789abcdef")


def exact(value: Any, fields: set[str], pointer: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        actual = set(value) if isinstance(value, dict) else set()
        raise InputError(
            "ARTIFACT_FIELDS",
            f"{pointer}: unexpected={sorted(actual - fields)}, missing={sorted(fields - actual)}",
            pointer,
        )
    return value


def require_version(value: dict[str, Any], pointer: str) -> None:
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise InputError("ARTIFACT_VERSION", f"Supported schema_version is 1 at {pointer}")


def require_sha(value: Any, pointer: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in SHA for char in value):
        raise InputError("SHA256_FORMAT", f"Invalid SHA-256 at {pointer}", pointer)
    return value


def safe_logical_path(raw: str, pointer: str = "") -> PurePosixPath:
    path = PurePosixPath(raw)
    if (
        not raw
        or "\\" in raw
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise InputError("PATH_ESCAPE", f"Unsafe relative path at {pointer}: {raw}", pointer)
    return path


def _existing_file(base: Path, raw: Any, pointer: str) -> Path:
    if not isinstance(raw, str):
        raise InputError("FIELD_TYPE", f"Expected path string at {pointer}", pointer)
    logical = safe_logical_path(raw, pointer)
    candidates = (base.joinpath(*logical.parts), Path.cwd().joinpath(*logical.parts))
    for candidate in candidates:
        if candidate.is_symlink():
            raise InputError("SYMLINK_ESCAPE", f"Symlink input at {pointer}", pointer)
        if candidate.is_file():
            return candidate.resolve()
    raise InputError("INPUT_UNAVAILABLE", f"Missing input at {pointer}: {raw}", pointer)


def _directory(base: Path, raw: Any, pointer: str, *, must_exist: bool = True) -> Path:
    if not isinstance(raw, str):
        raise InputError("FIELD_TYPE", f"Expected directory string at {pointer}", pointer)
    logical = safe_logical_path(raw, pointer)
    candidates = (base.joinpath(*logical.parts), Path.cwd().joinpath(*logical.parts))
    selected = next((item for item in candidates if item.exists()), candidates[0])
    if selected.is_symlink() or (must_exist and not selected.is_dir()):
        raise InputError("INPUT_UNAVAILABLE", f"Unavailable directory at {pointer}: {raw}")
    return selected.resolve()


def _load_reference(base: Path, raw: Any, name: str) -> tuple[Path, dict[str, Any], str]:
    ref = exact(raw, REFERENCE_FIELDS, f"/{name}")
    path = _existing_file(base, ref["path"], f"/{name}/path")
    enforce_limit(
        DEFAULT_LIMITS,
        "control_bytes",
        path.stat().st_size,
        "CONTROL_SIZE_LIMIT",
        f"Control input exceeds limit: {name}",
    )
    actual_transport = hashlib.sha256(read_bytes(path)).hexdigest()
    if actual_transport != require_sha(ref["sha256"], f"/{name}/sha256"):
        raise InputError("HASH_MISMATCH", f"Transport hash mismatch for {name}")
    value = read_json(path) if path.suffix == ".json" else read_yaml(path)
    require_version(value, f"/{name}")
    actual_semantic = verify_self_digest(value, f"/{name}")
    if actual_semantic != require_sha(ref["semantic_digest"], f"/{name}/semantic_digest"):
        raise InputError("SELECTED_DIGEST", f"Semantic digest mismatch for {name}")
    return path, value, actual_semantic


def _validate_limits(profile: dict[str, Any]) -> dict[str, int]:
    limits = profile.get("limits")
    if not isinstance(limits, dict) or set(limits) != set(DEFAULT_LIMITS):
        raise InputError("ARTIFACT_LIMITS", "Artifact profile must declare every version-1 limit")
    result: dict[str, int] = {}
    for key, ceiling in DEFAULT_LIMITS.items():
        value = limits.get(key)
        if type(value) is not int or value < 1 or value > ceiling:
            raise InputError("ARTIFACT_LIMITS", f"Invalid or unsupported limit {key}")
        result[key] = value
    return result


def _validate_snapshot(snapshot: dict[str, Any], root: Path, limits: dict[str, int]) -> None:
    fields = {
        "schema_version",
        "target_namespace",
        "snapshot_id",
        "source",
        "configuration",
        "files",
        "external_exports",
        "build_closure",
        "digest",
    }
    exact(snapshot, fields, "/target_snapshot")
    files = snapshot["files"]
    if not isinstance(files, list):
        raise InputError("TARGET_FILE_LIMIT", "Target snapshot files must be an array")
    enforce_limit(
        limits,
        "files",
        len(files),
        "TARGET_FILE_LIMIT",
        "Target snapshot file limit exceeded",
    )
    seen: set[str] = set()
    folded: set[str] = set()
    inode_keys: set[tuple[int, int]] = set()
    total = 0
    for index, record in enumerate(files):
        pointer = f"/target_snapshot/files/{index}"
        if not isinstance(record, dict) or set(record) != {
            "path",
            "bytes",
            "sha256",
            "media_kind",
            "semantic_role",
            "executable",
        }:
            raise InputError("SNAPSHOT_FILE_FIELDS", f"Invalid file record at {pointer}")
        logical = safe_logical_path(record["path"], pointer + "/path")
        name = logical.as_posix()
        if name in seen or name.casefold() in folded:
            raise InputError("SNAPSHOT_PATH_COLLISION", f"Duplicate or case-colliding path: {name}")
        seen.add(name)
        folded.add(name.casefold())
        path = root.joinpath(*logical.parts)
        if path.is_symlink() or not path.is_file():
            raise InputError("SNAPSHOT_FILE", f"Missing, symlinked, or non-regular file: {name}")
        stat = path.stat()
        inode = (stat.st_dev, stat.st_ino)
        if inode in inode_keys or stat.st_nlink != 1:
            raise InputError("SNAPSHOT_ALIAS", f"Multiply linked snapshot file: {name}")
        inode_keys.add(inode)
        data = read_bytes(path)
        if record["media_kind"] == "text/rst":
            enforce_limit(
                limits,
                "text_file_bytes",
                len(data),
                "TARGET_TEXT_LIMIT",
                f"Managed text file exceeds limit: {name}",
            )
        if type(record["bytes"]) is not int or record["bytes"] != len(data):
            raise InputError("SNAPSHOT_SIZE", f"Snapshot byte count mismatch: {name}")
        if record["sha256"] != hashlib.sha256(data).hexdigest():
            raise InputError("HASH_MISMATCH", f"Snapshot hash mismatch: {name}")
        if record["media_kind"] == "text/rst":
            try:
                data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise InputError("RST_ENCODING", f"Managed RST is not UTF-8: {name}") from exc
        total += len(data)
    enforce_limit(
        limits,
        "target_bytes",
        total,
        "TARGET_SIZE_LIMIT",
        "Declared target content exceeds limit",
    )
    closure = snapshot["build_closure"]
    if not isinstance(closure, dict) or sorted(closure.get("files", [])) != sorted(seen):
        raise InputError("SNAPSHOT_CLOSURE", "Build closure must name every declared file exactly")


def read_snapshot_files(inputs: ArtifactInputs) -> dict[str, str]:
    files: dict[str, str] = {}
    for record in inputs.snapshot["files"]:
        if record["media_kind"] != "text/rst":
            continue
        logical = safe_logical_path(record["path"])
        files[logical.as_posix()] = inputs.snapshot_root.joinpath(*logical.parts).read_text(
            encoding="utf-8"
        )
    return files


def load_artifact_inputs(path: Path) -> ArtifactInputs:
    try:
        request_path = path.resolve(strict=True)
    except OSError as exc:
        raise InputError("INPUT_UNAVAILABLE", str(exc)) from exc
    enforce_limit(
        DEFAULT_LIMITS,
        "control_bytes",
        request_path.stat().st_size,
        "CONTROL_SIZE_LIMIT",
        "Artifact request exceeds control-input limit",
    )
    request = exact(read_yaml(request_path), REQUEST_FIELDS, "/")
    require_version(request, "/")
    operation = request["operation"]
    if operation not in {"index", "candidate", "trace"}:
        raise InputError("ARTIFACT_OPERATION", f"Unsupported operation: {operation}")
    base = request_path.parent
    selected: dict[str, dict[str, Any] | None] = {}
    paths: list[Path] = [request_path]
    digests: dict[str, str] = {}
    required = {"target_snapshot", "artifact_profile"}
    if operation in {"candidate", "trace"}:
        required |= {"plan", "workflow_package"}
    if operation == "trace":
        required.add("trace_profile")
    for name in (
        "target_snapshot",
        "artifact_profile",
        "trace_profile",
        "plan",
        "workflow_package",
    ):
        raw = request[name]
        if raw is None:
            if name in required:
                raise InputError("MISSING_OPERATION_INPUT", f"{operation} requires {name}")
            selected[name] = None
            continue
        selected_path, value, selected_digest = _load_reference(base, raw, name)
        paths.append(selected_path)
        selected[name] = value
        digests[name] = selected_digest
    snapshot = selected["target_snapshot"]
    profile = selected["artifact_profile"]
    assert snapshot is not None and profile is not None
    limits = _validate_limits(profile)
    for selected_path in paths:
        enforce_limit(
            limits,
            "control_bytes",
            selected_path.stat().st_size,
            "CONTROL_SIZE_LIMIT",
            f"Control input exceeds selected profile limit: {selected_path.name}",
        )
    local = request["local_paths"]
    if (
        not isinstance(local, dict)
        or "snapshot_root" not in local
        or "protected_roots" not in local
    ):
        raise InputError("LOCAL_PATHS", "local_paths requires snapshot_root and protected_roots")
    snapshot_root = _directory(base, local["snapshot_root"], "/local_paths/snapshot_root")
    output_root = _directory(base, request["output_root"], "/output_root", must_exist=False)
    raw_protected = local["protected_roots"]
    if not isinstance(raw_protected, list):
        raise InputError("LOCAL_PATHS", "protected_roots must be an array")
    protected = tuple(
        _directory(base, item, f"/local_paths/protected_roots/{i}")
        for i, item in enumerate(raw_protected)
    )
    if any(output_root == root or output_root.is_relative_to(root) for root in protected):
        raise InputError("OUTPUT_SOURCE_ROOT", "Output root overlaps a protected root")
    _validate_snapshot(snapshot, snapshot_root, limits)
    review = profile.get("review")
    fixture_ok = (
        isinstance(review, dict)
        and isinstance(review.get("fixture_override"), dict)
        and review["fixture_override"].get("state") == "reviewed"
        and str(snapshot["target_namespace"]).startswith("fixture-")
    )
    if not isinstance(review, dict) or (review.get("state") != "reviewed" and not fixture_ok):
        raise ArtifactSemanticError(
            "PROFILE_UNREVIEWED", "Artifact profile is not reviewed for this target"
        )
    operations = request["operations"]
    if not isinstance(operations, list):
        raise InputError("EDIT_LIMIT", "Edit operations must be an array")
    enforce_limit(
        limits,
        "edits",
        len(operations),
        "EDIT_LIMIT",
        "Invalid or excessive edit operations",
    )
    if operation == "index" and operations:
        raise InputError("INDEX_EDITS", "Index requests cannot carry edit operations")
    if operation == "candidate" and not operations:
        raise InputError("CANDIDATE_EDITS", "Candidate requests require edit operations")
    plan = selected["plan"]
    package = selected["workflow_package"]
    if plan is not None:
        if plan.get("planning_status") != "complete" or plan.get("closure_complete") is not True:
            raise ArtifactSemanticError("PLAN_BLOCKED", "Only a complete sealed plan is supported")
    if package is not None:
        validate_workflow_package(package, {})
        plan_digest = package.get("manifest", {}).get("inputs", {}).get("plan")
        if plan is not None and plan_digest != plan.get("digest"):
            raise InputError(
                "PLAN_PACKAGE_BINDING", "Workflow package does not bind the selected plan"
            )
    trace_profile = selected["trace_profile"]
    if trace_profile is not None:
        review = trace_profile.get("review")
        fixture_ok = (
            isinstance(review, dict)
            and isinstance(review.get("fixture_override"), dict)
            and review["fixture_override"].get("state") == "reviewed"
            and str(snapshot["target_namespace"]).startswith("fixture-")
        )
        if not isinstance(review, dict) or (review.get("state") != "reviewed" and not fixture_ok):
            raise ArtifactSemanticError(
                "TRACE_PROFILE_UNREVIEWED", "Trace profile is not reviewed for this target"
            )
    folded = [str(item).casefold() for item in paths]
    if len(folded) != len(set(folded)):
        raise InputError("INPUT_CASE_COLLISION", "Selected inputs collide by case")
    for i, left in enumerate(paths):
        for right in paths[i + 1 :]:
            if os.path.samefile(left, right):
                raise InputError("INPUT_ALIAS", "Selected inputs alias the same file")
    return ArtifactInputs(
        request_path=request_path,
        request=request,
        operation=operation,
        snapshot=snapshot,
        artifact_profile=profile,
        trace_profile=trace_profile,
        plan=plan,
        workflow_package=package,
        semantic_digests=digests,
        input_paths=tuple(paths),
        snapshot_root=snapshot_root,
        output_root=output_root,
        protected_roots=protected,
        local_paths=local,
    )
