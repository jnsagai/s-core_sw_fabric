"""Bounded role profiles, refusal of privileged grants and derived runtime agent config."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.lock import server_by_id
from score_sw_fabric.agents.models import (
    PROTECTED_WORKSPACE_GLOBS,
    glob_list,
    glob_match,
    matches_any,
    string_list,
)
from score_sw_fabric.assurance.models import bounded_limits, exact, nonempty, stable_id, version
from score_sw_fabric.process_source.reader import InputError

ROLE_FIELDS = {
    "id",
    "status",
    "role",
    "purpose",
    "allowed_inputs",
    "expected_output",
    "write_scope",
    "builtin_tools",
    "mcp_servers",
    "data_destinations",
    "prohibited_decisions",
    "completion_criteria",
    "uncertainties_to_report",
    "loopback",
    "retry_limit",
    "model_profile",
    "budget",
    "credentials",
    "runtime",
}
ROLES = frozenset(
    {
        "process_coordinator",
        "requirements_engineer",
        "software_architect",
        "fmea_analyst",
        "dfa_analyst",
        "security_analyst",
        "developer",
        "verification_engineer",
        "compliance_analyst",
        "independent_critic",
        "delivery_reviewer",
    }
)
READ_TOOLS = frozenset({"read_file", "read_many_files", "grep", "glob", "list_dir"})
WRITE_TOOLS = frozenset({"write_file", "edit_file", "apply_patch"})
FORBIDDEN_TOOLS = {
    "shell": "TOOL_FORBIDDEN",
    "shell_command": "TOOL_FORBIDDEN",
    "web_search": "TOOL_FORBIDDEN",
    "web_fetch": "TOOL_FORBIDDEN",
    "spawn_agent": "TOOL_FORBIDDEN",
    "send_input": "TOOL_FORBIDDEN",
    "wait": "TOOL_FORBIDDEN",
    "close_agent": "TOOL_FORBIDDEN",
}
CREDENTIAL_CLASSES = (
    ("approv", "approval"),
    ("collector", "collector"),
    ("answer", "human_answer"),
    ("resume", "run_resume"),
    ("token", "runtime_token"),
)
BUDGET_CEILINGS = {
    "cost_microusd": 10_000_000_000,
    "input_tokens": 100_000_000,
    "output_tokens": 100_000_000,
    "wall_seconds": 7 * 24 * 3600,
    "calls": 10_000,
}
OBSERVATION_WRITES = {"add_overlay_node": "score-context/**"}


def _refuse(code: str, message: str, pointer: str) -> InputError:
    return InputError(code, message, pointer, "Remove the grant; roles never hold it.")


def validate_role(value: Any, lock: dict[str, Any]) -> dict[str, Any]:
    """Validate one role profile and refuse every privileged or unbounded grant."""
    role = version(value, "agent_role_profile", ROLE_FIELDS, "/agent_role_profile")
    stable_id(role["id"], "/id")
    nonempty(role["status"], "/status", max_length=64)
    if role["role"] not in ROLES:
        raise InputError("FIELD_ENUM", "Unknown role", "/role")
    nonempty(role["purpose"], "/purpose", max_length=2048)
    inputs = glob_list(role["allowed_inputs"], "/allowed_inputs")
    expected = exact(role["expected_output"], {"kind", "schema_version"}, "/expected_output")
    if expected != {"kind": "agent_result", "schema_version": 1}:
        raise InputError(
            "OUTPUT_UNSUPPORTED", "Expected agent_result version 1", "/expected_output"
        )
    scope = glob_list(role["write_scope"], "/write_scope")
    for index, pattern in enumerate([*scope, *inputs]):
        if pattern.split("/")[0] in {".git", "**", "*"} or matches_any(
            PROTECTED_WORKSPACE_GLOBS, pattern
        ):
            pointer = "/write_scope" if index < len(scope) else "/allowed_inputs"
            raise _refuse("PROTECTED_PATH", "Globs may not cover .git or the whole tree", pointer)
    credentials = role["credentials"]
    if not isinstance(credentials, list):
        raise InputError("FIELD_TYPE", "Credentials must be a list", "/credentials")
    for index, item in enumerate(credentials):
        name = str(item).lower()
        label = next((label for key, label in CREDENTIAL_CLASSES if key in name), "credential")
        raise _refuse(
            "CREDENTIAL_FORBIDDEN", f"Role requests a {label} credential", f"/credentials/{index}"
        )
    runtime = exact(role["runtime"], {"fabro_tools", "human_gate", "permissions"}, "/runtime")
    if runtime["fabro_tools"] is not False:
        raise _refuse(
            "RUN_TOOLS_FORBIDDEN", "Run-management tools are forbidden", "/runtime/fabro_tools"
        )
    if runtime["human_gate"] != "stop":
        raise _refuse(
            "HUMAN_GATE", "Required human gates must stop the role", "/runtime/human_gate"
        )
    if runtime["permissions"] not in {"read-only", "read-write"}:
        raise _refuse(
            "TOOL_FORBIDDEN", "Only read-only or read-write permissions", "/runtime/permissions"
        )
    builtin = string_list(role["builtin_tools"], "/builtin_tools", limit=32, length=64)
    if len(set(builtin)) != len(builtin):
        raise InputError("DUPLICATE_ID", "Duplicate builtin tool", "/builtin_tools")
    for index, tool in enumerate(builtin):
        pointer = f"/builtin_tools/{index}"
        if tool.startswith("fabro_"):
            raise _refuse("RUN_TOOLS_FORBIDDEN", "Run-management tools are forbidden", pointer)
        if tool in FORBIDDEN_TOOLS:
            raise _refuse(FORBIDDEN_TOOLS[tool], f"{tool} is not a bounded role tool", pointer)
        if tool not in READ_TOOLS | WRITE_TOOLS:
            raise _refuse("TOOL_FORBIDDEN", "Unknown builtin tool", pointer)
    writes = [tool for tool in builtin if tool in WRITE_TOOLS]
    if writes and runtime["permissions"] != "read-write":
        raise _refuse("TOOL_FORBIDDEN", "Write tools need read-write permissions", "/runtime")
    if writes and not scope:
        raise _refuse("WRITE_SCOPE_MISSING", "Write tools need a write scope", "/write_scope")
    servers = string_list(role["mcp_servers"], "/mcp_servers", limit=16, length=128)
    if len(set(servers)) != len(servers):
        raise InputError("DUPLICATE_ID", "Duplicate server", "/mcp_servers")
    for index, server_id in enumerate(servers):
        pointer = f"/mcp_servers/{index}"
        if server_id.lower().startswith("fabro"):
            raise _refuse(
                "RUN_TOOLS_FORBIDDEN", "Fabro run-management servers are forbidden", pointer
            )
        server = server_by_id(lock, server_id, pointer)
        if server["status"] != "supported":
            raise InputError("SERVER_UNSUPPORTED", "Role server is unsupported", pointer)
        for tool in server["tools"]:
            if tool["classification"] == "setup_privileged":
                raise _refuse(
                    "SETUP_FORBIDDEN", f"{server_id} exposes setup tool {tool['name']}", pointer
                )
        for write in server_writes(server):
            if not any(covers(pattern, write) for pattern in scope):
                raise _refuse("SERVER_WRITES_OUT_OF_SCOPE", f"{server_id} writes {write}", pointer)
    destinations = string_list(
        role["data_destinations"], "/data_destinations", limit=16, length=128
    )
    for index, item in enumerate(destinations):
        stable_id(item, f"/data_destinations/{index}")
    for name in ("prohibited_decisions", "completion_criteria", "uncertainties_to_report"):
        string_list(role[name], f"/{name}", limit=64, length=512)
    if not role["prohibited_decisions"]:
        raise InputError(
            "FIELD_TYPE", "Prohibited decisions must be explicit", "/prohibited_decisions"
        )
    loopback = exact(role["loopback"], {"max_correction_visits"}, "/loopback")
    for name, item, ceiling in (
        ("/loopback/max_correction_visits", loopback["max_correction_visits"], 20),
        ("/retry_limit", role["retry_limit"], 10),
    ):
        if type(item) is not int or not 0 <= item <= ceiling:
            raise InputError("LIMIT_EXCEEDED", "Invalid finite limit", name)
    stable_id(role["model_profile"], "/model_profile")
    bounded_limits(role["budget"], BUDGET_CEILINGS, "/budget")
    return role


def server_writes(server: dict[str, Any]) -> list[str]:
    """Workspace globs a granted server may write, including its write tools."""
    writes = list(server["startup_writes"])
    for tool in server["tools"]:
        extra = OBSERVATION_WRITES.get(tool["name"])
        if tool["classification"] == "local_observation_write" and extra and extra not in writes:
            writes.append(extra)
    return writes


def covers(pattern: str, target: str) -> bool:
    """Whether `pattern` covers every path matched by the literal-prefix glob `target`."""
    if pattern == target:
        return True
    prefix = target[: -len("/**")] if target.endswith("/**") else target
    return pattern.endswith("/**") and glob_match(pattern, prefix)


def granted_tools(role: dict[str, Any], lock: dict[str, Any]) -> list[dict[str, str]]:
    tools = []
    for server_id in role["mcp_servers"]:
        server = server_by_id(lock, server_id, "/mcp_servers")
        for tool in server["tools"]:
            tools.append(
                {
                    "server": server_id,
                    "tool": tool["name"],
                    "qualified_name": f"mcp__{server_id.replace('-', '_')}__{tool['name']}",
                    "classification": tool["classification"],
                    "schema_sha256": tool["schema_sha256"],
                }
            )
    return tools


def runtime_agent_config(role: dict[str, Any], lock: dict[str, Any], copy_root: Path) -> str:
    """Candidate Fabro run TOML granting only the role's pinned context servers."""
    limits = lock["limits"]
    lines = [
        "# Candidate only: derived by score-fabric 007; not executed by a Fabro agent stage.",
        "[run.agent]",
        "fabro_tools = false",
    ]
    for server_id in role["mcp_servers"]:
        server = server_by_id(lock, server_id, "/mcp_servers")
        python_path = ":".join(str(copy_root / item) for item in server["launch"]["python_path"])
        command = [sys.executable, "-s", "-B", "-m", server["launch"]["module"]]
        lines.extend(
            [
                "",
                f"[run.agent.mcps.{server_id}]",
                'type = "stdio"',
                f"command = {json.dumps(command)}",
                f'startup_timeout = "{limits["handshake_seconds"]}s"',
                f'tool_timeout = "{limits["tool_seconds"]}s"',
                "",
                f"[run.agent.mcps.{server_id}.env]",
                f"PYTHONPATH = {json.dumps(python_path)}",
                'PYTHONDONTWRITEBYTECODE = "1"',
            ]
        )
    return "\n".join(lines) + "\n"


