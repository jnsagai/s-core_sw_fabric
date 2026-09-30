"""Canonical artifact sealing, candidate construction, validation, and publication."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

from score_sw_fabric.artifacts.edit import apply_edits
from score_sw_fabric.artifacts.index import build_index, require_valid_index
from score_sw_fabric.artifacts.models import (
    ArtifactInputs,
    ArtifactSemanticError,
    enforce_limit,
    unevaluated_capabilities,
)
from score_sw_fabric.artifacts.native import validate_native
from score_sw_fabric.artifacts.obligations import derive_obligations
from score_sw_fabric.artifacts.reader import load_artifact_inputs, read_snapshot_files
from score_sw_fabric.artifacts.trace import evaluate_trace
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.reader import semantic_digest, verify_self_digest
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml

CANDIDATE_FIELDS = {
    "schema_version",
    "kind",
    "candidate_identity",
    "bindings",
    "base_files",
    "overlay_files",
    "edit_results",
    "source_map",
    "index",
    "report",
    "trace_validation",
    "native_receipt",
    "limitations",
    "capabilities",
    "digest",
}


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["digest"] = semantic_digest(result)
    return result


def _file_records(files: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "path": path,
            "bytes": len(content.encode()),
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }
        for path, content in sorted(files.items())
    ]


def _publish(path: Path, value: dict[str, Any], inputs: ArtifactInputs) -> None:
    target = path.absolute()
    root = inputs.output_root.resolve()
    try:
        resolved_parent = target.parent.resolve()
    except OSError as exc:
        raise InputError("OUTPUT_PATH", str(exc)) from exc
    if not resolved_parent.is_relative_to(root):
        raise InputError("OUTPUT_PATH", "Output must be beneath the request output_root")
    if target.is_symlink() or any(
        parent.is_symlink()
        for parent in target.parents
        if parent != root and parent.is_relative_to(root)
    ):
        raise InputError("OUTPUT_SYMLINK", "Output path may not traverse a symlink")
    if any(
        target.resolve() == source.resolve()
        or (target.exists() and os.path.samefile(target, source))
        for source in inputs.input_paths
    ):
        raise InputError("OUTPUT_ALIAS", "Output aliases an artifact input")
    if any(
        target.resolve() == protected or target.resolve().is_relative_to(protected)
        for protected in inputs.protected_roots
    ):
        raise InputError("OUTPUT_SOURCE_ROOT", "Output may not modify a protected tree")
    data = canonical(value)
    enforce_limit(
        inputs.artifact_profile["limits"],
        "package_bytes",
        len(data),
        "PACKAGE_SIZE",
        "Artifact output exceeds package limit",
    )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".artifact-", dir=target.parent)
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


def build_artifact_index(
    inputs: ArtifactInputs, files: dict[str, str] | None = None
) -> dict[str, Any]:
    selected = read_snapshot_files(inputs) if files is None else files
    receipt, native_export = validate_native(selected, inputs.artifact_profile, inputs.local_paths)
    return require_valid_index(
        build_index(selected, inputs.snapshot, inputs.artifact_profile, native_export, receipt)
    )


def index_request(request: Path, output: Path) -> dict[str, Any]:
    inputs = load_artifact_inputs(request)
    if inputs.operation != "index":
        raise InputError("ARTIFACT_OPERATION", "Expected an index request")
    index = build_artifact_index(inputs)
    _publish(output, index, inputs)
    return index


def _build_trace_report(
    inputs: ArtifactInputs, index: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    if inputs.plan is None or inputs.workflow_package is None or inputs.trace_profile is None:
        raise InputError(
            "ARTIFACT_OPERATION", "Trace evaluation requires plan, package and profile"
        )
    obligations = derive_obligations(inputs.plan, inputs.workflow_package, inputs.trace_profile)
    evaluated, coverage, observed, valid = evaluate_trace(obligations, index, inputs.trace_profile)
    findings = [item for obligation in evaluated for item in obligation.get("findings", [])]
    enforce_limit(
        inputs.artifact_profile["limits"],
        "findings",
        len(findings),
        "ARTIFACT_LIMIT",
        "Trace finding limit exceeded",
        semantic=True,
    )
    report = _seal(
        {
            "schema_version": 1,
            "kind": "artifact_report",
            "status": "passed" if valid else "blocked",
            "bindings": {
                "request": semantic_digest(inputs.request),
                "snapshot": inputs.snapshot["digest"],
                "artifact_profile": inputs.artifact_profile["digest"],
                "trace_profile": inputs.trace_profile["digest"],
                "plan": inputs.plan["digest"],
                "workflow_package": inputs.workflow_package["digest"],
                "index": index["digest"],
            },
            "obligations": evaluated,
            "observed_traces": observed,
            "coverage": coverage,
            "impact": None,
            "findings": findings,
            "limitations": [
                "Trace existence does not establish adequacy, evidence trust, approval, "
                "or readiness."
            ],
            "capabilities": unevaluated_capabilities(),
        }
    )
    return report, valid


def build_candidate(inputs: ArtifactInputs) -> dict[str, Any]:
    if inputs.operation != "candidate":
        raise InputError("ARTIFACT_OPERATION", "Expected a candidate request")
    base = read_snapshot_files(inputs)
    edited, edit_results, source_map = apply_edits(
        base, inputs.request["operations"], inputs.artifact_profile
    )
    index = build_artifact_index(inputs, edited)
    base_records = _file_records(base)
    overlay = [
        {
            **record,
            "base_sha256": next(
                (item["sha256"] for item in base_records if item["path"] == record["path"]), None
            ),
            "content": edited[record["path"]],
            "edit_ids": sorted(
                item["id"] for item in edit_results if item["target_path"] == record["path"]
            ),
        }
        for record in _file_records(edited)
        if base.get(record["path"]) != edited[record["path"]]
    ]
    bindings = {
        "request": semantic_digest(inputs.request),
        "snapshot": inputs.snapshot["digest"],
        "artifact_profile": inputs.artifact_profile["digest"],
        "trace_profile": inputs.trace_profile["digest"] if inputs.trace_profile else None,
        "plan": inputs.plan["digest"] if inputs.plan else None,
        "workflow_package": inputs.workflow_package["digest"] if inputs.workflow_package else None,
    }
    identity_basis = {
        "bindings": bindings,
        "base_files": base_records,
        "overlay_files": overlay,
        "edit_results": edit_results,
        "source_map": source_map,
        "index": index["digest"],
        "native_receipt": index["native_receipt"],
    }
    candidate_identity = hashlib.sha256(canonical(identity_basis)).hexdigest()
    report, trace_valid = (
        _build_trace_report(inputs, index) if inputs.trace_profile is not None else (None, False)
    )
    candidate = _seal(
        {
            "schema_version": 1,
            "kind": "artifact_candidate",
            "candidate_identity": candidate_identity,
            "bindings": bindings,
            "base_files": base_records,
            "overlay_files": overlay,
            "edit_results": edit_results,
            "source_map": source_map,
            "index": index,
            "report": report,
            "trace_validation": (
                "passed" if trace_valid else "blocked" if report is not None else "not_requested"
            ),
            "native_receipt": index["native_receipt"],
            "limitations": [
                "Reviewable isolated overlay only; production apply and engineering "
                "acceptance are outside Increment 004."
            ],
            "capabilities": unevaluated_capabilities(),
        }
    )
    validate_candidate(candidate, inputs.artifact_profile)
    return candidate


def candidate_request(request: Path, output: Path) -> dict[str, Any]:
    inputs = load_artifact_inputs(request)
    candidate = build_candidate(inputs)
    if candidate["trace_validation"] == "blocked":
        raise ArtifactSemanticError(
            "TRACE_UNRESOLVED",
            "Explicit candidate trace evaluation has unresolved obligations",
            findings=candidate["report"]["findings"],
        )
    _publish(output, candidate, inputs)
    return candidate


def validate_candidate(candidate: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, dict) or set(candidate) != CANDIDATE_FIELDS:
        raise InputError("CANDIDATE_FIELDS", "Invalid artifact candidate envelope")
    if candidate.get("schema_version") != 1 or candidate.get("kind") != "artifact_candidate":
        raise InputError("CANDIDATE_VERSION", "Unsupported artifact candidate")
    verify_self_digest(candidate, "/candidate")
    if candidate["bindings"].get("artifact_profile") != profile.get("digest"):
        raise InputError(
            "ARTIFACT_PROFILE_MISMATCH", "Candidate and selected artifact profile differ"
        )
    if candidate.get("capabilities") != unevaluated_capabilities():
        raise InputError("CANDIDATE_BOUNDARY", "Candidate capability boundary is invalid")
    base = {
        item["path"]: item for item in candidate.get("base_files", []) if isinstance(item, dict)
    }
    for item in candidate.get("overlay_files", []):
        if not isinstance(item, dict) or set(item) != {
            "path",
            "bytes",
            "sha256",
            "base_sha256",
            "content",
            "edit_ids",
        }:
            raise InputError("CANDIDATE_FILE_FIELDS", "Invalid candidate overlay file")
        content = item["content"].encode()
        if item["bytes"] != len(content) or item["sha256"] != hashlib.sha256(content).hexdigest():
            raise InputError(
                "CANDIDATE_FILE_DIGEST", f"Candidate file integrity mismatch: {item['path']}"
            )
        if item["base_sha256"] != (base.get(item["path"]) or {}).get("sha256"):
            raise InputError(
                "CANDIDATE_BASE_BINDING", f"Candidate base binding mismatch: {item['path']}"
            )
    verify_self_digest(candidate["index"], "/candidate/index")
    if (
        candidate["index"].get("valid") is not True
        or candidate["native_receipt"].get("accepted") is not True
    ):
        raise ArtifactSemanticError(
            "CANDIDATE_INVALID", "Candidate index or native receipt is not accepted"
        )
    trace_state = candidate.get("trace_validation")
    if trace_state not in {"not_requested", "passed", "blocked"}:
        raise InputError("TRACE_STATE", "Invalid candidate trace-validation state")
    if trace_state == "not_requested" and candidate.get("report") is not None:
        raise InputError(
            "TRACE_STATE", "Candidate with no requested trace cannot claim a trace report"
        )
    if trace_state in {"passed", "blocked"} and not isinstance(candidate.get("report"), dict):
        raise InputError("TRACE_STATE", "Candidate trace state requires an attached report")
    if trace_state in {"passed", "blocked"}:
        report = candidate["report"]
        verify_self_digest(report, "/candidate/report")
        if report.get("kind") != "artifact_report" or report.get("status") != trace_state:
            raise InputError("TRACE_STATE", "Candidate and attached trace report state differ")
        expected_bindings = {
            "request": candidate["bindings"]["request"],
            "snapshot": candidate["bindings"]["snapshot"],
            "artifact_profile": candidate["bindings"]["artifact_profile"],
            "trace_profile": candidate["bindings"]["trace_profile"],
            "plan": candidate["bindings"]["plan"],
            "workflow_package": candidate["bindings"]["workflow_package"],
            "index": candidate["index"]["digest"],
        }
        if report.get("bindings") != expected_bindings:
            raise InputError("TRACE_BINDING", "Attached trace report has different bindings")
    return {
        "valid": True,
        "candidate_identity": candidate["candidate_identity"],
        "digest": candidate["digest"],
        "trace_validation": trace_state,
        "capabilities": candidate["capabilities"],
    }


def read_candidate(path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    maximum = profile.get("limits", {}).get("package_bytes", 64 * 1024 * 1024)
    if type(maximum) is not int:
        raise InputError("ARTIFACT_LIMITS", "Invalid package byte limit")
    enforce_limit(
        {"package_bytes": maximum},
        "package_bytes",
        path.stat().st_size,
        "PACKAGE_SIZE",
        "Artifact candidate exceeds package limit",
    )
    candidate = read_json(path)
    validate_candidate(candidate, profile)
    return candidate


def trace_request(request: Path, output: Path) -> tuple[dict[str, Any], bool]:
    inputs = load_artifact_inputs(request)
    if (
        inputs.operation != "trace"
        or inputs.plan is None
        or inputs.workflow_package is None
        or inputs.trace_profile is None
    ):
        raise InputError("ARTIFACT_OPERATION", "Expected a complete trace request")
    index = build_artifact_index(inputs)
    report, valid = _build_trace_report(inputs, index)
    _publish(output, report, inputs)
    return report, valid


def load_profile(path: Path) -> dict[str, Any]:
    profile = read_json(path) if path.suffix == ".json" else read_yaml(path)
    verify_self_digest(profile, "/profile")
    return profile
