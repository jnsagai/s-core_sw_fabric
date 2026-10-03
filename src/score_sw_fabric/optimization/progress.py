"""Measured progress and hard stops; no scheduler and no engineering decisions."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.optimization.common import integer, record


def progress(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    mode: str = "correction",
    visits: int = 0,
    max_visits: int = 1,
    repeated_query: bool = False,
    repeated_failure: bool = False,
    budget_exhausted: bool = False,
    usage_unknown: bool = False,
    human_gate: bool = False,
) -> dict[str, Any]:
    integer(visits)
    integer(max_visits)
    reduced = any(
        type(before.get(key)) is int and type(after.get(key)) is int and after[key] < before[key]
        for key in ("failures", "diagnostics", "unresolved")
    )
    changed = bool(
        before.get("source") and after.get("source") and before["source"] != after["source"]
    )
    new_trace = after.get("trace_count", 0) > before.get("trace_count", 0)
    evidence_changed = bool(
        before.get("evidence") and after.get("evidence") and before["evidence"] != after["evidence"]
    )
    made = changed or reduced or new_trace or (mode == "evidence-refresh" and evidence_changed)
    reason = next(
        (
            code
            for condition, code in (
                (human_gate, "HUMAN_GATE"),
                (usage_unknown, "USAGE_UNKNOWN"),
                (budget_exhausted, "BUDGET_EXHAUSTED"),
                (repeated_query, "REPEATED_QUERY"),
                (repeated_failure, "REPEATED_FAILURE"),
                (visits > max_visits, "CORRECTION_LIMIT"),
                (visits > 0 and not made, "NO_PROGRESS_AFTER_CORRECTION"),
            )
            if condition
        ),
        None,
    )
    return record(
        "optimization_progress",
        made_progress=made,
        stop_reason=reason,
        continue_allowed=reason is None,
        mode=mode,
        before=before,
        after=after,
    )
