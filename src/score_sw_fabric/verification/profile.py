"""Pinned native verification rules and a recorded local C++ toolchain profile."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import relative_path, string_list
from score_sw_fabric.assurance.models import exact, nonempty, sha, stable_id, version
from score_sw_fabric.process_source.reader import InputError, read_bytes
from score_sw_fabric.runtime.request import parse_yaml
from score_sw_fabric.safety.native import list_table_rows

PROFILE_FIELDS = {
    "id",
    "status",
    "sources",
    "test_types",
    "derivation_techniques",
    "rules",
    "source_tags",
    "requirement_directives",
    "design",
    "inspection_checklist",
    "loop",
    "pending_obligations",
}
RULE_CHECKS = frozenset({"metadata_values", "metadata_required", "requirement_link"})
TOOLCHAIN_FIELDS = {
    "id",
    "status",
    "compiler",
    "test_library",
    "coverage_tool",
    "standard",
    "policy",
    "link_flags",
}
VALUE = re.compile(r"^\s*\*\s+.+\((?P<value>[a-z][a-z-]*)\)\s*$")
FLAG = re.compile(r"^-[A-Za-z0-9=+_,.-]+$")


def _sources(value: Any) -> set[str]:
    if not isinstance(value, list) or not value or len(value) > 32:
        raise InputError("LIMIT_EXCEEDED", "Profile sources must be bounded", "/sources")
    ids = set()
    for index, raw in enumerate(value):
        pointer = f"/sources/{index}"
        source = exact(raw, {"id", "repository", "commit", "path", "sha256"}, pointer)
        ids.add(stable_id(source["id"], pointer + "/id"))
        nonempty(source["repository"], pointer, max_length=512)
        if not isinstance(source["commit"], str) or not re.fullmatch(
            r"[0-9a-f]{40}", source["commit"]
        ):
            raise InputError("HASH_FORMAT", "Expected a full commit", pointer + "/commit")
        relative_path(source["path"], pointer + "/path")
        sha(source["sha256"], pointer + "/sha256")
    if len(ids) != len(value):
        raise InputError("DUPLICATE_ID", "Duplicate source", "/sources")
    return ids


def validate_profile(value: Any) -> dict[str, Any]:
    profile = version(value, "verification_profile", PROFILE_FIELDS, "/verification_profile")
    stable_id(profile["id"], "/id")
    nonempty(profile["status"], "/status", max_length=64)
    sources = _sources(profile["sources"])
    for key in ("test_types", "derivation_techniques", "source_tags", "requirement_directives"):
        items = string_list(profile[key], f"/{key}", limit=32, length=64)
        if not items or len(set(items)) != len(items):
            raise InputError("PROFILE_FIELD", f"{key} must be unique and non-empty", f"/{key}")
    rules = profile["rules"]
    if (
        not isinstance(rules, list)
        or {rule.get("check") for rule in rules if isinstance(rule, dict)} != RULE_CHECKS
    ):
        raise InputError("PROFILE_FIELD", "Profile must bind every native metadata rule", "/rules")
    for index, raw in enumerate(rules):
        rule = exact(raw, {"id", "check", "source"}, f"/rules/{index}")
        stable_id(rule["id"], f"/rules/{index}/id")
        if rule["source"] not in sources:
            raise InputError("FIELD_ENUM", "Rule source is not pinned", f"/rules/{index}")
    design = exact(
        profile["design"], {"work_product", "sections", "diagram_directives", "source"}, "/design"
    )
    stable_id(design["work_product"], "/design/work_product")
    string_list(design["sections"], "/design/sections", limit=16, length=128)
    string_list(design["diagram_directives"], "/design/diagram_directives", limit=8, length=32)
    if design["source"] not in sources:
        raise InputError("FIELD_ENUM", "Design source is not pinned", "/design/source")
    checklist = profile["inspection_checklist"]
    if not isinstance(checklist, list) or not checklist or len(checklist) > 64:
        raise InputError("LIMIT_EXCEEDED", "Checklist must be bounded", "/inspection_checklist")
    for index, raw in enumerate(checklist):
        item = exact(raw, {"id", "criterion", "source"}, f"/inspection_checklist/{index}")
        nonempty(item["id"], f"/inspection_checklist/{index}/id", max_length=32)
        nonempty(item["criterion"], f"/inspection_checklist/{index}/criterion", max_length=1024)
        if item["source"] not in sources:
            raise InputError(
                "FIELD_ENUM", "Checklist source is not pinned", "/inspection_checklist"
            )
    loop = exact(profile["loop"], {"max_attempts"}, "/loop")
    if type(loop["max_attempts"]) is not int or not 1 <= loop["max_attempts"] <= 20:
        raise InputError("LIMIT_EXCEEDED", "Attempt budget must be 1-20", "/loop/max_attempts")
    obligations = profile["pending_obligations"]
    if not isinstance(obligations, list) or not obligations or len(obligations) > 64:
        raise InputError(
            "LIMIT_EXCEEDED", "Pending obligations must be bounded", "/pending_obligations"
        )
    for index, raw in enumerate(obligations):
        item = exact(raw, {"id", "description", "owner"}, f"/pending_obligations/{index}")
        stable_id(item["id"], f"/pending_obligations/{index}/id")
        nonempty(item["description"], f"/pending_obligations/{index}", max_length=512)
        nonempty(item["owner"], f"/pending_obligations/{index}", max_length=128)
    return profile


def load_profile(data: bytes) -> dict[str, Any]:
    return validate_profile(parse_yaml(data, "/verification_profile"))


def _file(value: Any, pointer: str) -> dict[str, str]:
    record = exact(value, {"path", "sha256"}, pointer)
    nonempty(record["path"], pointer + "/path", max_length=1024)
    if not record["path"].startswith("/"):
        raise InputError("INPUT_PATH", "Toolchain paths must be absolute", pointer + "/path")
    sha(record["sha256"], pointer + "/sha256")
    return record


def validate_toolchain(value: Any) -> dict[str, Any]:
    toolchain = version(value, "cpp_toolchain_profile", TOOLCHAIN_FIELDS, "/cpp_toolchain_profile")
    stable_id(toolchain["id"], "/id")
    nonempty(toolchain["status"], "/status", max_length=64)
    for key in ("compiler", "coverage_tool"):
        tool = exact(toolchain[key], {"path", "sha256", "version"}, f"/{key}")
        _file({"path": tool["path"], "sha256": tool["sha256"]}, f"/{key}")
        nonempty(tool["version"], f"/{key}/version", max_length=256)
    library = exact(
        toolchain["test_library"],
        {"name", "version", "include", "header", "libraries"},
        "/test_library",
    )
    nonempty(library["name"], "/test_library/name", max_length=64)
    nonempty(library["version"], "/test_library/version", max_length=64)
    if not isinstance(library["include"], str) or not library["include"].startswith("/"):
        raise InputError("INPUT_PATH", "Include path must be absolute", "/test_library/include")
    _file(library["header"], "/test_library/header")
    libraries = library["libraries"]
    if not isinstance(libraries, list) or not libraries or len(libraries) > 8:
        raise InputError(
            "LIMIT_EXCEEDED", "Test libraries must be bounded", "/test_library/libraries"
        )
    for index, item in enumerate(libraries):
        _file(item, f"/test_library/libraries/{index}")
    if toolchain["standard"] != "c++17":
        raise InputError("FIELD_ENUM", "Only C++17 is selected", "/standard")
    policy = exact(
        toolchain["policy"],
        {"source", "selected_levels", "unavailable_levels", "flags", "unsupported_flags"},
        "/policy",
    )
    source = exact(policy["source"], {"repository", "commit", "path", "sha256"}, "/policy/source")
    relative_path(source["path"], "/policy/source/path")
    sha(source["sha256"], "/policy/source/sha256")
    for key in ("selected_levels", "unavailable_levels", "flags", "unsupported_flags"):
        string_list(policy[key], f"/policy/{key}", limit=200, length=128)
    for key in ("flags", "unsupported_flags"):
        for flag in policy[key]:
            if FLAG.fullmatch(flag) is None:
                raise InputError("FIELD_TYPE", "Invalid compiler flag", f"/policy/{key}")
    if set(policy["flags"]) & set(policy["unsupported_flags"]):
        raise InputError(
            "PROFILE_FIELD", "A flag cannot be both selected and unsupported", "/policy"
        )
    for flag in string_list(toolchain["link_flags"], "/link_flags", limit=16, length=128):
        if FLAG.fullmatch(flag) is None:
            raise InputError("FIELD_TYPE", "Invalid link flag", "/link_flags")
    return toolchain


def load_toolchain(data: bytes) -> dict[str, Any]:
    return validate_toolchain(parse_yaml(data, "/cpp_toolchain_profile"))


def _digest(path: str) -> str:
    return hashlib.sha256(read_bytes(Path(path).resolve())).hexdigest()


def tool_version(path: str) -> str:
    try:
        completed = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InputError("TOOLCHAIN_UNAVAILABLE", "Tool did not report a version") from exc
    return completed.stdout.splitlines()[0].strip() if completed.stdout else ""


def verify_toolchain(toolchain: dict[str, Any]) -> dict[str, Any]:
    """Require the host tools to match the profile exactly; return the observed identity."""
    observed: dict[str, Any] = {}
    for key in ("compiler", "coverage_tool"):
        tool = toolchain[key]
        try:
            digest = _digest(tool["path"])
        except InputError as exc:
            raise InputError("TOOLCHAIN_UNAVAILABLE", f"{key} is unavailable", f"/{key}") from exc
        if digest != tool["sha256"] or tool_version(tool["path"]) != tool["version"]:
            raise InputError("TOOLCHAIN_MISMATCH", f"{key} differs from its profile", f"/{key}")
        observed[key] = {
            "path": tool["path"],
            "resolved": str(Path(tool["path"]).resolve()),
            "sha256": digest,
            "version": tool["version"],
        }
    library = toolchain["test_library"]
    for index, item in enumerate([library["header"], *library["libraries"]]):
        try:
            digest = _digest(item["path"])
        except InputError as exc:
            raise InputError(
                "TOOLCHAIN_UNAVAILABLE", "Test library is unavailable", f"/test_library/{index}"
            ) from exc
        if digest != item["sha256"]:
            raise InputError(
                "TOOLCHAIN_MISMATCH",
                "Test library differs from its profile",
                f"/test_library/{index}",
            )
    observed["test_library"] = {
        "name": library["name"],
        "version": library["version"],
        "header_sha256": library["header"]["sha256"],
        "libraries": [item["sha256"] for item in library["libraries"]],
    }
    return observed


def extract_values(text: str, heading: str) -> list[str]:
    """Values in parentheses from a bullet list under `* <heading>` in the native rule text."""
    values: list[str] = []
    active = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("* "):
            if stripped == f"* {heading}":
                active = True
                continue
            match = VALUE.match(line)
            if active and match and line.startswith(" " * 8):
                values.append(match.group("value"))
                continue
            if active and not line.startswith(" " * 8):
                active = False
    return values


def extract_tags(text: str) -> list[str]:
    block = text[text.index("TAGS = [") : text.index("]", text.index("TAGS = ["))]
    return [a + b for a, b in re.findall(r'"([^"]*)"\s*\+\s*"([^"]*)"', block)]


def extract_checklist(text: str) -> list[dict[str, str]]:
    body = text[text.index(".. list-table:: Implementation Checklist") :].split("\n", 1)[1]
    rows = list_table_rows(body, header_rows=0)
    header = rows[0]["cells"]
    identifier = header.index("Review ID")
    criterion = header.index("Acceptance Criteria")
    return [
        {"id": row["cells"][identifier], "criterion": row["cells"][criterion]}
        for row in rows[1:]
        if len(row["cells"]) > criterion and row["cells"][identifier].startswith("IMPL_")
    ]


def extract_policy(text: str, levels: list[str]) -> list[str]:
    flags: list[str] = []
    for name, args in re.findall(r'cc_args\(\s*name = "([^"]+)",.*?args = \[(.*?)\]', text, re.S):
        selected = {
            name
            for level in levels
            for name in (f"{level}_args", f"{level}_warnings_args", f"{level}_cxx_warnings_args")
        }
        if name in selected:
            flags.extend(re.findall(r'"(-[^"]+)"', args))
    return flags
