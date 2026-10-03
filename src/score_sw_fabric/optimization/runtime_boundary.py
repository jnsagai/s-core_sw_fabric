"""Explicit bounded-service candidate and command-hook admission; live grant stays external."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, checked
from score_sw_fabric.optimization.firewall import admit_tool


def guard(
    context: dict[str, Any],
    decision: dict[str, Any],
    *,
    stage: str,
    instruction: Path | None = None,
    instruction_sha256: str | None = None,
    host_cwd: Path | None = None,
) -> dict[str, Any]:
    checked(decision, "token_governor_decision")
    if context.get("node_id") != stage or decision["decision"] != "admissible":
        raise OptimizationError("STAGE_ADMISSION_REFUSED")
    if decision.get("call_authorized") is not False:
        raise OptimizationError("UNTRUSTED_EXECUTION_GRANT")
    if context.get("event") == "pre_tool_use":
        name = context.get("tool_name", "")
        prefix = "mcp__score_bounded__"
        if not isinstance(name, str) or not name.startswith(prefix):
            raise OptimizationError("BOUNDED_TOOL_REQUIRED")
        args = context.get("tool_input")
        if not isinstance(args, dict):
            raise OptimizationError("HOOK_INPUT")
        admit_tool(name.removeprefix(prefix), args)
    elif context.get("event") != "stage_start":
        raise OptimizationError("HOOK_EVENT")
    if instruction is not None and instruction_sha256 is not None:
        from score_sw_fabric.optimization.activation import authorize_stage

        return authorize_stage(instruction, instruction_sha256, context, decision, stage, host_cwd)
    # A sealed optimization record is not an execution instruction.
    raise OptimizationError("LIVE_CALL_NOT_AUTHORIZED")


def runtime_config(
    python: Path,
    root: Path,
    state: Path,
    governor: Path,
    stage: str,
    *,
    instruction: Path | None = None,
    instruction_sha256: str | None = None,
) -> str:
    """Source-checked native stdio and blocking command hooks; unactivated candidate only."""
    lines = [
        "[run.agent]",
        "fabro_tools = false",
        "",
        "[run.agent.mcps.score_bounded]",
        'type = "stdio"',
        "command = "
        + json.dumps(
            [
                str(python),
                "-m",
                "score_sw_fabric.optimization.cli",
                "serve",
                "--root",
                str(root),
                "--state",
                str(state),
                "--stage",
                stage,
            ]
        ),
        "",
    ]
    for event in ("stage_start", "pre_tool_use"):
        lines += [
            "[[run.hooks]]",
            f'id = "optimization-{event}"',
            f'event = "{event}"',
            *(['matcher = "^agent$"'] if event == "stage_start" else []),
            "blocking = true",
            "sandbox = false",
            'timeout = "5s"',
            "command = "
            + json.dumps(
                [
                    str(python),
                    "-m",
                    "score_sw_fabric.optimization.cli",
                    "guard",
                    "--decision",
                    str(governor),
                    "--stage",
                    stage,
                    *(
                        [
                            "--instruction",
                            str(instruction),
                            "--instruction-sha256",
                            str(instruction_sha256),
                        ]
                        if instruction is not None
                        else []
                    ),
                ]
            ),
            "",
        ]
    return "\n".join(lines)
