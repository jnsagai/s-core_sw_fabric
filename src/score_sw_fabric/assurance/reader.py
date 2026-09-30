"""Duplicate-safe bounded input loading and guarded output paths."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from score_sw_fabric.assurance.models import (
    MAX_CONTROL_BYTES,
    MAX_DEPTH,
    MAX_REFERENCES,
    bounded_list,
    domain,
    exact,
    instant,
    scope,
    sha,
    verify_digest,
)
from score_sw_fabric.compiler.reader import semantic_digest, verify_self_digest
from score_sw_fabric.process_source.reader import (
    InputError,
    _json_compatible,
    _pairs,
    _reject_constant,
    _UniqueSafeLoader,
    read_bytes,
    read_json,
    read_yaml,
)

REQUEST_FIELDS = {
    "schema_version",
    "operation",
    "assurance_domain",
    "scope",
    "inputs",
    "local_paths",
    "output_root",
    "as_of",
}
REF_FIELDS = {"path", "sha256", "semantic_digest"}


def _depth(value: Any, level: int = 0) -> None:
    if level > MAX_DEPTH:
        raise InputError("LIMIT_EXCEEDED", "Reference nesting exceeds 32 levels")
    if isinstance(value, dict):
        for item in value.values():
            _depth(item, level + 1)
    elif isinstance(value, list):
        for item in value:
            _depth(item, level + 1)


def safe_path(raw: Any, pointer: str) -> PurePosixPath:
    if (
        not isinstance(raw, str)
        or not raw
        or "\\" in raw
        or "//" in raw
        or raw.startswith("./")
        or ":" in raw.split("/")[0]
    ):
        raise InputError("PATH_ESCAPE", f"Unsafe path at {pointer}", pointer)
    logical = PurePosixPath(raw)
    if logical.is_absolute() or any(part in {"", ".", ".."} for part in raw.split("/")):
        raise InputError("PATH_ESCAPE", f"Unsafe path at {pointer}", pointer)
    return logical


def _no_symlink_ancestors(path: Path, stop: Path) -> None:
    candidate = path
    while candidate != stop and candidate.is_relative_to(stop):
        if candidate.is_symlink():
            raise InputError("SYMLINK_ESCAPE", f"Symlink path is unsupported: {candidate}")
        candidate = candidate.parent


def resolve_file(base: Path, raw: Any, pointer: str) -> Path:
    logical = safe_path(raw, pointer)
    selected: set[Path] = set()
    for anchor in (base, Path.cwd()):
        candidate = anchor.joinpath(*logical.parts)
        _no_symlink_ancestors(candidate, anchor)
        if candidate.is_file():
            resolved = candidate.resolve()
            if not resolved.is_relative_to(anchor.resolve()):
                raise InputError("PATH_ESCAPE", f"Input escapes anchor at {pointer}", pointer)
            if candidate.stat().st_nlink != 1:
                raise InputError("INPUT_ALIAS", f"Hardlinked input at {pointer}", pointer)
            selected.add(resolved)
    if len(selected) > 1:
        raise InputError("INPUT_ALIAS", f"Ambiguous input at {pointer}: {raw}", pointer)
    if selected:
        return next(iter(selected))
    raise InputError("INPUT_UNAVAILABLE", f"Missing input at {pointer}: {raw}", pointer)


def resolve_directory(base: Path, raw: Any, pointer: str) -> Path:
    logical = safe_path(raw, pointer)
    selected: set[Path] = set()
    for anchor in (base, Path.cwd()):
        candidate = anchor.joinpath(*logical.parts)
        _no_symlink_ancestors(candidate, anchor)
        if candidate.is_dir():
            resolved = candidate.resolve()
            if not resolved.is_relative_to(anchor.resolve()):
                raise InputError("PATH_ESCAPE", f"Directory escapes anchor at {pointer}", pointer)
            selected.add(resolved)
    if len(selected) != 1:
        raise InputError(
            "INPUT_UNAVAILABLE", f"Directory absent or ambiguous at {pointer}", pointer
        )
    return next(iter(selected))


def _parse_selected_bytes(data: bytes, suffix: str, pointer: str) -> dict[str, Any]:
    try:
        if suffix == ".json":
            result = json.loads(data, object_pairs_hook=_pairs, parse_constant=_reject_constant)
        elif suffix in {".yaml", ".yml"}:
            result = yaml.load(data, Loader=_UniqueSafeLoader)
            _json_compatible(result, set())
        else:
            raise InputError("FIELD_UNKNOWN", f"Unsupported input suffix at {pointer}", pointer)
    except (UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise InputError(
            "INPUT_PARSE", f"Invalid selected input at {pointer}: {exc}", pointer
        ) from exc
    except (RecursionError, OverflowError) as exc:
        raise InputError(
            "LIMIT_EXCEEDED", f"Input nesting exceeds limit at {pointer}", pointer
        ) from exc
    if not isinstance(result, dict):
        raise InputError("FIELD_TYPE", f"Expected input object at {pointer}", pointer)
    return result


def read_reference(base: Path, raw: Any, pointer: str) -> tuple[Path, dict[str, Any]]:
    ref = exact(raw, REF_FIELDS, pointer)
    path = resolve_file(base, ref["path"], pointer + "/path")
    data = read_bytes(path)
    if len(data) > MAX_CONTROL_BYTES:
        raise InputError("LIMIT_EXCEEDED", f"Input too large at {pointer}", pointer)
    if hashlib.sha256(data).hexdigest() != sha(ref["sha256"], pointer + "/sha256"):
        raise InputError("HASH_MISMATCH", f"Transport hash mismatch at {pointer}", pointer)
    value = _parse_selected_bytes(data, path.suffix, pointer)
    _depth(value)
    kind = value.get("kind")
    if "kind" in value and not isinstance(kind, str):
        raise InputError("FIELD_TYPE", f"Invalid kind at {pointer}", pointer)
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise InputError("VERSION_UNSUPPORTED", f"Unsupported version at {pointer}", pointer)
    if kind == "signed_receipt":
        selected = verify_digest(value, pointer, field="receipt_digest")["receipt_digest"]
    elif isinstance(kind, str) and kind.startswith("assurance_"):
        selected = verify_digest(value, pointer)["digest"]
    elif "digest" in value:
        selected = verify_self_digest(value, pointer)
    else:
        selected = semantic_digest(value)
    if selected != sha(ref["semantic_digest"], pointer + "/semantic_digest"):
        raise InputError("SELECTED_DIGEST", f"Semantic digest mismatch at {pointer}", pointer)
    return path, value


def read_request(path: Path, operation: str) -> dict[str, Any]:
    if path.is_symlink() or (path.exists() and path.stat().st_nlink != 1):
        raise InputError("INPUT_ALIAS", "Request path cannot be a symlink or hardlink")
    if path.suffix not in {".json", ".yaml", ".yml"}:
        raise InputError("FIELD_UNKNOWN", "Unsupported assurance request suffix")
    try:
        request = read_json(path) if path.suffix == ".json" else read_yaml(path)
    except (RecursionError, OverflowError) as exc:
        raise InputError("LIMIT_EXCEEDED", "Assurance request nesting exceeds limit") from exc
    fields = REQUEST_FIELDS | ({"gate_mode"} if operation == "gate" else set())
    exact(request, fields, "/")
    _depth(request)
    if operation == "gate" and request["gate_mode"] not in {
        "normal",
        "not_started",
        "reuse_prior",
        "whole_gate_not_applicable",
    }:
        raise InputError("FIELD_UNKNOWN", "Unknown gate mode")
    if type(request["schema_version"]) is not int or request["schema_version"] != 1:
        raise InputError("VERSION_UNSUPPORTED", "Unsupported assurance request version")
    if request["operation"] != operation:
        raise InputError("OPERATION_MISMATCH", f"Expected {operation} request")
    domain(request["assurance_domain"], "/assurance_domain")
    scope(request["scope"], "/scope")
    instant(request["as_of"], "/as_of")
    if not isinstance(request["inputs"], dict) or len(request["inputs"]) > MAX_REFERENCES:
        raise InputError("LIMIT_EXCEEDED", "Invalid assurance input set")
    local_fields = {"protected_roots"}
    if operation in {"evidence", "gate"}:
        local_fields.add("raw_root")
    local = exact(request["local_paths"], local_fields, "/local_paths")
    roots = bounded_list(local["protected_roots"], MAX_REFERENCES, "/local_paths/protected_roots")
    for index, raw in enumerate(roots):
        resolve_directory(path.parent, raw, f"/local_paths/protected_roots/{index}")
    if "raw_root" in local:
        resolve_directory(path.parent, local["raw_root"], "/local_paths/raw_root")
    safe_path(request["output_root"], "/output_root")
    return request


def load_inputs(
    request_path: Path, request: dict[str, Any], names: set[str]
) -> tuple[dict[str, dict[str, Any]], list[Path]]:
    inputs = exact(request["inputs"], names, "/inputs")
    values: dict[str, dict[str, Any]] = {}
    paths: list[Path] = [request_path.resolve()]
    for name in sorted(inputs):
        raw = inputs[name]
        if raw is None:
            continue
        if isinstance(raw, list):
            bounded_list(raw, MAX_REFERENCES, f"/inputs/{name}")
            for index, item in enumerate(raw):
                path, value = read_reference(request_path.parent, item, f"/inputs/{name}/{index}")
                paths.append(path)
                values[f"{name}/{index}"] = value
        else:
            path, value = read_reference(request_path.parent, raw, f"/inputs/{name}")
            paths.append(path)
            values[name] = value
    if len(paths) != len(set(paths)):
        raise InputError("INPUT_ALIAS", "The same physical input is selected more than once")
    folded: dict[str, Path] = {}
    for selected in paths:
        key = str(selected).casefold()
        if key in folded and folded[key] != selected:
            raise InputError("INPUT_ALIAS", "Case-variant input paths are ambiguous")
        folded[key] = selected
    return values, paths


def output_path(request_path: Path, request: dict[str, Any], out: Path, inputs: list[Path]) -> Path:
    logical = safe_path(request["output_root"], "/output_root")
    root_candidate = Path.cwd().joinpath(*logical.parts)
    _no_symlink_ancestors(root_candidate, Path.cwd())
    root = root_candidate.resolve()
    destination = out.absolute()
    _no_symlink_ancestors(destination, root)
    if not destination.parent.resolve().is_relative_to(root):
        raise InputError("OUTPUT_PATH", "Output must be beneath declared output_root")
    if destination.is_symlink():
        raise InputError("OUTPUT_SYMLINK", "Output may not be a symlink")
    for source in inputs:
        if destination.resolve() == source or (
            destination.exists() and os.path.samefile(destination, source)
        ):
            raise InputError("OUTPUT_ALIAS", "Output aliases an input")
    protected_roots = list(request["local_paths"].get("protected_roots", []))
    if "raw_root" in request["local_paths"]:
        protected_roots.append(request["local_paths"]["raw_root"])
    for raw in protected_roots:
        protected = resolve_directory(request_path.parent, raw, "/local_paths/protected_roots")
        if destination.resolve().is_relative_to(protected):
            raise InputError("OUTPUT_SOURCE_ROOT", "Output overlaps a protected root")
    return destination
