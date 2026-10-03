"""Nullable observed provider usage; estimates stay in a separate accounting channel."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, checked, integer, record

DIMENSIONS = {"call", "task", "role", "model", "workflow", "increment"}
METRICS = (
    "input_tokens",
    "cached_input_tokens",
    "uncached_input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "model_calls",
    "tool_calls",
    "cost_microusd",
    "wall_milliseconds",
    "correction_visits",
    "escalations",
    "critic_calls",
)


def usage(
    dimensions: dict[str, str],
    metrics: dict[str, int | None],
    *,
    origin: str = "runtime_observation",
) -> dict[str, Any]:
    if set(dimensions) != DIMENSIONS or any(
        not isinstance(i, str) or not i or len(i) > 128 for i in dimensions.values()
    ):
        raise OptimizationError("USAGE_DIMENSIONS")
    if set(metrics) - set(METRICS) or origin not in {"runtime_observation", "unknown"}:
        raise OptimizationError("USAGE_FIELDS")
    values = {name: metrics.get(name) for name in METRICS}
    for value in values.values():
        if value is not None:
            integer(value)
            if origin == "unknown":
                raise OptimizationError("USAGE_ORIGIN")
    total, cached, uncached = (
        values[key] for key in ("input_tokens", "cached_input_tokens", "uncached_input_tokens")
    )
    if total is not None and (
        any(i is not None and i > total for i in (cached, uncached))
        or (cached is not None and uncached is not None and cached + uncached != total)
    ):
        raise OptimizationError("CACHE_SPLIT")
    return record("optimization_usage", dimensions=dimensions, metrics=values, origin=origin)


def aggregate(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if len(entries) > 10000:
        raise OptimizationError("LEDGER_LIMIT")
    identifiers = set()
    for entry in entries:
        checked(entry, "optimization_usage")
        usage(entry["dimensions"], entry["metrics"], origin=entry["origin"])
        identifier = (
            entry["dimensions"]["workflow"],
            entry["dimensions"]["task"],
            entry["dimensions"]["call"],
        )
        if identifier in identifiers:
            raise OptimizationError("DUPLICATE_CALL")
        identifiers.add(identifier)
    metrics = {}
    for name in METRICS:
        values = [entry["metrics"][name] for entry in entries]
        metrics[name] = (
            None if any(i is None for i in values) else sum(i for i in values if i is not None)
        )
    return record(
        "optimization_usage_aggregate",
        calls=len(entries),
        metrics=metrics,
        entry_digests=[i["digest"] for i in entries],
    )
