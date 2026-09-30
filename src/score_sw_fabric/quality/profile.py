"""Exact candidate policy/tool selections, with native statuses and explicit gaps."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import relative_path, string_list
from score_sw_fabric.assurance.models import exact, nonempty, sha, stable_id, version
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.request import _no_links, parse_yaml

PROFILE_FIELDS = {
    "id",
    "status",
    "native_sources",
    "language",
    "guideline_edition",
    "mapping_state",
    "decision_policy_ref",
    "required_obligations",
    "analyzers",
    "sanitizers",
}
TOOLCHAIN_FIELDS = {"id", "status", "tool", "dependencies", "library_dirs"}


def absolute_file(value: Any, pointer: str) -> dict[str, Any]:
    record = exact(value, {"path", "sha256"}, pointer)
    text = nonempty(record["path"], pointer + "/path", max_length=1024)
    if not text.startswith("/") or ".." in Path(text).parts or "\x00" in text:
        raise InputError("INPUT_PATH", "Tool paths must be absolute", pointer)
    _no_links(Path(text), pointer)
    sha(record["sha256"], pointer + "/sha256")
    return record


def load_profile(data: bytes) -> dict[str, Any]:
    p = version(parse_yaml(data, "/profile"), "quality_profile", PROFILE_FIELDS, "/profile")
    stable_id(p["id"], "/profile/id")
    nonempty(p["status"], "/profile/status", max_length=64)
    if (
        p["language"] != "c++17"
        or p["guideline_edition"] != "MISRA C++:2023"
        or p["mapping_state"] != "unknown"
        or p["decision_policy_ref"] is not None
    ):
        raise InputError(
            "PROFILE_UNSUPPORTED", "Only the unmapped draft C++17 profile is supported"
        )
    sources = p["native_sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 32:
        raise InputError("LIMIT_EXCEEDED", "Native sources must be bounded")
    seen = set()
    for raw in sources:
        s = exact(
            raw,
            {"id", "repository", "commit", "path", "sha256", "native_status", "license", "notice"},
            "/native_sources",
        )
        identifier = stable_id(s["id"], "/native_sources/id")
        if identifier in seen:
            raise InputError("DUPLICATE_ID", "Duplicate native source")
        seen.add(identifier)
        for key in ("repository", "native_status", "license", "notice"):
            nonempty(s[key], f"/native_sources/{key}", max_length=1024)
        if not isinstance(s["commit"], str) or re.fullmatch(r"[a-f0-9]{40}", s["commit"]) is None:
            raise InputError("HASH_FORMAT", "Native commit must be full")
        relative_path(s["path"], "/native_sources/path")
        sha(s["sha256"], "/native_sources/sha256")
    if "clang_tidy" not in seen:
        raise InputError("PROFILE_FIELD", "Clang-Tidy configuration source is missing")
    string_list(p["required_obligations"], "/required_obligations", limit=64, length=128)
    for key, fields in [("analyzers", {"id", "role", "state"}), ("sanitizers", {"id", "state"})]:
        items = p[key]
        if not isinstance(items, list) or len(items) > 32:
            raise InputError("LIMIT_EXCEEDED", "Too many tools")
        ids = set()
        for raw in items:
            item = exact(raw, fields, f"/{key}")
            identifier = stable_id(item["id"], f"/{key}/id")
            if identifier in ids:
                raise InputError("DUPLICATE_ID", "Duplicate tool")
            ids.add(identifier)
            if item["state"] not in {"candidate", "unimplemented", "unavailable", "unknown"}:
                raise InputError("FIELD_ENUM", "Unknown tool state")
            if key == "analyzers" and item["role"] not in {"primary", "complementary"}:
                raise InputError("FIELD_ENUM", "Unknown tool role")
    if not any(a["id"] == "clang-tidy" and a["role"] == "complementary" for a in p["analyzers"]):
        raise InputError("PROFILE_FIELD", "Clang-Tidy must remain complementary")
    return p


def load_toolchain(data: bytes, kind: str = "quality_toolchain_profile") -> dict[str, Any]:
    p = version(parse_yaml(data, "/toolchain"), kind, TOOLCHAIN_FIELDS, "/toolchain")
    stable_id(p["id"], "/toolchain/id")
    nonempty(p["status"], "/toolchain/status", max_length=64)
    tool = exact(p["tool"], {"path", "sha256", "version"}, "/tool")
    absolute_file({"path": tool["path"], "sha256": tool["sha256"]}, "/tool")
    nonempty(tool["version"], "/tool/version", max_length=256)
    deps = p["dependencies"]
    if not isinstance(deps, list) or len(deps) > 32:
        raise InputError("LIMIT_EXCEEDED", "Too many runtime assets")
    paths = []
    for dep in deps:
        paths.append(absolute_file(dep, "/dependencies")["path"])
    if len(set(paths)) != len(paths):
        raise InputError("DUPLICATE_ID", "Duplicate runtime asset")
    dirs = string_list(p["library_dirs"], "/library_dirs", limit=8)
    for d in dirs:
        absolute_file({"path": d, "sha256": "0" * 64}, "/library_dirs")
        if not Path(d).is_dir():
            raise InputError("INPUT_NOT_DIRECTORY", "Library directory is unavailable")
    if kind == "quality_toolchain_profile" and any(
        not any(Path(d).is_relative_to(Path(lib)) for lib in dirs) for d in paths
    ):
        raise InputError("INPUT_PATH", "Runtime asset outside selected library directories")
    return p
