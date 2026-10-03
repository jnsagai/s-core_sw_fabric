"""Explicit conditional route requests; model/catalogue admission remains in 007."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, integer, record


def route(
    task_class: str,
    *,
    gates_passed: bool,
    corrections: int = 0,
    request_stronger: bool = False,
    ambiguity: bool = False,
    safety: bool = False,
    reviewer_required: bool = False,
    owner_supervision: bool = False,
) -> dict[str, Any]:
    integer(corrections, maximum=1)
    if task_class not in {"S0", "S1", "S2", "S3", "S4"}:
        raise OptimizationError("CLASSIFICATION_UNKNOWN")
    triggered = ambiguity or safety or (not gates_passed and corrections >= 1)
    if request_stronger and not triggered:
        raise OptimizationError("ESCALATION_TRIGGER")
    if task_class == "S4" and not owner_supervision:
        raise OptimizationError("S4_AUTHORIZATION_REQUIRED")
    critic = task_class in {"S2", "S3", "S4"} or triggered or reviewer_required
    return record(
        "model_route",
        task_class=task_class,
        tier="supervisor"
        if owner_supervision
        else ("stronger" if request_stronger or task_class == "S3" else "routine"),
        critic={
            "required": critic,
            "reason": "SENSITIVE_OR_UNRESOLVED"
            if critic
            else ("LOCAL_GATES_PASSED" if gates_passed else "AWAITING_DETERMINISTIC_CORRECTION"),
        },
        escalation_trigger=triggered,
        authority="route_request_requires_007_admission",
    )
