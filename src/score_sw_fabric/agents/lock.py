"""Reviewed S-CORE APM/MCP context-package lock and disposable-copy verification."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import glob_list, relative_path, string_list
from score_sw_fabric.assurance.models import (
    bounded_limits,
    exact,
    nonempty,
    sha,
    stable_id,
    version,
)
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError, read_bytes
from score_sw_fabric.runtime.request import parse_yaml

LOCK_FIELDS = {
    "id",
    "status",
    "source",
    "files",
    "servers",
    "setup_operations",
    "runtime_client",
    "limits",
}
SERVER_FIELDS = {
    "id",
    "package",
    "manifest",
    "status",
    "unsupported_reason",
    "upstream_launch",
    "launch",
    "expected",
    "startup_writes",
    "tools",
}
CLASSIFICATIONS = frozenset({"context_read", "local_observation_write", "setup_privileged"})
LOCK_LIMITS = {
    "handshake_seconds": 120,
    "tool_seconds": 600,
    "line_bytes": 16 * 1024 * 1024,
    "result_bytes": 1024 * 1024,
}
MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
PINNED_GIT = re.compile(r"@[0-9a-f]{40}(#|$)")
MAX_TOOLS = 256


def tool_digest(tool: Any) -> str:
    """SHA-256 of one advertised MCP tool object in canonical JSON."""
    return hashlib.sha256(canonical(tool)).hexdigest()


def _server(value: Any, pointer: str) -> dict[str, Any]:
    server = exact(value, SERVER_FIELDS, pointer)
    stable_id(server["id"], pointer + "/id")
    nonempty(server["package"], pointer + "/package", max_length=128)
    relative_path(server["manifest"], pointer + "/manifest")
    if server["status"] not in {"supported", "unsupported"}:
        raise InputError("FIELD_ENUM", f"Unsupported server status at {pointer}", pointer)
    upstream = exact(server["upstream_launch"], {"command", "args"}, pointer + "/upstream_launch")
    nonempty(upstream["command"], pointer + "/upstream_launch/command", max_length=256)
    string_list(upstream["args"], pointer + "/upstream_launch/args", limit=64)
    if server["status"] == "unsupported":
        nonempty(server["unsupported_reason"], pointer + "/unsupported_reason", max_length=1024)
        if server["launch"] is not None or server["tools"]:
            raise InputError("LOCK_UNSUPPORTED", f"Unsupported server has launch at {pointer}")
    else:
        if server["unsupported_reason"] is not None:
            raise InputError("FIELD_TYPE", f"Supported server has a reason at {pointer}", pointer)
        launch = exact(server["launch"], {"kind", "python_path", "module"}, pointer + "/launch")
        if launch["kind"] != "python_module":
            raise InputError("LAUNCH_UNSUPPORTED", f"Only python_module launch at {pointer}")
        for index, item in enumerate(string_list(launch["python_path"], pointer, limit=8)):
            relative_path(item, f"{pointer}/launch/python_path/{index}")
        if not isinstance(launch["module"], str) or MODULE.fullmatch(launch["module"]) is None:
            raise InputError("FIELD_TYPE", f"Invalid module at {pointer}/launch/module")
    expected = exact(
        server["expected"], {"server_name", "server_version", "protocol_version"}, pointer
    )
    for name, item in expected.items():
        if item is not None or server["status"] == "supported":
            nonempty(item, f"{pointer}/expected/{name}", max_length=128)
    glob_list(server["startup_writes"], pointer + "/startup_writes")
    tools = server["tools"]
    if not isinstance(tools, list) or len(tools) > MAX_TOOLS:
        raise InputError("LIMIT_EXCEEDED", f"Too many tools at {pointer}", pointer)
    names = set()
    for index, raw in enumerate(tools):
        tool = exact(raw, {"name", "classification", "schema_sha256"}, f"{pointer}/tools/{index}")
        nonempty(tool["name"], f"{pointer}/tools/{index}/name", max_length=128)
        if tool["classification"] not in CLASSIFICATIONS:
            raise InputError("FIELD_ENUM", f"Unknown classification at {pointer}/tools/{index}")
        sha(tool["schema_sha256"], f"{pointer}/tools/{index}/schema_sha256")
        names.add(tool["name"])
    if len(names) != len(tools):
        raise InputError("DUPLICATE_ID", f"Duplicate tool at {pointer}", pointer)
    return server


def validate_lock(value: Any) -> dict[str, Any]:
    lock = version(value, "apm_context_lock", LOCK_FIELDS, "/apm_context_lock")
    stable_id(lock["id"], "/id")
    nonempty(lock["status"], "/status", max_length=64)
    source = exact(
        lock["source"],
        {"repository", "commit", "license", "license_path", "notice_path"},
        "/source",
    )
    nonempty(source["repository"], "/source/repository", max_length=512)
    commit = source["commit"]
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise InputError("HASH_FORMAT", "Expected a full source commit", "/source/commit")
    nonempty(source["license"], "/source/license", max_length=64)
    files = lock["files"]
    if not isinstance(files, list) or not files or len(files) > 1000:
        raise InputError("LIMIT_EXCEEDED", "Lock files must be a bounded non-empty list", "/files")
    paths = []
    for index, raw in enumerate(files):
        item = exact(raw, {"path", "sha256"}, f"/files/{index}")
        paths.append(relative_path(item["path"], f"/files/{index}/path"))
        sha(item["sha256"], f"/files/{index}/sha256")
    if len(set(paths)) != len(paths):
        raise InputError("DUPLICATE_ID", "Duplicate locked file", "/files")
    for name in ("license_path", "notice_path"):
        if relative_path(source[name], f"/source/{name}") not in paths:
            raise InputError("LOCK_INCOMPLETE", f"{name} is not a locked file", f"/source/{name}")
    servers = lock["servers"]
    if not isinstance(servers, list) or not servers or len(servers) > 32:
        raise InputError("LIMIT_EXCEEDED", "Lock servers must be bounded", "/servers")
    ids = [_server(item, f"/servers/{index}")["id"] for index, item in enumerate(servers)]
    if len(set(ids)) != len(ids):
        raise InputError("DUPLICATE_ID", "Duplicate server ID", "/servers")
    for index, server in enumerate(servers):
        if server["manifest"] not in paths:
            raise InputError("LOCK_INCOMPLETE", "Manifest is not locked", f"/servers/{index}")
        launch = server["launch"]
        if launch is not None:
            module = launch["module"].replace(".", "/")
            candidates = {
                f"{prefix.rstrip('/')}/{module}{suffix}"
                for prefix in launch["python_path"]
                for suffix in (".py", "/__init__.py", "/__main__.py")
            }
            if not candidates & set(paths):
                raise InputError(
                    "LOCK_INCOMPLETE", "Launch module is not locked", f"/servers/{index}"
                )
    operations = lock["setup_operations"]
    if not isinstance(operations, list) or len(operations) > 16:
        raise InputError("LIMIT_EXCEEDED", "Too many setup operations", "/setup_operations")
    for index, raw in enumerate(operations):
        pointer = f"/setup_operations/{index}"
        item = exact(raw, {"id", "server", "tool", "declared_writes"}, pointer)
        stable_id(item["id"], pointer + "/id")
        glob_list(item["declared_writes"], pointer + "/declared_writes")
        server = server_by_id(lock, item["server"], pointer + "/server")
        tool = next((tool for tool in server["tools"] if tool["name"] == item["tool"]), None)
        if tool is None or tool["classification"] != "setup_privileged":
            raise InputError("LOCK_INCOMPLETE", "Setup tool must be setup_privileged", pointer)
    client = exact(
        lock["runtime_client"], {"name", "protocol_version", "compatibility"}, "/runtime_client"
    )
    for name in ("name", "protocol_version"):
        nonempty(client[name], f"/runtime_client/{name}", max_length=64)
    if client["compatibility"] not in {"not_verified", "verified"}:
        raise InputError("FIELD_ENUM", "Unknown compatibility", "/runtime_client/compatibility")
    bounded_limits(lock["limits"], LOCK_LIMITS, "/limits")
    if any(lock["limits"][name] == 0 for name in LOCK_LIMITS):
        raise InputError("LIMIT_EXCEEDED", "Lock limits must be positive", "/limits")
    return lock


def load_lock(data: bytes) -> dict[str, Any]:
    return validate_lock(parse_yaml(data, "/apm_context_lock"))


def server_by_id(lock: dict[str, Any], server_id: Any, pointer: str) -> dict[str, Any]:
    for server in lock["servers"]:
        if server["id"] == server_id:
            selected: dict[str, Any] = server
            return selected
    raise InputError("SERVER_UNKNOWN", "Server is not in the lock", pointer)


def verify_copy(lock: dict[str, Any], copy_root: Path) -> list[dict[str, str]]:
    """Return drift findings for locked files and manifest launch records in a disposable copy."""
    findings = []
    for item in lock["files"]:
        path = copy_root / item["path"]
        try:
            for parent in (path, *path.parents):
                if parent == copy_root:
                    break
                if parent.is_symlink():
                    raise InputError("INPUT_ALIAS", "Locked path is a link")
            observed = hashlib.sha256(read_bytes(path)).hexdigest()
        except InputError:
            observed = None
        if observed != item["sha256"]:
            findings.append({"code": "LOCK_FILE_DRIFT", "detail": item["path"]})
    if findings:
        return findings
    for server in lock["servers"]:
        manifest = parse_yaml(read_bytes(copy_root / server["manifest"]), "/manifest")
        entries = (
            manifest.get("dependencies", {}).get("mcp", []) if isinstance(manifest, dict) else []
        )
        entry = next(
            (
                item
                for item in entries
                if isinstance(item, dict) and item.get("name") == server["package"]
            ),
            None,
        )
        recorded = (
            None if entry is None else {"command": entry.get("command"), "args": entry.get("args")}
        )
        if recorded != server["upstream_launch"]:
            findings.append({"code": "MANIFEST_LAUNCH_DRIFT", "detail": server["id"]})
    return findings


def upstream_findings(lock: dict[str, Any]) -> list[dict[str, str]]:
    """Name upstream launch references that do not pin a revision; they are never executed."""
    findings = []
    for server in lock["servers"]:
        args = server["upstream_launch"]["args"]
        if any(arg.startswith("git+") and PINNED_GIT.search(arg) is None for arg in args):
            findings.append({"code": "UPSTREAM_LAUNCH_UNPINNED", "detail": server["id"]})
    return findings
