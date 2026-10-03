"""Capability discovery and explicit setup against a verified disposable package copy."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.lock import (
    load_lock,
    server_by_id,
    tool_digest,
    upstream_findings,
    verify_copy,
)
from score_sw_fabric.agents.mcp import McpError, McpSession, call_tool, initialize, list_tools
from score_sw_fabric.agents.models import (
    READINESS,
    diff_snapshots,
    git_baseline,
    input_file,
    load_request,
    local_dir,
    matches_any,
    protected_roots,
    separate_roots,
    snapshot,
)
from score_sw_fabric.assurance.models import exact, seal, stable_id
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError

DISCOVER_FIELDS = {"lock", "copy_root", "workspace", "servers", "probes", "protected_roots"}
SETUP_FIELDS = {"lock", "copy_root", "workspace", "operation", "protected_roots"}
WORKSPACE_TOKEN = "$WORKSPACE"
MAX_PROBES = 32


@dataclass(frozen=True)
class Target:
    lock: dict[str, Any]
    lock_path: Path
    lock_sha256: str
    copy_root: Path
    workspace: Path
    protected: list[Path]

    def inputs(self) -> list[Path]:
        return [self.lock_path]


def _target(record: dict[str, Any], base: Path) -> Target:
    lock_path, lock_bytes = input_file(base, record["lock"], "/lock")
    lock = load_lock(lock_bytes)
    copy_root = local_dir(base, record["copy_root"], "/copy_root")
    workspace = local_dir(base, record["workspace"], "/workspace")
    protected = protected_roots(base, record["protected_roots"], "/protected_roots")
    separate_roots({"copy_root": copy_root, "workspace": workspace}, protected)
    return Target(
        lock=lock,
        lock_path=lock_path,
        lock_sha256=hashlib.sha256(lock_bytes).hexdigest(),
        copy_root=copy_root,
        workspace=workspace,
        protected=protected,
    )


def interpreter() -> dict[str, str]:
    return {"path": sys.executable, "version": platform.python_version()}


def launch_argv(server: dict[str, Any]) -> list[str]:
    return [sys.executable, "-s", "-B", "-m", server["launch"]["module"]]


def launch_environment(server: dict[str, Any], copy_root: Path, home: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": ":".join(str(copy_root / item) for item in server["launch"]["python_path"]),
    }


def _substitute(value: Any, workspace: Path) -> Any:
    if value == WORKSPACE_TOKEN:
        return str(workspace)
    if isinstance(value, dict):
        return {key: _substitute(item, workspace) for key, item in value.items()}
    if isinstance(value, list):
        return [_substitute(item, workspace) for item in value]
    return value


def _compare(
    server: dict[str, Any], init: dict[str, Any], tools: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    info = init["serverInfo"]
    observed = {
        "server_name": info.get("name"),
        "server_version": info.get("version"),
        "protocol_version": init.get("protocolVersion"),
        "tools": sorted(
            ({"name": tool["name"], "schema_sha256": tool_digest(tool)} for tool in tools),
            key=lambda item: item["name"],
        ),
    }
    findings = []
    expected = server["expected"]
    if (observed["server_name"], observed["server_version"]) != (
        expected["server_name"],
        expected["server_version"],
    ):
        findings.append({"code": "SERVER_IDENTITY_MISMATCH", "detail": server["id"]})
    if observed["protocol_version"] != expected["protocol_version"]:
        findings.append(
            {"code": "PROTOCOL_MISMATCH", "detail": str(observed["protocol_version"])[:64]}
        )
    locked = {tool["name"]: tool for tool in server["tools"]}
    seen = {tool["name"]: tool for tool in observed["tools"]}
    if len(seen) != len(tools):
        findings.append({"code": "TOOL_UNLISTED", "detail": "duplicate tool name"})
    for name in sorted(set(locked) - set(seen)):
        findings.append({"code": "TOOL_MISSING", "detail": name})
    for name in sorted(set(seen) - set(locked)):
        findings.append({"code": "TOOL_UNLISTED", "detail": name[:128]})
    for name in sorted(set(seen) & set(locked)):
        if seen[name]["schema_sha256"] != locked[name]["schema_sha256"]:
            findings.append({"code": "TOOL_SCHEMA_DRIFT", "detail": name})
    for item in observed["tools"]:
        item["classification"] = locked.get(item["name"], {}).get("classification")
    return observed, findings


def _session(
    target: Target,
    server: dict[str, Any],
    calls: list[tuple[str, dict[str, Any]]],
    allowed_writes: list[str],
) -> dict[str, Any]:
    """Launch one server, compare it with the lock, run calls only when it matches exactly."""
    limits = target.lock["limits"]
    before = snapshot(target.workspace)
    findings: list[dict[str, str]] = []
    observed: dict[str, Any] | None = None
    results: list[dict[str, Any]] = []
    # Auth-capable homes remain internal even when command scratch uses external TMPDIR.
    with tempfile.TemporaryDirectory(prefix="score-agent-home-", dir="/tmp") as home:
        session = McpSession(
            launch_argv(server),
            cwd=target.workspace,
            environment=launch_environment(server, target.copy_root, Path(home)),
            line_bytes=limits["line_bytes"],
        )
        try:
            with session:
                init = initialize(
                    session, server["expected"]["protocol_version"], limits["handshake_seconds"]
                )
                tools = list_tools(session, limits["handshake_seconds"], 256)
                observed, findings = _compare(server, init, tools)
                started = diff_snapshots(before, snapshot(target.workspace))
                findings.extend(
                    {"code": "UNDECLARED_WORKSPACE_WRITE", "detail": item["path"][:512]}
                    for item in started
                    if not matches_any(server["startup_writes"], item["path"])
                )
                for name, arguments in calls:
                    outcome, text, code = "skipped", None, None
                    if not findings:
                        try:
                            text = call_tool(
                                session,
                                name,
                                arguments,
                                limits["tool_seconds"],
                                limits["result_bytes"],
                            )
                            outcome = "ok"
                        except McpError as exc:
                            outcome, code = "failed", exc.code
                            findings.append(
                                {"code": "TOOL_CALL_FAILED", "detail": f"{name}: {exc.code}"}
                            )
                    results.append(
                        {
                            "server": server["id"],
                            "tool": name,
                            "arguments_sha256": hashlib.sha256(canonical(arguments)).hexdigest(),
                            "outcome": outcome,
                            "error_code": code,
                            "result_text": text,
                            "result_sha256": None
                            if text is None
                            else hashlib.sha256(text.encode()).hexdigest(),
                            "origin": "mcp_tool_result",
                        }
                    )
        except McpError as exc:
            findings.append({"code": "HANDSHAKE_FAILED", "detail": exc.code})
    after = snapshot(target.workspace)
    changes = diff_snapshots(before, after)
    undeclared = [item["path"] for item in changes if not matches_any(allowed_writes, item["path"])]
    for path in undeclared:
        finding = {"code": "UNDECLARED_WORKSPACE_WRITE", "detail": path[:512]}
        if finding not in findings:
            findings.append(finding)
    return {
        "observed": observed,
        "findings": findings,
        "results": results,
        "before": before,
        "after": after,
        "changes": changes,
        "undeclared": undeclared,
        "stderr_sha256": session.stderr_sha256,
        "exit_code": session.returncode,
    }


def _base_record(kind: str, target: Target) -> dict[str, Any]:
    baseline = git_baseline(target.workspace)
    return {
        "schema_version": 1,
        "kind": kind,
        "lock": {"id": target.lock["id"], "sha256": target.lock_sha256},
        "source": {
            "repository": target.lock["source"]["repository"],
            "commit": target.lock["source"]["commit"],
            "license": target.lock["source"]["license"],
        },
        "copy_root": str(target.copy_root),
        "interpreter": interpreter(),
        "workspace": {"path": str(target.workspace), "commit": baseline["commit"]},
        "engineering_readiness": READINESS,
    }


def discover(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    """Discover selected servers; exit status 0 when all are available, otherwise 1."""
    record, base = load_request(request_path, "agent_discover_request", DISCOVER_FIELDS)
    target = _target(record, base)
    selected = record["servers"]
    if not isinstance(selected, list) or not selected or len(selected) > 32:
        raise InputError("LIMIT_EXCEEDED", "Select 1-32 servers", "/servers")
    if len(set(map(str, selected))) != len(selected):
        raise InputError("DUPLICATE_ID", "Duplicate selected server", "/servers")
    servers = [
        server_by_id(target.lock, item, f"/servers/{index}") for index, item in enumerate(selected)
    ]
    probes = record["probes"]
    if not isinstance(probes, list) or len(probes) > MAX_PROBES:
        raise InputError("LIMIT_EXCEEDED", "Too many probes", "/probes")
    calls: dict[str, list[tuple[str, dict[str, Any]]]] = {server["id"]: [] for server in servers}
    for index, raw in enumerate(probes):
        pointer = f"/probes/{index}"
        probe = exact(raw, {"server", "tool", "arguments"}, pointer)
        server = server_by_id(target.lock, probe["server"], pointer + "/server")
        if server["id"] not in calls:
            raise InputError("PROBE_FORBIDDEN", "Probe server is not selected", pointer)
        tool = next((item for item in server["tools"] if item["name"] == probe["tool"]), None)
        if tool is None or tool["classification"] != "context_read":
            raise InputError("PROBE_FORBIDDEN", "Only context_read tools may be probed", pointer)
        if not isinstance(probe["arguments"], dict) or len(canonical(probe["arguments"])) > 65536:
            raise InputError("FIELD_TYPE", "Probe arguments must be a bounded object", pointer)
        calls[server["id"]].append(
            (tool["name"], _substitute(probe["arguments"], target.workspace))
        )
    output = _base_record("agent_capability_inventory", target)
    copy_findings = verify_copy(target.lock, target.copy_root)
    entries = []
    probe_results: list[dict[str, Any]] = []
    for server in servers:
        entry: dict[str, Any] = {
            "id": server["id"],
            "status": "blocked",
            "observed": None,
            "findings": [],
            "workspace_changes": [],
            "exit_code": None,
            "stderr_sha256": None,
        }
        if server["status"] == "unsupported":
            entry["status"] = "unsupported"
            entry["findings"] = [{"code": "SERVER_UNSUPPORTED", "detail": server["id"]}]
        elif copy_findings:
            entry["findings"] = copy_findings
        else:
            result = _session(target, server, calls[server["id"]], server["startup_writes"])
            entry.update(
                {
                    "status": "blocked" if result["findings"] else "available",
                    "observed": result["observed"],
                    "findings": result["findings"],
                    "workspace_changes": result["changes"],
                    "exit_code": result["exit_code"],
                    "stderr_sha256": result["stderr_sha256"],
                }
            )
            probe_results.extend(result["results"])
        entries.append(entry)
    outcome = "available" if all(item["status"] == "available" for item in entries) else "blocked"
    output.update(
        {
            "servers": entries,
            "unsupported": [
                {"id": item["id"], "reason": item["unsupported_reason"]}
                for item in target.lock["servers"]
                if item["status"] == "unsupported"
            ],
            "probes": probe_results,
            "upstream_findings": upstream_findings(target.lock),
            "runtime_client": dict(target.lock["runtime_client"]),
            "outcome": outcome,
            "limitations": [
                "Servers ran from a verified disposable copy with the fabric interpreter; the "
                "upstream uvx launch was not executed.",
                "Tool results are context observations, not evidence or decisions.",
                "Fabro agent-side MCP compatibility is recorded, not demonstrated.",
            ],
        }
    )
    return (
        0 if outcome == "available" else 1,
        seal(output),
        target.inputs(),
        [*target.protected, target.copy_root, target.workspace],
    )


def setup(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    """Run one explicit, idempotent setup operation on a disposable Git workspace."""
    record, base = load_request(request_path, "agent_setup_request", SETUP_FIELDS)
    target = _target(record, base)
    operation_id = stable_id(record["operation"], "/operation")
    operation = next(
        (item for item in target.lock["setup_operations"] if item["id"] == operation_id), None
    )
    if operation is None:
        raise InputError("SETUP_UNSUPPORTED", "Setup operation is not in the lock", "/operation")
    server = server_by_id(target.lock, operation["server"], "/operation")
    output = _base_record("agent_setup_record", target)
    output["operation"] = {"id": operation["id"], "server": server["id"], "tool": operation["tool"]}
    findings = verify_copy(target.lock, target.copy_root)
    if server["status"] != "supported":
        findings.append({"code": "SERVER_UNSUPPORTED", "detail": server["id"]})
    result: dict[str, Any] | None = None
    if not findings:
        result = _session(
            target,
            server,
            [(operation["tool"], {"repo_path": str(target.workspace)})],
            [*operation["declared_writes"], *server["startup_writes"]],
        )
        findings = result["findings"]
        text = result["results"][0]["result_text"] if result["results"] else None
        if text is not None and not findings:
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = None
            if not isinstance(parsed, dict) or parsed.get("ok") is not True:
                findings.append({"code": "TOOL_CALL_FAILED", "detail": operation["tool"]})
    changes = [] if result is None else result["changes"]
    blocked = bool(findings)
    output.update(
        {
            "findings": findings,
            "before_digest": None if result is None else result["before"]["digest"],
            "after_digest": None if result is None else result["after"]["digest"],
            "changes": changes,
            "undeclared": [] if result is None else result["undeclared"],
            "tool_result": None
            if result is None or not result["results"]
            else result["results"][0],
            "outcome": "blocked" if blocked else ("changed" if changes else "unchanged"),
            "idempotent": not blocked and not changes,
            "limitations": [
                "Setup is a separate operator action and is never granted to an engineering role.",
                "Graph setup is unsupported: graphify is absent and installing it needs network "
                "access and a separate dependency decision.",
            ],
        }
    )
    return (
        1 if blocked else 0,
        seal(output),
        target.inputs(),
        [*target.protected, target.copy_root, target.workspace],
    )
