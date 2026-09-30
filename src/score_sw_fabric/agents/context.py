"""Role context bundles bound to a repository baseline with labelled local observations."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.lock import load_lock
from score_sw_fabric.agents.models import (
    READINESS,
    git_baseline,
    input_file,
    json_file,
    load_request,
    local_dir,
    protected_roots,
    relative_path,
    separate_roots,
    snapshot,
    string_list,
    yaml_file,
)
from score_sw_fabric.agents.roles import (
    granted_tools,
    role_prompt,
    runtime_agent_config,
    validate_role,
)
from score_sw_fabric.assurance.models import exact, nonempty, seal, sha, stable_id, verify_digest
from score_sw_fabric.process_source.reader import InputError, read_bytes

CONTEXT_FIELDS = {
    "lock",
    "inventory",
    "role",
    "model_profiles",
    "workspace",
    "task",
    "native_sources",
    "assumptions",
    "observations",
    "protected_roots",
}
OBSERVATION_LOGS = (".score-local/sessions.jsonl", ".score-local/observations.jsonl")
TEXT_FIELDS = ("text", "goal", "task", "query", "rationale", "decision")
MAX_OBSERVATIONS = 10_000
MAX_OBSERVATION_TEXT = 4096
MAX_LOG_BYTES = 16 * 1024 * 1024
SECRET_PATTERNS = (
    re.compile(r"fabro_dev_[0-9a-f]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*\S{8,}"),
)


def credential_like(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def read_observations(workspace: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Read upstream hint logs as bounded records with stable IDs and log digests."""
    records: list[dict[str, Any]] = []
    logs = []
    for name in OBSERVATION_LOGS:
        path = workspace / name
        if path.is_symlink() or not path.is_file():
            continue
        data = read_bytes(path)
        if len(data) > MAX_LOG_BYTES:
            raise InputError("LIMIT_EXCEEDED", "Observation log exceeds 16 MiB", "/observations")
        logs.append({"path": name, "sha256": hashlib.sha256(data).hexdigest()})
        for line in data.splitlines():
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except ValueError:
                parsed = None
            identifier = parsed.get("id") if isinstance(parsed, dict) else None
            if not isinstance(identifier, str) or not identifier or len(identifier) > 128:
                identifier = "line__" + hashlib.sha256(line).hexdigest()[:16]
            records.append(
                {
                    "id": identifier,
                    "log": name,
                    "record_type": str(parsed.get("record_type", "observation"))[:64]
                    if isinstance(parsed, dict)
                    else "unparsed",
                    "session_id": str(parsed.get("session_id", ""))[:128]
                    if isinstance(parsed, dict)
                    else "",
                    "timestamp": str(parsed.get("timestamp", ""))[:64]
                    if isinstance(parsed, dict)
                    else "",
                    "text": " | ".join(
                        str(parsed[field]) for field in TEXT_FIELDS if parsed.get(field)
                    )
                    if isinstance(parsed, dict)
                    else "",
                    "line_sha256": hashlib.sha256(line).hexdigest(),
                }
            )
            if len(records) > MAX_OBSERVATIONS:
                raise InputError("LIMIT_EXCEEDED", "Too many observations", "/observations")
    return records, logs


def _bindings(base: Path, value: Any) -> dict[str, str]:
    """Collect record-to-commit bindings from prior sealed output checks."""
    bound: dict[str, str] = {}
    if not isinstance(value, list) or len(value) > 1000:
        raise InputError(
            "LIMIT_EXCEEDED", "Too many observation bindings", "/observations/bindings"
        )
    for index, item in enumerate(value):
        pointer = f"/observations/bindings/{index}"
        _, _, check = json_file(base, item, pointer)
        verify_digest(check, pointer)
        if check.get("kind") != "agent_output_check":
            raise InputError("KIND_MISMATCH", "Bindings must come from agent_output_check", pointer)
        raw_bindings = check.get("observation_bindings")
        if not isinstance(raw_bindings, list):
            raise InputError("FIELD_TYPE", "Check lacks observation bindings", pointer)
        for position, raw in enumerate(raw_bindings):
            binding = exact(raw, {"record_id", "baseline_commit"}, f"{pointer}/{position}")
            record_id = nonempty(binding["record_id"], pointer, max_length=128)
            commit = nonempty(binding["baseline_commit"], pointer, max_length=64)
            if bound.get(record_id, commit) != commit:
                raise InputError("BINDING_CONFLICT", "Observation bound to two commits", pointer)
            bound[record_id] = commit
    return bound


