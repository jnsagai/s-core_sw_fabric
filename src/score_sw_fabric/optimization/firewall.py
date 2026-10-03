"""Fail-closed optimized-stage tools; no arbitrary shell or generic evidence reads."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.optimization.common import OptimizationError

BOUNDED_TOOLS = frozenset(
    {
        "evidence_summary",
        "finding_list",
        "finding_get",
        "sarif_find_rule",
        "sarif_find_file",
        "sarif_find_location",
        "sarif_count_by_rule",
        "sarif_count_by_path",
        "get_source_excerpt",
        "get_observation",
    }
)


def admit_tool(name: str, arguments: dict[str, Any]) -> None:
    if name not in BOUNDED_TOOLS or not isinstance(arguments, dict):
        raise OptimizationError("BOUNDED_TOOL_REQUIRED")
