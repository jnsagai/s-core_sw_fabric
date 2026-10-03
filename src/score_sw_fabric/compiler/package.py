"""Guarded compilation, package sealing, integrity checks, and publication."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.graph_validation import validate_graph
from score_sw_fabric.compiler.ir import build_ir
from score_sw_fabric.compiler.mapping import project_mapping
from score_sw_fabric.compiler.models import CompilerInputs, CompilerSemanticError
from score_sw_fabric.compiler.reader import load_compiler_inputs, semantic_digest
from score_sw_fabric.compiler.render import render_native
from score_sw_fabric.compiler.validator import validate_native
from score_sw_fabric.process_source.reader import InputError, read_json

NativeValidator = Callable[[dict[str, str], str, dict[str, Any]], dict[str, Any]]


def _safe_path(raw: str) -> PurePosixPath:
    path = PurePosixPath(raw)
    if (
        not raw
        or "\\" in raw
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise InputError("PACKAGE_PATH", f"Unsafe package path: {raw}")
    return path


def _origin_key(value: dict[str, Any]) -> bytes:
    return canonical(value)


def _source_map(
    graph: dict[str, Any], files: dict[str, str], mapping: dict[str, Any]
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for kind, values in (
        ("node", graph["nodes"]),
        ("edge", graph["edges"]),
        ("gate", graph["gates"]),
        ("loop", graph["loop_policies"]),
        ("fan_group", graph["fan_groups"]),
    ):
        for value in values:
            identifier = value.get("id") or value.get("node_id")
            origins = value.get("origins") or (
                [value["origin"]] if "origin" in value else graph["origins"]
            )
            entries.append(
                {
                    "kind": kind,
                    "id": identifier,
                    "output_file": "workflow.fabro"
                    if kind in {"node", "edge", "gate", "loop", "fan_group"}
                    else None,
                    "plan_instance_ids": sorted(
                        value.get("instance_ids", value.get("subjects", []))
                    ),
                    "origins": sorted(origins, key=_origin_key),
                    "content_binding": hashlib.sha256(canonical(value)).hexdigest(),
                }
            )
    file_origins = {
        item["path"]: [item["origin"]]
        for item in mapping["support_files"]
        if isinstance(item, dict) and "path" in item and "origin" in item
    }
    for path, content in files.items():
        entries.append(
            {
                "kind": "file",
                "id": path,
                "output_file": path,
                "plan_instance_ids": [],
                "origins": sorted(file_origins.get(path, graph["origins"]), key=_origin_key),
                "content_binding": hashlib.sha256(content.encode()).hexdigest(),
            }
        )
    entries.append(
        {
            "kind": "renderer_decision",
            "id": "explicit-native-types-v1",
            "output_file": "workflow.fabro",
            "plan_instance_ids": [],
            "origins": graph["origins"],
            "content_binding": hashlib.sha256(b"explicit-native-types-v1").hexdigest(),
        }
    )
    return sorted(entries, key=lambda item: (item["kind"], str(item["id"])))


def _file_records(files: dict[str, str], source_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for path, content in files.items():
        encoded = content.encode("utf-8")
        records.append(
            {
                "path": path,
                "bytes": len(encoded),
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "semantic_kind": "workflow_config" if path.endswith(".toml") else "native_source",
                "referencing_elements": sorted(
                    item["id"] for item in source_map if item["output_file"] == path
                ),
            }
        )
    return sorted(records, key=lambda item: item["path"])


def validate_closure(
    files: dict[str, str], entrypoint: str, profile: dict[str, Any]
) -> list[dict[str, Any]]:
    limits = profile["limits"]
    if not isinstance(files, dict) or len(files) > limits["native_files"]:
        raise InputError("PACKAGE_FILE_LIMIT", "Native file count limit exceeded")
    folded: set[str] = set()
    total = 0
    for path, content in files.items():
        _safe_path(path)
        if path.casefold() in folded:
            raise InputError("PACKAGE_CASE_COLLISION", f"Case-colliding package path: {path}")
        folded.add(path.casefold())
        if not isinstance(content, str):
            raise InputError("PACKAGE_CONTENT", f"Package content is not UTF-8 text: {path}")
        size = len(content.encode("utf-8"))
        if size > limits["native_file_bytes"]:
            raise InputError("PACKAGE_FILE_SIZE", f"Package file exceeds limit: {path}")
        total += size
    if total > limits["native_total_bytes"]:
        raise InputError("PACKAGE_SOURCE_SIZE", "Native source set exceeds limit")
    if entrypoint not in files or entrypoint != "workflow.toml":
        raise InputError("PACKAGE_ENTRYPOINT", "Entrypoint must be declared workflow.toml")
    return []


def validate_package_byte_count(size: int, profile: dict[str, Any]) -> None:
    if size > profile["limits"]["package_bytes"]:
        raise InputError("PACKAGE_SIZE", "Sealed package exceeds limit")


def compile_package(
    inputs: CompilerInputs, *, native_validator: NativeValidator = validate_native
) -> dict[str, Any]:
    """Compile entirely in memory and return a sealed, natively accepted package."""

    projected = project_mapping(inputs.plan, inputs.mapping, inputs.compiler_profile)
    graph = build_ir(projected, inputs.mapping, inputs.compiler_profile)
    semantic_validation = validate_graph(graph, inputs.compiler_profile)
    files = render_native(graph, projected["support_files"])
    validate_closure(files, "workflow.toml", inputs.compiler_profile)
    missing_support = sorted(
        support
        for node in graph["nodes"]
        for support in node["support_files"]
        if support not in files
    )
    if missing_support:
        raise CompilerSemanticError(
            "UNDECLARED_SUPPORT_FILE", f"Actions reference undeclared files: {missing_support}"
        )
    source_map = _source_map(graph, files, inputs.mapping)
    native_validation = native_validator(files, "workflow.toml", inputs.validator_profile)
    file_records = _file_records(files, source_map)
    ir_digest = hashlib.sha256(canonical(graph)).hexdigest()
    source_map_digest = hashlib.sha256(canonical(source_map)).hexdigest()
    baseline = {
        "compiler_profile": inputs.semantic_digests["compiler_profile"],
        "validator_profile": inputs.semantic_digests["validator_profile"],
        "inputs": dict(sorted(inputs.semantic_digests.items())),
        "ir_digest": ir_digest,
        "file_digests": {item["path"]: item["sha256"] for item in file_records},
        "source_map_digest": source_map_digest,
    }
    package_identity = hashlib.sha256(canonical(baseline)).hexdigest()
    unevaluated = {
        name: "not_evaluated"
        for name in (
            "registration",
            "execution",
            "evidence",
            "acceptance",
            "engineering_readiness",
            "release",
        )
    }
    compile_report = {
        "status": "compiled_and_validated",
        "package_identity": package_identity,
        "counts": {"nodes": len(graph["nodes"]), "edges": len(graph["edges"]), "files": len(files)},
        "capabilities": unevaluated,
        "diagnostics": [],
    }
    manifest = {
        "schema_version": 1,
        "package_identity": package_identity,
        "compiler": {
            "id": inputs.compiler_profile["id"],
            "version": inputs.compiler_profile["version"],
            "digest": inputs.semantic_digests["compiler_profile"],
            "limits": inputs.compiler_profile["limits"],
        },
        "validator": {
            "id": inputs.validator_profile["id"],
            "version": inputs.validator_profile["version"],
            "digest": inputs.semantic_digests["validator_profile"],
            "source_commit": inputs.validator_profile["source_commit"],
        },
        "inputs": dict(sorted(inputs.semantic_digests.items())),
        "ir": graph,
        "ir_digest": ir_digest,
        "file_records": file_records,
        "source_map_digest": source_map_digest,
        "compile_report_digest": hashlib.sha256(canonical(compile_report)).hexdigest(),
        "limitations": [
            "Registration, execution, evidence acceptance, readiness, release, "
            "and deployment are not evaluated."
        ],
    }
    payload = {
        "schema_version": 1,
        "manifest": manifest,
        "entrypoint": "workflow.toml",
        "files": files,
        "source_map": source_map,
        "compile_report": compile_report,
        "semantic_validation": semantic_validation,
        "native_validation": native_validation,
    }
    digest = semantic_digest(payload)
    package = {**payload, "digest": digest}
    validate_package_byte_count(len(canonical(package)), inputs.compiler_profile)
    validate_package(package, inputs.compiler_profile)
    return package


def validate_package(package: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema_version",
        "manifest",
        "entrypoint",
        "files",
        "source_map",
        "compile_report",
        "semantic_validation",
        "native_validation",
        "digest",
    }
    if (
        not isinstance(package, dict)
        or set(package) != expected
        or type(package.get("schema_version")) is not int
        or package["schema_version"] != 1
    ):
        raise InputError("PACKAGE_FIELDS", "Invalid workflow package envelope")
    declared = package["digest"]
    if not isinstance(declared, str) or semantic_digest(package) != declared:
        raise InputError("PACKAGE_DIGEST", "Workflow package self-digest mismatch")
    manifest = package["manifest"]
    manifest_fields = {
        "schema_version",
        "package_identity",
        "compiler",
        "validator",
        "inputs",
        "ir",
        "ir_digest",
        "file_records",
        "source_map_digest",
        "compile_report_digest",
        "limitations",
    }
    if not isinstance(manifest, dict) or set(manifest) != manifest_fields:
        raise InputError("PACKAGE_MANIFEST_FIELDS", "Invalid package manifest fields")
    if set(manifest.get("compiler", {})) != {"id", "version", "digest", "limits"}:
        raise InputError("PACKAGE_COMPILER_FIELDS", "Invalid compiler binding fields")
    if set(manifest.get("validator", {})) != {"id", "version", "digest", "source_commit"}:
        raise InputError("PACKAGE_VALIDATOR_FIELDS", "Invalid validator binding fields")
    if "limits" in profile and (
        manifest["compiler"]["id"] != profile.get("id")
        or manifest["compiler"]["digest"] != profile.get("digest")
    ):
        raise InputError("COMPILER_PROFILE_MISMATCH", "Package compiler profile differs")
    report_fields = {"status", "package_identity", "counts", "capabilities", "diagnostics"}
    report = package["compile_report"]
    if not isinstance(report, dict) or set(report) != report_fields:
        raise InputError("COMPILE_REPORT_FIELDS", "Invalid compile report fields")
    capabilities = {
        "registration",
        "execution",
        "evidence",
        "acceptance",
        "engineering_readiness",
        "release",
    }
    if set(report.get("capabilities", {})) != capabilities or set(
        report["capabilities"].values()
    ) != {"not_evaluated"}:
        raise InputError("COMPILE_REPORT_BOUNDARY", "Invalid unevaluated capability boundary")
    source_fields = {
        "kind",
        "id",
        "output_file",
        "plan_instance_ids",
        "origins",
        "content_binding",
    }
    if not isinstance(package["source_map"], list) or any(
        not isinstance(item, dict) or set(item) != source_fields for item in package["source_map"]
    ):
        raise InputError("SOURCE_MAP_FIELDS", "Invalid source-map entry fields")
    semantic_fields = {"ruleset", "counts", "findings", "valid"}
    if (
        not isinstance(package["semantic_validation"], dict)
        or set(package["semantic_validation"]) != semantic_fields
    ):
        raise InputError("SEMANTIC_RECEIPT_FIELDS", "Invalid semantic receipt fields")
    native_fields = {
        "validator",
        "source_set_digest",
        "workflow_name",
        "nodes",
        "edges",
        "diagnostics",
        "accepted",
    }
    if (
        not isinstance(package["native_validation"], dict)
        or set(package["native_validation"]) != native_fields
    ):
        raise InputError("NATIVE_RECEIPT_FIELDS", "Invalid native receipt fields")
    limits = profile.get("limits")
    if not isinstance(limits, dict):
        limits = manifest.get("compiler", {}).get("limits")
    if not isinstance(limits, dict):
        raise InputError("COMPILER_PROFILE", "Package compiler limits are unavailable")
    validate_closure(package["files"], package["entrypoint"], {"limits": limits})
    records = manifest.get("file_records")
    record_fields = {
        "path",
        "bytes",
        "sha256",
        "semantic_kind",
        "referencing_elements",
    }
    if (
        not isinstance(records, list)
        or any(not isinstance(item, dict) or set(item) != record_fields for item in records)
        or {item.get("path") for item in records if isinstance(item, dict)} != set(package["files"])
    ):
        raise InputError("PACKAGE_CLOSURE", "File records do not match declared files")
    for record in records:
        content = package["files"][record["path"]].encode()
        if (
            record.get("bytes") != len(content)
            or record.get("sha256") != hashlib.sha256(content).hexdigest()
        ):
            raise InputError("PACKAGE_FILE_DIGEST", f"File integrity mismatch: {record['path']}")
    if (
        manifest.get("source_map_digest")
        != hashlib.sha256(canonical(package["source_map"])).hexdigest()
    ):
        raise InputError("SOURCE_MAP_DIGEST", "Source-map integrity mismatch")
    if (
        manifest.get("compile_report_digest")
        != hashlib.sha256(canonical(package["compile_report"])).hexdigest()
    ):
        raise InputError("COMPILE_REPORT_DIGEST", "Compile-report integrity mismatch")
    graph = manifest.get("ir")
    if (
        not isinstance(graph, dict)
        or manifest.get("ir_digest") != hashlib.sha256(canonical(graph)).hexdigest()
    ):
        raise InputError("IR_DIGEST", "IR integrity mismatch")
    missing_support = sorted(
        support
        for node in graph["nodes"]
        for support in node.get("support_files", [])
        if support not in package["files"]
    )
    if missing_support:
        raise InputError(
            "UNDECLARED_SUPPORT_FILE", f"Actions reference undeclared files: {missing_support}"
        )
    if any("command_file" in node for node in graph["nodes"]):
        support = [
            {"path": path, "content": content, "origin": {}}
            for path, content in package["files"].items()
            if path not in {"workflow.fabro", "workflow.toml"}
        ]
        try:
            rendered = render_native(graph, support)
        except CompilerSemanticError as exc:
            raise InputError("COMMAND_BINDING", f"Invalid packaged command binding: {exc}") from exc
        if rendered != package["files"]:
            raise InputError(
                "COMMAND_BINDING", "Packaged command binding differs from native source"
            )
    expected_subjects = {
        (kind, str(value.get("id") or value.get("node_id")))
        for kind, values in (
            ("node", graph["nodes"]),
            ("edge", graph["edges"]),
            ("gate", graph["gates"]),
            ("loop", graph["loop_policies"]),
            ("fan_group", graph["fan_groups"]),
        )
        for value in values
    }
    mapped = {(item.get("kind"), str(item.get("id"))) for item in package["source_map"]}
    if not expected_subjects <= mapped:
        raise InputError("SOURCE_MAP_COVERAGE", "Source map does not cover every semantic element")
    return {"valid": True, "package_identity": manifest["package_identity"], "digest": declared}


def read_package(path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    package = read_json(path)
    maximum = profile.get("limits", {}).get("package_bytes", 64 * 1024 * 1024)
    if type(maximum) is not int or path.stat().st_size > maximum:
        raise InputError("PACKAGE_SIZE", "Workflow package exceeds limit")
    validate_package(package, profile)
    return package


def write_package(path: Path, package: dict[str, Any], inputs: CompilerInputs) -> None:
    """Atomically publish only beneath the selected output root."""

    target = (Path.cwd() / path).absolute()
    resolved = target.resolve()
    if not resolved.is_relative_to(inputs.output_root.resolve()):
        raise InputError("OUTPUT_PATH", "Output must be beneath the declared output root")
    if target.is_symlink() or any(
        parent.is_symlink()
        for parent in target.parents
        if parent != inputs.output_root and parent.is_relative_to(inputs.output_root)
    ):
        raise InputError("OUTPUT_SYMLINK", "Output path may not traverse a symlink")
    if any(resolved == root or resolved.is_relative_to(root) for root in inputs.protected_roots):
        raise InputError("OUTPUT_SOURCE_ROOT", "Output may not modify a protected tree")
    if any(
        resolved == item.resolve() or (target.exists() and os.path.samefile(target, item))
        for item in inputs.input_paths
    ):
        raise InputError("OUTPUT_ALIAS", "Output aliases a compiler input")
    data = canonical(package)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".workflow-package-", dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError as exc:
        raise InputError("OUTPUT_IO", str(exc)) from exc


def compile_request(
    request: Path, output: Path, *, native_validator: NativeValidator = validate_native
) -> dict[str, Any]:
    inputs = load_compiler_inputs(request)
    package = compile_package(inputs, native_validator=native_validator)
    write_package(output, package, inputs)
    return package
