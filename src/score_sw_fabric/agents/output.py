"""Structured role-result validation and snapshot-based write-scope checks."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.context import read_observations
from score_sw_fabric.agents.lock import load_lock, server_by_id
from score_sw_fabric.agents.models import (
    PROTECTED_WORKSPACE_GLOBS,
    READINESS,
    diff_snapshots,
    git_baseline,
    input_file,
    json_file,
    load_request,
    local_dir,
    matches_any,
    protected_roots,
    relative_path,
    snapshot,
)
from score_sw_fabric.agents.roles import server_writes
from score_sw_fabric.assurance.models import exact, nonempty, seal, verify_digest, version
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.request import parse_json

CHECK_FIELDS = {"lock", "bundle", "result", "protected_roots"}
RESULT_FIELDS = {
    "role_id",
    "context_digest",
    "changed_paths",
    "native_ids_affected",
    "evidence_refs",
    "unresolved_assumptions",
    "proposed_next_action",
    "self_reported_checks",
}
MAX_RESULT_BYTES = 1024 * 1024


def validate_result(value: Any) -> dict[str, Any]:
    """Validate an agent_result version 1 object; raises InputError naming the fault."""
    result = version(value, "agent_result", RESULT_FIELDS, "/agent_result")
    nonempty(result["role_id"], "/role_id", max_length=256)
    nonempty(result["context_digest"], "/context_digest", max_length=64)
    for name, limit in (("changed_paths", 10_000), ("native_ids_affected", 10_000)):
        items = result[name]
        if not isinstance(items, list) or len(items) > limit:
            raise InputError("FIELD_TYPE", f"{name} must be a bounded list", f"/{name}")
        for index, item in enumerate(items):
            if name == "changed_paths":
                relative_path(item, f"/{name}/{index}")
            else:
                nonempty(item, f"/{name}/{index}", max_length=256)
        if len(set(items)) != len(items):
            raise InputError("DUPLICATE_ID", f"Duplicate entry in {name}", f"/{name}")
    refs = result["evidence_refs"]
    if not isinstance(refs, list) or len(refs) > 1000:
        raise InputError("FIELD_TYPE", "evidence_refs must be a bounded list", "/evidence_refs")
    for index, item in enumerate(refs):
        ref = exact(item, {"kind", "ref"}, f"/evidence_refs/{index}")
        nonempty(ref["kind"], f"/evidence_refs/{index}/kind", max_length=64)
        nonempty(ref["ref"], f"/evidence_refs/{index}/ref", max_length=1024)
    assumptions = result["unresolved_assumptions"]
    if not isinstance(assumptions, list) or len(assumptions) > 200:
        raise InputError(
            "FIELD_TYPE", "unresolved_assumptions must be a list", "/unresolved_assumptions"
        )
    for index, item in enumerate(assumptions):
        nonempty(item, f"/unresolved_assumptions/{index}", max_length=2048)
    nonempty(result["proposed_next_action"], "/proposed_next_action", max_length=4096)
    checks = result["self_reported_checks"]
    if not isinstance(checks, list) or len(checks) > 200:
        raise InputError(
            "FIELD_TYPE", "self_reported_checks must be a list", "/self_reported_checks"
        )
    for index, item in enumerate(checks):
        check = exact(item, {"name", "result"}, f"/self_reported_checks/{index}")
        nonempty(check["name"], f"/self_reported_checks/{index}/name", max_length=256)
        if check["result"] not in {"pass", "fail", "unknown"}:
            raise InputError("FIELD_ENUM", "Unknown check result", f"/self_reported_checks/{index}")
    return result


def check(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    record, base = load_request(request_path, "agent_check_request", CHECK_FIELDS)
    lock_path, lock_bytes = input_file(base, record["lock"], "/lock")
    lock = load_lock(lock_bytes)
    bundle_path, _, bundle = json_file(base, record["bundle"], "/bundle")
    verify_digest(bundle, "/bundle")
    if bundle.get("kind") != "agent_context_bundle" or bundle.get("lock", {}).get("sha256") != (
        hashlib.sha256(lock_bytes).hexdigest()
    ):
        raise InputError("BUNDLE_MISMATCH", "Bundle does not bind this lock", "/bundle")
    result_path, result_bytes = input_file(base, record["result"], "/result")
    workspace = local_dir(base, bundle["workspace"]["path"], "/bundle/workspace")
    protected = protected_roots(base, record["protected_roots"], "/protected_roots")
    reasons: list[dict[str, str]] = []
    violations: list[dict[str, str]] = []
    structure = "valid"
    result: dict[str, Any] | None = None
    try:
        if len(result_bytes) > MAX_RESULT_BYTES:
            raise InputError("LIMIT_EXCEEDED", "Result exceeds 1 MiB", "/agent_result")
        result = validate_result(parse_json(result_bytes, "/agent_result"))
    except InputError as exc:
        structure = "malformed"
        reasons.append(
            {"code": "RESULT_MALFORMED", "detail": f"{exc.code} {str(exc.pointer)[:200]}"}
        )
    if result is not None and (
        result["role_id"] != bundle["role"]["id"] or result["context_digest"] != bundle["digest"]
    ):
        reasons.append({"code": "CONTEXT_MISMATCH", "detail": "role or context digest differs"})
    baseline = git_baseline(workspace)
    if baseline["commit"] != bundle["workspace"]["commit"]:
        reasons.append({"code": "BASELINE_CHANGED", "detail": baseline["commit"]})
    after = snapshot(workspace)
    changes = diff_snapshots(bundle["workspace"]["snapshot"], after)
    kinds = {
        item["path"]: item["kind"]
        for item in [*bundle["workspace"]["snapshot"]["files"], *after["files"]]
    }
    managed: list[str] = []
    for tool in bundle["mcp_tools"]:
        server = server_by_id(lock, tool["server"], "/bundle/mcp_tools")
        managed.extend(item for item in server_writes(server) if item not in managed)
    for item in changes:
        path = item["path"]
        if matches_any(PROTECTED_WORKSPACE_GLOBS, path):
            violations.append({"code": "PROTECTED_PATH", "path": path})
        elif not matches_any(bundle["write_scope"], path):
            violations.append({"code": "WRITE_OUT_OF_SCOPE", "path": path})
    observed = {
        item["path"]
        for item in changes
        if not matches_any(managed, item["path"]) and kinds.get(item["path"]) != "directory"
    }
    declared = set() if result is None else set(result["changed_paths"])
    if result is not None:
        for path in sorted(observed - declared):
            violations.append({"code": "UNDECLARED_CHANGE", "path": path})
        for path in sorted(declared - observed):
            violations.append({"code": "DECLARED_NOT_CHANGED", "path": path})
    for item in violations:
        reasons.append({"code": item["code"], "detail": item["path"][:512]})
    previous = set(bundle["observation_index"]["record_ids"])
    current, _ = read_observations(workspace)
    bindings = [
        {"record_id": item["id"], "baseline_commit": bundle["workspace"]["commit"]}
        for item in current
        if item["id"] not in previous
    ]
    stopped = bool(reasons)
    output = {
        "schema_version": 1,
        "kind": "agent_output_check",
        "role_id": bundle["role"]["id"],
        "context_digest": bundle["digest"],
        "result_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "structure": structure,
        "workspace": {"path": str(workspace), "commit": baseline["commit"]},
        "changes": changes,
        "violations": violations,
        "outcome": "stopped" if stopped else "within_bounds",
        "reasons": reasons,
        "native_ids_affected": [] if result is None else result["native_ids_affected"],
        "unresolved_assumptions": [] if result is None else result["unresolved_assumptions"],
        "proposed_next_action": None if result is None else result["proposed_next_action"],
        "self_reported_checks": []
        if result is None
        else [{**item, "origin": "agent_assertion"} for item in result["self_reported_checks"]],
        "evidence_refs": []
        if result is None
        else [{**item, "verification": "not_verified"} for item in result["evidence_refs"]],
        "observation_bindings": bindings,
        "engineering_readiness": READINESS,
        "limitations": [
            "within_bounds means only deterministic structure and scope checks passed; review "
            "of the content remains required.",
            "Self-reported checks are agent assertions and evidence references are unverified.",
            "Observation bindings record the baseline of new hint records, not their truth.",
        ],
    }
    return (
        1 if stopped else 0,
        seal(output),
        [lock_path, bundle_path, result_path],
        [*protected, workspace],
    )
