"""Baseline-bound scope from native impact, not broad repository scans."""

from __future__ import annotations

import hashlib
from typing import Any

from score_sw_fabric.agents.models import relative_path
from score_sw_fabric.optimization.common import OptimizationError, canonical, checked, record


def manifest(
    task: str,
    baseline: str,
    changes: dict[str, Any],
    index: dict[str, Any],
    mapping: dict[str, list[str]],
    *,
    evidence_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    checked(changes, "optimization_impact")
    checked(index)
    if changes["after"] != index["digest"]:
        raise OptimizationError("INDEX_DRIFT")
    if changes["state"] != "complete":
        raise OptimizationError("IMPACT_BLOCKED")
    affected = changes["affected"]
    current_keys = {i["key"] for i in [*index.get("needs", []), *index.get("wrappers", [])]}
    for identifier in affected:
        if identifier in current_keys and (identifier not in mapping or not mapping[identifier]):
            raise OptimizationError("CONTEXT_MAPPING_UNKNOWN")
    for paths in mapping.values():
        if not isinstance(paths, list) or len(paths) > 1000:
            raise OptimizationError("CONTEXT_LIMIT")
        for path in paths:
            relative_path(path, "/context/path")
    primary = sorted({path for key in changes["direct"] for path in mapping.get(key, [])})
    related = sorted({path for key in affected for path in mapping.get(key, [])} - set(primary))
    return record(
        "context_manifest",
        task=task,
        baseline=baseline,
        index_digest=index["digest"],
        impact_digest=changes["digest"],
        mapping_digest=hashlib.sha256(canonical(mapping)).hexdigest(),
        native_ids=affected,
        primary=primary,
        related=related,
        removed_ids=sorted(set(affected) - current_keys),
        evidence_refs=evidence_refs or [],
        excluded_reason="no_reverse_dependency_in_either_baseline",
    )
