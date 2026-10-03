"""Derived native transitive impact and explicit baseline-vector freshness."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.artifacts.impact import analyze_impact
from score_sw_fabric.optimization.common import OptimizationError, checked, record


def impact(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    checked(before)
    checked(after)
    native = analyze_impact(before, after, {"impact_rules": []})
    affected = sorted({i["subject"] for i in native["dependency_paths"]})
    if native["blockers"]:
        affected = sorted(
            {
                item["key"]
                for tree in (before, after)
                for item in [*tree.get("needs", []), *tree.get("wrappers", [])]
            }
        )
    return record(
        "optimization_impact",
        before=before["digest"],
        after=after["digest"],
        direct=sorted(
            set(
                native["changed"]
                + native["added"]
                + native["removed"]
                + native.get("relation_changed_subjects", [])
            )
        ),
        affected=affected,
        relation_changes=native.get("relation_changes", []),
        unknown_dependencies=native["unknown_dependencies"],
        blockers=native["blockers"],
        state=native["state"],
        native=native,
    )


def freshness(
    current: dict[str, str], evidence: list[dict[str, Any]], decisions: list[dict[str, Any]]
) -> dict[str, Any]:
    if not current or any(
        not isinstance(k, str) or not isinstance(v, str) or not v for k, v in current.items()
    ):
        raise OptimizationError("BASELINE_VECTOR")

    def stale(records: list[dict[str, Any]]) -> list[str]:
        if len(records) > 10000 or len({i["id"] for i in records}) != len(records):
            raise OptimizationError("RECORD_LIMIT")
        # Exact vector equality: missing/new baseline dimensions cannot be silently reused.
        return sorted(i["id"] for i in records if i.get("baseline") != current)

    return record(
        "optimization_freshness",
        current=current,
        stale_evidence=stale(evidence),
        stale_decisions=stale(decisions),
        authority="derived_only_005_gate_required",
    )