def role_prompt(
    role: dict[str, Any],
    task: dict[str, str],
    sources: list[dict[str, Any]],
    tools: list[dict[str, str]],
    assumptions: list[str],
    baseline: str,
) -> str:
    """Deterministic role instructions; the prompt is context, never policy or approval."""

    def section(title: str, items: list[str]) -> list[str]:
        return [f"## {title}", *(f"- {item}" for item in items or ["none"]), ""]

    lines = [
        f"# Role: {role['role']} ({role['id']})",
        "",
        role["purpose"],
        "",
        f"Task {task['id']}: {task['statement']}",
        f"Repository baseline: {baseline}",
        "",
        *section(
            "Native sources",
            [f"{item['id']} {item['path']} sha256={item['sha256']}" for item in sources],
        ),
        *section("Readable paths", role["allowed_inputs"]),
        *section("Writable paths (all others are read-only)", role["write_scope"]),
        *section("Builtin tools", role["builtin_tools"]),
        *section(
            "Context tools",
            [f"{item['qualified_name']} ({item['classification']})" for item in tools],
        ),
        *section("Prohibited decisions", role["prohibited_decisions"]),
        *section("Completion criteria", role["completion_criteria"]),
        *section("Report these uncertainties", role["uncertainties_to_report"]),
        *section("Unresolved assumptions", assumptions),
        "## Output",
        "Return one JSON object of kind agent_result version 1 with changed_paths,",
        "native_ids_affected, evidence_refs, unresolved_assumptions, proposed_next_action and",
        "self_reported_checks. Self-reported checks are assertions, not verification evidence.",
        "Local working-memory observations are hints, not evidence or decisions. Stop at every",
        "required human gate; you cannot approve, answer, resume or collect evidence.",
    ]
    return "\n".join(lines) + "\n"
