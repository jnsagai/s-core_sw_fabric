"""Derived bounded review context with evidence references; no approval authority."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, canonical, checked, record


def review_pack(
    context: dict[str, Any],
    changed_paths: list[str],
    diff_ref: dict[str, Any],
    verification: list[dict[str, Any]],
    unresolved: list[str],
) -> dict[str, Any]:
    checked(context, "optimized_context_bundle")
    scope = set(context["l1"]) | set(context["l2"])
    if set(changed_paths) - scope:
        raise OptimizationError("REVIEW_OUT_OF_SCOPE")
    for item in verification:
        checked(item)
    result = record(
        "review_pack",
        context_digest=context["digest"],
        intent=context["l0"],
        changed_paths=sorted(set(changed_paths)),
        diff_ref=diff_ref,
        verification=[
            {"kind": i["kind"], "digest": i["digest"], "status": i.get("status", "unknown")}
            for i in verification
        ],
        unresolved=unresolved,
        human_review="pending",
    )
    if len(canonical(result)) > 12000:
        raise OptimizationError("REVIEW_CONTEXT_LIMIT")
    return result
