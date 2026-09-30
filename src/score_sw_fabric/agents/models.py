"""Shared version-1 agent request loading, safe paths, snapshots and Git baselines."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import exact, nonempty, seal, sha, version
from score_sw_fabric.process_source.reader import InputError, read_bytes
from score_sw_fabric.runtime.request import _local, _no_links, parse_json, parse_yaml

MAX_REQUEST_BYTES = 1024 * 1024
MAX_LIST = 1000
MAX_SNAPSHOT_FILES = 20_000
MAX_SNAPSHOT_BYTES = 256 * 1024 * 1024
PROTECTED_WORKSPACE_GLOBS = (".git", ".git/**")
GIT_SURFACE_DIRECTORIES = frozenset({"hooks", "info"})
GIT_SURFACE_FILES = frozenset({"config"})
GIT_TIMEOUT_SECONDS = 30
READINESS = "not_evaluated"


def bounded_diagnostic(error: InputError) -> dict[str, str]:
    """Return a stable-sized diagnostic that names the refusal without echoing input content."""
    code = str(error.code)[:128]
    return {
        "code": code,
        "pointer": str(error.pointer)[:256],
        "message": f"Agent input rejected ({code}).",
    }


def load_request(path: Path, kind: str, fields: set[str]) -> tuple[dict[str, Any], Path]:
    """Read one exact version-1 YAML request and return it with its resolution base."""
    selected = _no_links(path, "/request")
    data = read_bytes(selected)
    if len(data) > MAX_REQUEST_BYTES:
        raise InputError("LIMIT_EXCEEDED", "Agent request exceeds 1 MiB", "/request")
    record = version(parse_yaml(data, "/request"), kind, fields, "/request")
    return record, selected.parent


def input_file(base: Path, value: Any, pointer: str) -> tuple[Path, bytes]:
    """Read a `{path, sha256}` selection and require exact bytes."""
    record = exact(value, {"path", "sha256"}, pointer)
    path = _local(base, record["path"], pointer + "/path")
    data = read_bytes(path)
    if hashlib.sha256(data).hexdigest() != sha(record["sha256"], pointer + "/sha256"):
        raise InputError("INPUT_DRIFT", f"Input bytes changed at {pointer}", pointer)
    return path, data


def yaml_file(base: Path, value: Any, pointer: str) -> tuple[Path, bytes, dict[str, Any]]:
    path, data = input_file(base, value, pointer)
    parsed = parse_yaml(data, pointer)
    if not isinstance(parsed, dict):
        raise InputError("YAML_ROOT", f"Expected a mapping at {pointer}", pointer)
    return path, data, parsed


def json_file(base: Path, value: Any, pointer: str) -> tuple[Path, bytes, dict[str, Any]]:
    path, data = input_file(base, value, pointer)
    parsed = parse_json(data, pointer)
    if not isinstance(parsed, dict):
        raise InputError("JSON_ROOT", f"Expected an object at {pointer}", pointer)
    return path, data, parsed


def local_dir(base: Path, raw: Any, pointer: str) -> Path:
    path = _local(base, raw, pointer)
    if not path.is_dir():
        raise InputError("INPUT_NOT_DIRECTORY", f"Expected a directory at {pointer}", pointer)
    return path.resolve()


def protected_roots(base: Path, value: Any, pointer: str) -> list[Path]:
    if not isinstance(value, list) or len(value) > 100:
        raise InputError("LIMIT_EXCEEDED", "Too many protected roots", pointer)
    return [_local(base, item, f"{pointer}/{index}").resolve() for index, item in enumerate(value)]


def separate_roots(named: dict[str, Path], protected: list[Path]) -> None:
    """Require named working roots to be disjoint from each other and from protected roots."""
    items = list(named.items())
    for index, (name, path) in enumerate(items):
        for root in protected:
            if path.is_relative_to(root) or root.is_relative_to(path):
                raise InputError("PROTECTED_ROOT", f"{name} overlaps a protected root", f"/{name}")
        for other_name, other in items[index + 1 :]:
            if path.is_relative_to(other) or other.is_relative_to(path):
                raise InputError(
                    "ROOT_OVERLAP", f"{name} and {other_name} overlap", f"/{other_name}"
                )


def string_list(
    value: Any, pointer: str, *, limit: int = MAX_LIST, length: int = 1024
) -> list[str]:
    if not isinstance(value, list) or len(value) > limit:
        raise InputError("LIMIT_EXCEEDED", f"Expected a bounded list at {pointer}", pointer)
    return [
        nonempty(item, f"{pointer}/{index}", max_length=length) for index, item in enumerate(value)
    ]


def relative_path(value: Any, pointer: str) -> str:
    """Validate a workspace-relative POSIX path without traversal or empty segments."""
    text = nonempty(value, pointer, max_length=1024)
    parts = text.split("/")
    if (
        text.startswith("/")
        or "\\" in text
        or "\x00" in text
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise InputError("INPUT_PATH", f"Unsafe relative path at {pointer}", pointer)
    return text


def glob_list(value: Any, pointer: str) -> list[str]:
    """Validate relative globs; `**` matches whole segments only."""
    globs = string_list(value, pointer, limit=200, length=512)
    for index, item in enumerate(globs):
        relative_path(item, f"{pointer}/{index}")
        if any("**" in part and part != "**" for part in item.split("/")):
            raise InputError("GLOB_FORMAT", f"`**` must be a whole segment at {pointer}", pointer)
    if len(set(globs)) != len(globs):
        raise InputError("DUPLICATE_ID", f"Duplicate glob at {pointer}", pointer)
    return globs


def glob_match(pattern: str, path: str) -> bool:
    def match(pattern_parts: list[str], path_parts: list[str]) -> bool:
        if not pattern_parts:
            return not path_parts
        head, rest = pattern_parts[0], pattern_parts[1:]
        if head == "**":
            return any(match(rest, path_parts[index:]) for index in range(len(path_parts) + 1))
        return (
            bool(path_parts)
            and fnmatch.fnmatchcase(path_parts[0], head)
            and match(rest, path_parts[1:])
        )

    return match(pattern.split("/"), path.split("/"))


def matches_any(patterns: list[str] | tuple[str, ...], path: str) -> bool:
    return any(glob_match(pattern, path) for pattern in patterns)


def snapshot(root: Path) -> dict[str, Any]:
    """Record workspace files, links and directories with size and SHA-256.

    Inside `.git` only the executable/configuration surface (`config`, `hooks/`, `info/`) is
    recorded; objects, refs and the index change with ordinary Git reads and commits, and the
    commit itself is compared separately.
    """
    entries: list[dict[str, Any]] = []
    total = 0
    for current, directories, files in os.walk(root, followlinks=False):
        relative_dir = Path(current).relative_to(root)
        if relative_dir == Path(".git"):
            directories[:] = [name for name in directories if name in GIT_SURFACE_DIRECTORIES]
            files = [name for name in files if name in GIT_SURFACE_FILES]
        linked = [name for name in directories if (Path(current) / name).is_symlink()]
        for name in sorted(set(directories) - set(linked)):
            entries.append(
                {
                    "path": (relative_dir / name).as_posix(),
                    "kind": "directory",
                    "size": 0,
                    "sha256": hashlib.sha256(b"").hexdigest(),
                }
            )
        for name in sorted([*files, *linked]):
            full = Path(current) / name
            relative = (relative_dir / name).as_posix()
            if full.is_symlink():
                payload = os.readlink(full).encode("utf-8", "surrogateescape")
                kind = "symlink"
            elif full.is_file():
                if full.stat().st_size > MAX_SNAPSHOT_BYTES:
                    raise InputError("LIMIT_EXCEEDED", "Workspace file exceeds snapshot limit")
                payload = full.read_bytes()
                kind = "file"
            else:
                payload = b""
                kind = "other"
            total += len(payload)
            entries.append(
                {
                    "path": relative,
                    "kind": kind,
                    "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
            if len(entries) > MAX_SNAPSHOT_FILES or total > MAX_SNAPSHOT_BYTES:
                raise InputError("LIMIT_EXCEEDED", "Workspace exceeds snapshot limits")
        directories[:] = [name for name in directories if name not in linked]
    entries.sort(key=lambda item: item["path"])
    return seal({"files": entries})


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, str]]:
    old = {item["path"]: item for item in before["files"]}
    new = {item["path"]: item for item in after["files"]}
    changes = []
    for path in sorted(set(old) | set(new)):
        if path not in new:
            changes.append({"path": path, "change": "removed"})
        elif path not in old:
            changes.append({"path": path, "change": "added"})
        elif (old[path]["kind"], old[path]["sha256"]) != (new[path]["kind"], new[path]["sha256"]):
            changes.append({"path": path, "change": "modified"})
    return changes


def _git(workspace: Path, *arguments: str) -> bytes:
    environment = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0",
        "HOME": str(workspace),
    }
    try:
        completed = subprocess.run(
            ["git", "-C", str(workspace), *arguments],
            capture_output=True,
            env=environment,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InputError("GIT_UNAVAILABLE", "Git inspection failed", "/workspace") from exc
    if completed.returncode != 0:
        raise InputError("WORKSPACE_NOT_GIT", "Workspace Git inspection failed", "/workspace")
    return completed.stdout


def git_baseline(workspace: Path) -> dict[str, Any]:
    """Read the workspace commit, tracked paths and dirty paths without writing to Git."""
    top = _git(workspace, "rev-parse", "--show-toplevel").decode().strip()
    if Path(top).resolve() != workspace.resolve():
        raise InputError("WORKSPACE_NOT_GIT", "Workspace must be a Git top level", "/workspace")
    commit = _git(workspace, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    tracked = sorted(
        item for item in _git(workspace, "ls-files", "-z").decode().split("\0") if item
    )
    dirty = set()
    records = _git(
        workspace, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames"
    ).decode()
    for record in records.split("\0"):
        if record:
            dirty.add(record[3:])
    return {"commit": commit, "tracked": tracked, "dirty_paths": sorted(dirty)}
