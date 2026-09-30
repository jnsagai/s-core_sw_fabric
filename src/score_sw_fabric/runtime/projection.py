"""Project a sealed 003 package into Fabro's distinct version wire form."""

from __future__ import annotations

import hashlib
import tomllib
import unicodedata
from pathlib import PurePosixPath
from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.package import validate_package
from score_sw_fabric.process_source.reader import InputError

MAX_VERSION_FILES = 512
MAX_VERSION_FILE_BYTES = 512 * 1024
MAX_VERSION_BYTES = 2 * 1024 * 1024


def _logical_path(raw: Any, pointer: str) -> str:
    if (
        not isinstance(raw, str)
        or not raw
        or "\\" in raw
        or "//" in raw
        or raw.startswith("~")
        or (len(raw) >= 2 and raw[0].isascii() and raw[0].isalpha() and raw[1] == ":")
        or any(ord(character) < 32 or ord(character) == 127 for character in raw)
        or len(raw.encode("utf-8")) > 240
        or len(raw.split("/")) > 16
        or any(part in {"", ".", ".."} for part in raw.split("/"))
        or PurePosixPath(raw).is_absolute()
    ):
        raise InputError("PACKAGE_PATH", f"Unsafe path at {pointer}", pointer)
    return raw


def project_version(package: dict[str, Any], compiler_profile: dict[str, Any]) -> dict[str, Any]:
    """Return a closed native version and a separate binding to its 003 source."""
    validate_package(package, compiler_profile)
    if package["semantic_validation"]["valid"] is not True:
        raise InputError("PACKAGE_INVALID", "003 semantic validation is not complete")
    if package["native_validation"]["accepted"] is not True:
        raise InputError("PACKAGE_INVALID", "003 native validation is not accepted")
    files = package["files"]
    native_receipt = package["native_validation"]
    if native_receipt["source_set_digest"] != hashlib.sha256(canonical(files)).hexdigest():
        raise InputError("NATIVE_RECEIPT_STALE", "003 native validation covers different files")
    validator = native_receipt.get("validator")
    if (
        not isinstance(validator, dict)
        or validator.get("source_commit") != package["manifest"]["validator"]["source_commit"]
    ):
        raise InputError("VALIDATOR_IDENTITY", "003 native validator identity differs")
    if len(files) > MAX_VERSION_FILES:
        raise InputError("WIRE_LIMIT_EXCEEDED", "Fabro file count exceeds 512")
    config_name = _logical_path(package["entrypoint"], "/entrypoint")
    try:
        config = tomllib.loads(files[config_name])
    except (KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise InputError("PACKAGE_CONFIG", "Invalid 003 workflow configuration") from exc
    if (
        set(config) != {"_version", "workflow"}
        or type(config["_version"]) is not int
        or config["_version"] != 1
    ):
        raise InputError("PACKAGE_CONFIG", "Unsupported 003 workflow configuration")
    workflow = config["workflow"]
    if not isinstance(workflow, dict) or set(workflow) != {"graph"}:
        raise InputError("PACKAGE_CONFIG", "003 workflow graph reference is ambiguous")
    graph = _logical_path(workflow["graph"], "/files/workflow.toml/workflow/graph")
    if graph != "workflow.fabro" or graph not in files:
        raise InputError("PACKAGE_CONFIG", "003 graph entrypoint is not declared")
    native_files: dict[str, str] = {}
    folded: set[str] = set()
    for raw, content in files.items():
        path = _logical_path(raw, f"/files/{raw}")
        folded_path = unicodedata.normalize("NFC", path).casefold()
        if folded_path in folded:
            raise InputError("PACKAGE_CASE_COLLISION", "Case-colliding native file path")
        folded.add(folded_path)
        if not isinstance(content, str):
            raise InputError("PACKAGE_CONTENT", "Fabro version files must be UTF-8 text")
        if len(content.encode("utf-8")) > MAX_VERSION_FILE_BYTES:
            raise InputError("WIRE_LIMIT_EXCEEDED", f"Fabro file exceeds 512 KiB: {path}")
        native_files[path] = content
    for path in sorted(folded):
        if any(path.startswith(other + "/") for other in folded if other != path):
            raise InputError("PACKAGE_PATH_COLLISION", "Native file shadows a directory")
    if len(package["manifest"]["ir"].get("child_workflows", [])):
        raise InputError("CHILD_WORKFLOW_UNSUPPORTED", "Child workflow closure is not supported")
    wire = {
        "entrypoint": graph,
        "files": dict(sorted(native_files.items())),
        "workflow_dependencies": {},
    }
    # Fabro hashes serde_json::to_vec(WorkflowVersion), which has no trailing newline.
    wire_bytes = canonical(wire).removesuffix(b"\n")
    if len(wire_bytes) > MAX_VERSION_BYTES:
        raise InputError("WIRE_LIMIT_EXCEEDED", "Fabro canonical version exceeds 2 MiB")
    return {
        "source_package_digest": package["digest"],
        "source_entrypoint": config_name,
        "wire_entrypoint": graph,
        "wire": wire,
        "wire_digest": hashlib.sha256(wire_bytes).hexdigest(),
        "wire_bytes": len(wire_bytes),
    }
