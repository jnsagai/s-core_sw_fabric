"""Private operator inputs for a scoped experiment, never engineering acceptance.

The operator supplies the checksum in the native hook command. File permissions and
workspace exclusion protect against ordinary workspace writes; they are not an OS
security boundary against another process running as the operator's Unix account.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, json_object


def private_file(path: Path) -> bytes:
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise OptimizationError("PRIVATE_INSTRUCTION_REQUIRED")
    details = path.stat()
    parent = path.parent.stat()
    if (
        not stat.S_ISREG(details.st_mode)
        or details.st_uid != os.getuid()
        or details.st_mode & 0o077
        or parent.st_uid != os.getuid()
        or parent.st_mode & 0o077
    ):
        raise OptimizationError("PRIVATE_INSTRUCTION_REQUIRED")
    return path.read_bytes()


def verify_instruction(path: Path, expected_sha256: str) -> dict[str, Any]:
    raw = private_file(path)
    if (
        not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        or hashlib.sha256(raw).hexdigest() != expected_sha256
    ):
        raise OptimizationError("INSTRUCTION_DIGEST")
    value = json_object(raw)
    if (
        value.get("kind") != "qualification_instruction"
        or value.get("scope") != "qualification_only"
        or value.get("provider") != "deepseek"
        or value.get("owner_instructions") != ["go", "deepseek flash only"]
        or set(value.get("models", [])) != {"deepseek-flash", "deepseek-v4-flash"}
    ):
        raise OptimizationError("QUALIFICATION_SCOPE")
    workspace = Path(value["workspace"]).resolve(strict=True)
    if (workspace / "storage-selection.json").exists():
        from score_sw_fabric.storage import validate_run_root

        validate_run_root(workspace)
    if path.is_relative_to(workspace):
        raise OptimizationError("INSTRUCTION_IN_WORKSPACE")
    bound_digests = set()
    for filename, digest in value["files"].items():
        content = private_file(Path(filename))
        if hashlib.sha256(content).hexdigest() != digest:
            raise OptimizationError("ACTIVATION_FILE_DRIFT")
        bound_digests.add(digest)
        if content.startswith(b"{"):
            from score_sw_fabric.optimization.common import checked

            candidate = json_object(content)
            if "digest" in candidate:
                bound_digests.add(checked(candidate)["digest"])
    for name in ("governor", "context", "role", "skills"):
        if not re.fullmatch(r"[0-9a-f]{64}", value["bindings"][name]):
            raise OptimizationError("ACTIVATION_BINDING")
        if value["bindings"][name] not in bound_digests:
            raise OptimizationError("ACTIVATION_BINDING")
    binding = Path(value["run_binding"])
    if binding.is_relative_to(workspace):
        raise OptimizationError("INSTRUCTION_IN_WORKSPACE")
    run = json_object(private_file(binding))
    if (
        not isinstance(run.get("run_id"), str)
        or not run["run_id"]
        or run.get("stopped") is not False
    ):
        raise OptimizationError("RUN_BINDING")
    limits = value["limits"]
    ceilings = {
        "requests": 10,
        "request_bytes": 24000,
        "output_tokens": 2000,
        "cost_microusd": 100000,
    }
    for name, ceiling in ceilings.items():
        if type(limits[name]) is not int or not 0 < limits[name] <= ceiling:
            raise OptimizationError("QUALIFICATION_LIMIT")
    # Provider peak prices are conservative bounds, not a measured invoice.
    if value["price_bounds"] != {"input_microusd_per_token": 0.3, "output_microusd_per_token": 1.2}:
        raise OptimizationError("PRICE_BOUND")
    tasks = value["tasks"]
    if (
        not isinstance(tasks, list)
        or not tasks
        or len(tasks) > 10
        or len({t["marker"] for t in tasks}) != len(tasks)
    ):
        raise OptimizationError("TASK_BINDING")
    for task in tasks:
        if (
            not isinstance(task["prompt"], str)
            or not task["prompt"]
            or not isinstance(task["marker"], str)
            or not task["marker"]
            or task["marker"] not in task["prompt"]
            or type(task["max_requests"]) is not int
            or not 0 < task["max_requests"] <= 3
        ):
            raise OptimizationError("TASK_BINDING")
    if "tool_projection" in value:
        from score_sw_fabric.optimization.firewall import BOUNDED_TOOLS

        projection = value["tool_projection"]
        selected = projection.get("allowed_tools")
        if (
            set(projection) != {"allowed_tools"}
            or not isinstance(selected, list)
            or any(not isinstance(name, str) for name in selected)
            or len(selected) != len(set(selected))
            or not set(selected) <= BOUNDED_TOOLS
        ):
            raise OptimizationError("TOOL_SELECTION")
    return value


def authorize_stage(
    path: Path,
    pin: str,
    context: dict[str, Any],
    decision: dict[str, Any],
    stage: str,
    host_cwd: Path | None = None,
) -> dict[str, Any]:
    value = verify_instruction(path, pin)
    run = json_object(private_file(Path(value["run_binding"])))
    identity_matches = context.get("run_id") == run["run_id"]
    native = run.get("native_context")
    if native is not None:
        # This pinned Fabro revision emits "petri" as the hook ID. Its exact,
        # run-specific host cwd is the measured identity witness instead.
        cwd = Path(native["cwd"])
        server = Path(native["server_root"])
        relative = cwd.relative_to(server / "storage/scratch")
        identity_matches = (
            native.get("source_commit") == "1b4fb15281ebb724426f9e480dce48d0100ff79b"
            and server == path.parent.parent
            and len(relative.parts) == 5
            and relative.parts[0].endswith("-" + run["run_id"])
            and relative.parts[1:] == ("petri", "scopes", "invocation-0-scope-0", "work")
            and native.get("run_id") == "petri"
            and context.get("run_id") == "petri"
            and (context.get("cwd") == str(cwd) or (context.get("cwd") is None and host_cwd == cwd))
            and (host_cwd is None or host_cwd == cwd)
            and cwd.is_dir()
            and not any(p.is_symlink() for p in (cwd, *cwd.parents))
        )
    if not identity_matches or value["stage"] != stage:
        raise OptimizationError("RUN_BINDING")
    if value["bindings"]["governor"] != decision["digest"]:
        raise OptimizationError("ACTIVATION_BINDING")
    governor_limits(value)
    if context.get("event") == "pre_tool_use" and "tool_projection" in value:
        name = context["tool_name"].removeprefix("mcp__score_bounded__")
        if name not in value["tool_projection"]["allowed_tools"]:
            raise OptimizationError("TOOL_SELECTION")
    return {
        "decision": "allow",
        "scope": "qualification_only",
        "instruction_sha256": pin,
        "task": value["task"],
        "engineering_acceptance": "pending",
    }


def governor_limits(instruction: dict[str, Any]) -> dict[str, int]:
    """Read the exact pinned governor's operational ceilings, not caller overrides."""
    from score_sw_fabric.optimization.common import checked

    expected = instruction["bindings"]["governor"]
    for filename in instruction["files"]:
        raw = private_file(Path(filename))
        if not raw.startswith(b"{"):
            continue
        value = json_object(raw)
        if value.get("digest") == expected:
            checked(value, "token_governor_decision")
            limits = value.get("limits")
            names = ("input_tokens", "output_tokens", "calls", "context_tokens")
            if (
                value.get("decision") != "admissible"
                or value.get("call_authorized") is not False
                or not isinstance(limits, dict)
                or any(type(limits.get(n)) is not int or limits[n] <= 0 for n in names)
            ):
                raise OptimizationError("ACTIVATION_BUDGET")
            return {n: limits[n] for n in names}
    raise OptimizationError("ACTIVATION_BUDGET")
