"""Stable autonomous-stage contract; engineering rationale remains in schema-required fields."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.agents.output import validate_result
from score_sw_fabric.optimization.common import OptimizationError, canonical, checked

SILENT_EXECUTION = (
    "Execution style: Do not narrate your reasoning or plan. Use bounded tools directly. "
    "Return only the requested artifact or structured stage result. Do not repeat evidence. "
    "Never read raw SARIF/minified machine JSON or full logs through generic tools. "
    "Use bounded evidence queries and digest references. Engineering rationale is permitted "
    "only where the output schema requires it. Stop at human gates and budget/no-progress limits."
)


def render_prompt(
    static_role: str,
    constraints: list[str],
    tools: str,
    component: str,
    task: dict[str, Any],
    current: dict[str, Any],
) -> str:
    return "\n\n".join(
        (
            SILENT_EXECUTION,
            static_role,
            "\n".join(constraints),
            tools,
            component,
            canonical(task).decode(),
            canonical(current).decode(),
        )
    )


def stage_result(value: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    checked(context)
    result = validate_result(value)
    if result["context_digest"] != context["digest"]:
        raise OptimizationError("CONTEXT_DRIFT")
    if len(canonical(value)) > 12000:
        raise OptimizationError("STAGE_OUTPUT_LIMIT")
    return result
