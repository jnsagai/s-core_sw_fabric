"""Derived Fabro stage selection retaining every supplied mandatory check and human gate."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, record

MODES = {
    "full": ["impact", "plan", "tasks", "implement", "verify", "package"],
    "delta": ["impact", "plan_delta", "tasks_delta", "implement", "verify", "package"],
    "correction": ["impact", "implement", "verify", "package"],
    "verification-only": ["impact", "verify", "package"],
    "evidence-refresh": ["impact", "collect", "freshness", "package"],
}


def mode_plan(mode: str, mandatory_checks: list[str], human_gates: list[str]) -> dict[str, Any]:
    if mode not in MODES or not mandatory_checks or not isinstance(human_gates, list):
        raise OptimizationError("MODE_REQUIREMENTS")
    if any(
        not isinstance(i, str) or not i or len(i) > 128 for i in [*mandatory_checks, *human_gates]
    ):
        raise OptimizationError("MODE_REQUIREMENTS")
    return record(
        "optimization_mode_plan",
        mode=mode,
        stages=MODES[mode],
        mandatory_checks=sorted(set(mandatory_checks)),
        human_gates=sorted(set(human_gates)),
        agent_required=mode in {"full", "delta", "correction"},
        runtime_owner="Fabro",
        execution_authorized=False,
    )
