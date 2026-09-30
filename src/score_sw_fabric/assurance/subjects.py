"""Derive an exact engineering subject from sealed 002 and 004 inputs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from score_sw_fabric.artifacts.models import ArtifactSemanticError, unevaluated_capabilities
from score_sw_fabric.artifacts.obligations import derive_obligations
from score_sw_fabric.artifacts.package import validate_candidate
from score_sw_fabric.artifacts.trace import evaluate_trace
from score_sw_fabric.assurance.models import MAX_PREDICATES, seal, sha, unique_strings
from score_sw_fabric.assurance.reader import resolve_file
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.reader import semantic_digest, verify_self_digest
from score_sw_fabric.process_source.reader import InputError, read_bytes

SUBJECT_INPUTS = {
    "plan",
    "candidate",
    "report",
    "artifact_profile",
    "trace_profile",
    "snapshot",
    "workflow_package",
    "artifact_request",
}


def _bound(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise InputError(
            "SUBJECT_MISMATCH", f"Subject binding differs: {label}", f"/inputs/{label}"
        )


def _artifact_request_closure(
    inputs: dict[str, Any], source_override: dict[str, bytes] | None = None
) -> None:
    request = inputs["artifact_request"]
    candidate = inputs["candidate"]
    _bound(candidate["bindings"]["request"], semantic_digest(request), "artifact_request")
    for name, field in (
        ("plan", "plan"),
        ("artifact_profile", "artifact_profile"),
        ("trace_profile", "trace_profile"),
        ("snapshot", "target_snapshot"),
        ("workflow_package", "workflow_package"),
    ):
        selected = request.get(field)
        if name == "trace_profile" and selected is None and "trace_profile" not in inputs:
            continue
        if not isinstance(selected, dict) or name not in inputs:
            raise InputError("CLOSURE_MISSING", f"Artifact request lacks {field}")
        _bound(selected.get("semantic_digest"), inputs[name]["digest"], field)
    source_root = request.get("local_paths", {}).get("snapshot_root")
    if not isinstance(source_root, str):
        raise InputError("CLOSURE_MISSING", "Artifact snapshot source root is missing")
    root = Path.cwd() / source_root
    if source_override is None and not root.is_dir():
        raise InputError("INPUT_UNAVAILABLE", "Artifact snapshot source root is absent")
    base = {item["path"]: item for item in candidate["base_files"]}
    snapshot = {item["path"]: item for item in inputs["snapshot"]["files"]}
    if set(base) != set(snapshot):
        raise InputError("SUBJECT_MISMATCH", "Candidate base and snapshot file sets differ")
    for name, item in snapshot.items():
        if source_override is None:
            source = resolve_file(root, name, "/snapshot/files")
            content = source.read_bytes()
        else:
            try:
                content = source_override[name]
            except KeyError as exc:
                raise InputError("CLOSURE_MISSING", f"Missing source bytes for {name}") from exc
        actual = hashlib.sha256(content).hexdigest()
        _bound(actual, sha(item["sha256"], "/snapshot/files/sha256"), "source file")
        _bound(actual, base[name]["sha256"], "candidate base file")
        _bound(len(content), item["bytes"], "source byte count")


def build_subject(
    request: dict[str, Any],
    inputs: dict[str, Any],
    *,
    source_override: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    """Validate closure and seal an identity independent of later observations."""
    missing = SUBJECT_INPUTS - set(inputs) - {"report", "trace_profile"}
    if missing or set(inputs) - SUBJECT_INPUTS:
        raise InputError(
            "CLOSURE_MISSING", f"Unexpected or missing subject inputs: {sorted(missing)}"
        )
    plan = inputs["plan"]
    candidate = inputs["candidate"]
    profile = inputs["artifact_profile"]
    snapshot = inputs["snapshot"]
    workflow = inputs["workflow_package"]
    trace_profile = inputs.get("trace_profile")
    for name in ("plan", "candidate", "artifact_profile", "snapshot", "workflow_package"):
        verify_self_digest(inputs[name], f"/inputs/{name}")
    if trace_profile is not None:
        verify_self_digest(trace_profile, "/inputs/trace_profile")
    _bound(
        candidate["bindings"].get("trace_profile"),
        trace_profile["digest"] if trace_profile is not None else None,
        "trace_profile",
    )
    if plan.get("schema_version") != 1 or plan.get("plan_kind") != "draft":
        raise InputError("VERSION_UNSUPPORTED", "Expected a sealed 002 draft plan")
    if candidate.get("schema_version") != 1 or candidate.get("kind") != "artifact_candidate":
        raise InputError("VERSION_UNSUPPORTED", "Expected a sealed 004 candidate")
    validate_candidate(candidate, profile)
    for name, value in (
        ("plan", plan["digest"]),
        ("artifact_profile", profile["digest"]),
        ("snapshot", snapshot["digest"]),
        ("workflow_package", workflow["digest"]),
    ):
        _bound(candidate["bindings"].get(name), value, name)
    identity_basis = {
        "bindings": candidate["bindings"],
        "base_files": candidate["base_files"],
        "overlay_files": candidate["overlay_files"],
        "edit_results": candidate["edit_results"],
        "source_map": candidate["source_map"],
        "index": candidate["index"]["digest"],
        "native_receipt": candidate["index"]["native_receipt"],
    }
    actual_identity = hashlib.sha256(canonical(identity_basis)).hexdigest()
    _bound(candidate["candidate_identity"], actual_identity, "candidate identity")
    _bound(candidate["native_receipt"], candidate["index"]["native_receipt"], "native receipt")
    for index, template in enumerate(profile.get("templates", [])):
        if not isinstance(template, dict):
            raise InputError("FIELD_TYPE", "Invalid artifact template entry")
        path = template.get("path")
        if not isinstance(path, str):
            raise InputError("FIELD_TYPE", "Invalid artifact template path")
        expected_hash = sha(template.get("sha256"), f"/profile/templates/{index}/sha256")
        if source_override is None:
            source = resolve_file(Path.cwd(), path, f"/profile/templates/{index}/path")
            content = read_bytes(source)
        else:
            try:
                content = source_override[path]
            except (KeyError, TypeError) as exc:
                raise InputError("CLOSURE_MISSING", f"Missing template bytes: {path}") from exc
        _bound(hashlib.sha256(content).hexdigest(), expected_hash, f"template {path}")
    _artifact_request_closure(inputs, source_override)
    plan_ids = unique_strings(
        [item["instance_id"] for item in plan["instances"]],
        MAX_PREDICATES,
        "/plan/instances",
    )
    if not plan_ids:
        raise InputError("OBLIGATION_SET_INCOMPLETE", "Plan has no obligation instances")
    report = inputs.get("report")
    report_info: dict[str, Any] | None = None
    report_ids: list[str] = []
    limitations: list[str] = []
    if report is not None:
        verify_self_digest(report, "/report")
        if report.get("kind") != "artifact_report":
            raise InputError("KIND_MISMATCH", "Expected an 004 artifact report")
        _bound(report["bindings"].get("plan"), plan["digest"], "report plan")
        _bound(report["bindings"].get("index"), candidate["index"]["digest"], "report index")
        if not isinstance(candidate["report"], dict):
            raise InputError("SUBJECT_MISMATCH", "Candidate does not bind selected report")
        _bound(candidate["report"], report, "candidate report")
        if trace_profile is None:
            raise InputError("CLOSURE_MISSING", "Trace report lacks its selected profile")
        try:
            expected_trace = derive_obligations(plan, workflow, trace_profile)
            evaluated, coverage, observed, valid = evaluate_trace(
                expected_trace, candidate["index"], trace_profile
            )
        except ArtifactSemanticError as exc:
            raise InputError("TRACE_RECOMPUTE", str(exc)) from exc
        expected_fields = {
            "status": "passed" if valid else "blocked",
            "obligations": evaluated,
            "coverage": coverage,
            "observed_traces": observed,
            "findings": [
                item for obligation in evaluated for item in obligation.get("findings", [])
            ],
            "capabilities": unevaluated_capabilities(),
            "impact": None,
        }
        for field, expected_value in expected_fields.items():
            _bound(report.get(field), expected_value, f"report {field}")
        report_ids = unique_strings(
            [item["id"] for item in report["obligations"]],
            MAX_PREDICATES,
            "/report/obligations",
        )
        report_info = {
            "digest": report["digest"],
            "status": report["status"],
            "index_digest": report["bindings"]["index"],
            "expected_obligation_ids": report_ids,
        }
    else:
        if candidate["trace_validation"] != "not_requested" or candidate["report"] is not None:
            raise InputError("CLOSURE_MISSING", "Candidate report is absent from subject inputs")
        limitations.append("TRACE_NOT_EVALUATED")
    expected = sorted(set(plan_ids) | set(report_ids))
    native = candidate["native_receipt"]
    subject = {
        "schema_version": 1,
        "kind": "assurance_subject",
        "assurance_domain": request["assurance_domain"],
        "scope": request["scope"],
        "plan": {
            "digest": plan["digest"],
            "target_namespace": plan["target_namespace"],
            "instances": [
                {
                    "id": item["instance_id"],
                    "disposition": item["effective_disposition"],
                }
                for item in sorted(plan["instances"], key=lambda item: item["instance_id"])
            ],
            "semantic_inputs": plan["semantic_inputs"],
        },
        "artifact_candidate": {
            "digest": candidate["digest"],
            "candidate_identity": candidate["candidate_identity"],
            "bindings": candidate["bindings"],
            "index_digest": candidate["index"]["digest"],
            "native_receipt_digest": hashlib.sha256(canonical(native)).hexdigest(),
        },
        "artifact_report": report_info,
        "source_baselines": [snapshot["source"]],
        "process_baseline": plan["semantic_inputs"],
        "toolchain": {"native_validator": native["validator"], "commands": native["commands"]},
        "profiles": {
            "artifact": profile["digest"],
            "trace": candidate["bindings"]["trace_profile"],
        },
        "policy_bindings": {},
        "expected_obligation_ids": expected,
        "file_closure": [
            {"path": item["path"], "sha256": item["sha256"], "role": "base"}
            for item in sorted(candidate["base_files"], key=lambda item: item["path"])
        ]
        + [
            {"path": item["path"], "sha256": item["sha256"], "role": "overlay"}
            for item in sorted(candidate["overlay_files"], key=lambda item: item["path"])
        ],
        "limitations": limitations,
    }
    return seal(subject)