def build_context(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    record, base = load_request(request_path, "agent_context_request", CONTEXT_FIELDS)
    lock_path, lock_bytes = input_file(base, record["lock"], "/lock")
    lock = load_lock(lock_bytes)
    lock_sha = hashlib.sha256(lock_bytes).hexdigest()
    inventory_path, _, inventory = json_file(base, record["inventory"], "/inventory")
    verify_digest(inventory, "/inventory")
    if inventory.get("kind") != "agent_capability_inventory" or inventory.get("lock") != {
        "id": lock["id"],
        "sha256": lock_sha,
    }:
        raise InputError("INVENTORY_MISMATCH", "Inventory does not bind this lock", "/inventory")
    role_path, role_bytes, raw_role = yaml_file(base, record["role"], "/role")
    role = validate_role(raw_role, lock)
    profiles_path, profiles_bytes, profiles = yaml_file(
        base, record["model_profiles"], "/model_profiles"
    )
    if role["model_profile"] not in {
        item.get("id") for item in profiles.get("profiles", []) if isinstance(item, dict)
    }:
        raise InputError(
            "MODEL_PROFILE_UNKNOWN", "Role model profile is not defined", "/model_profiles"
        )
    available = {
        item["id"] for item in inventory.get("servers", []) if item.get("status") == "available"
    }
    for index, server_id in enumerate(role["mcp_servers"]):
        if server_id not in available:
            raise InputError(
                "INVENTORY_NOT_AVAILABLE",
                "Role server was not discovered available",
                f"/mcp_servers/{index}",
            )
    workspace = local_dir(base, record["workspace"], "/workspace")
    if inventory.get("workspace", {}).get("path") != str(workspace):
        raise InputError(
            "INVENTORY_MISMATCH", "Inventory was taken for another workspace", "/workspace"
        )
    protected = protected_roots(base, record["protected_roots"], "/protected_roots")
    separate_roots({"workspace": workspace}, protected)
    copy_root = Path(str(inventory.get("copy_root", "")))
    task = exact(record["task"], {"id", "statement"}, "/task")
    stable_id(task["id"], "/task/id")
    nonempty(task["statement"], "/task/statement", max_length=8192)
    if credential_like(task["statement"]):
        raise InputError(
            "CREDENTIAL_IN_CONTEXT", "Task statement contains a credential-like value", "/task"
        )
    assumptions = string_list(record["assumptions"], "/assumptions", limit=200, length=1024)
    baseline = git_baseline(workspace)
    tracked = set(baseline["tracked"])
    dirty = set(baseline["dirty_paths"])
    sources = []
    raw_sources = record["native_sources"]
    if not isinstance(raw_sources, list) or len(raw_sources) > 1000:
        raise InputError("LIMIT_EXCEEDED", "Too many native sources", "/native_sources")
    for index, raw in enumerate(raw_sources):
        pointer = f"/native_sources/{index}"
        item = exact(raw, {"id", "path", "sha256"}, pointer)
        nonempty(item["id"], pointer + "/id", max_length=256)
        path = relative_path(item["path"], pointer + "/path")
        expected = sha(item["sha256"], pointer + "/sha256")
        full = workspace / path
        try:
            observed = (
                hashlib.sha256(read_bytes(full)).hexdigest() if not full.is_symlink() else None
            )
        except InputError:
            observed = None
        if observed != expected:
            raise InputError("NATIVE_SOURCE_DRIFT", "Native source is missing or changed", pointer)
        if path not in tracked or path in dirty:
            raise InputError("NATIVE_SOURCE_UNCOMMITTED", "Native source is not committed", pointer)
        sources.append(
            {"id": item["id"], "path": path, "sha256": expected, "revision": baseline["commit"]}
        )
    if len({item["id"] for item in sources}) != len(sources):
        raise InputError("DUPLICATE_ID", "Duplicate native source", "/native_sources")
    selection = exact(record["observations"], {"include_text", "bindings"}, "/observations")
    if not isinstance(selection["include_text"], bool):
        raise InputError("FIELD_TYPE", "include_text must be boolean", "/observations/include_text")
    bound = _bindings(base, selection["bindings"])
    observations, logs = read_observations(workspace)
    omissions = []
    classified = []
    for item in observations:
        commit = bound.get(item["id"])
        if commit is None:
            state, reason = "uncertain", "BASELINE_UNBOUND"
        elif commit == baseline["commit"]:
            state, reason = "current", "BOUND_TO_CURRENT_BASELINE"
        else:
            state, reason = "stale", "BOUND_TO_OTHER_BASELINE"
        text: str | None = None
        if selection["include_text"]:
            if credential_like(item["text"]):
                omissions.append(f"observation {item['id']}: text withheld as credential-like")
            else:
                text = item["text"][:MAX_OBSERVATION_TEXT]
        classified.append(
            {
                "id": item["id"],
                "log": item["log"],
                "record_type": item["record_type"],
                "session_id": item["session_id"],
                "timestamp": item["timestamp"],
                "line_sha256": item["line_sha256"],
                "text": text,
                "origin": "local_observation_hint",
                "baseline": commit,
                "state": state,
                "reason": reason,
            }
        )
    if observations and not selection["include_text"]:
        omissions.append(
            f"{len(observations)} local observation texts omitted; private context not selected"
        )
    omissions.append("Local observation store contents other than record metadata are not copied.")
    tools = granted_tools(role, lock)
    prompt = role_prompt(role, task, sources, tools, assumptions, baseline["commit"])
    output = {
        "schema_version": 1,
        "kind": "agent_context_bundle",
        "role": {
            "id": role["id"],
            "sha256": hashlib.sha256(role_bytes).hexdigest(),
            "role": role["role"],
            "status": role["status"],
            "purpose": role["purpose"],
        },
        "lock": {"id": lock["id"], "sha256": lock_sha},
        "inventory_digest": inventory["digest"],
        "model_profiles_sha256": hashlib.sha256(profiles_bytes).hexdigest(),
        "model_profile": role["model_profile"],
        "task": task,
        "workspace": {
            "path": str(workspace),
            "commit": baseline["commit"],
            "dirty_paths": baseline["dirty_paths"],
            "snapshot": snapshot(workspace),
        },
        "native_sources": sources,
        "allowed_inputs": role["allowed_inputs"],
        "write_scope": role["write_scope"],
        "builtin_tools": role["builtin_tools"],
        "mcp_tools": tools,
        "data_destinations": role["data_destinations"],
        "expected_output": role["expected_output"],
        "prohibited_decisions": role["prohibited_decisions"],
        "completion_criteria": role["completion_criteria"],
        "uncertainties_to_report": role["uncertainties_to_report"],
        "unresolved_assumptions": assumptions,
        "observation_index": {
            "record_ids": sorted({item["id"] for item in observations}),
            "logs": logs,
        },
        "observations": classified,
        "omissions": omissions,
        "runtime_agent_config": {
            "format": "fabro_run_toml",
            "status": "candidate_not_executed",
            "text": runtime_agent_config(role, lock, copy_root),
        },
        "role_prompt": {"text": prompt, "sha256": hashlib.sha256(prompt.encode()).hexdigest()},
        "engineering_readiness": READINESS,
        "limitations": [
            "Observations are local hints; none is evidence, a decision or a native record.",
            "The runtime agent configuration is a candidate; no Fabro agent stage executed it.",
            "Role, model and budget profiles are drafts pending owner review.",
        ],
    }
    return (
        0,
        seal(output),
        [lock_path, inventory_path, role_path, profiles_path],
        [*protected, workspace],
    )
