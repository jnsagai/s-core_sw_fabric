"""Categorized semantic comparison for indexes, candidates, and reports."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.artifacts.models import unevaluated_capabilities
from score_sw_fabric.compiler.reader import semantic_digest, verify_self_digest

CATEGORIES = (
    "baseline",
    "wrapper",
    "need",
    "option_status_classification",
    "content",
    "relation",
    "containment",
    "obligation",
    "coverage",
    "impact",
    "template_profile",
    "native_validator",
    "file_bytes",
)


def _empty_changes() -> dict[str, list[str]]:
    return {"added": [], "removed": [], "modified": []}


def _entities(value: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    index = value.get("index", value)
    return {item.get("key", item.get("id")): item for item in index.get(key, [])}


def _changed(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[str]]:
    result = _empty_changes()
    for key in sorted(after.keys() - before.keys()):
        result["added"].append(str(key))
    for key in sorted(before.keys() - after.keys()):
        result["removed"].append(str(key))
    for key in sorted(before.keys() & after.keys()):
        if before[key] != after[key]:
            result["modified"].append(str(key))
    return result


def _projection(entity: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: entity.get(field) for field in fields}


def _classify_entities(
    categories: dict[str, Any],
    kind: str,
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> None:
    categories[kind]["added"] = sorted(str(key) for key in after.keys() - before.keys())
    categories[kind]["removed"] = sorted(str(key) for key in before.keys() - after.keys())
    identity_fields = (
        "key",
        "target_namespace",
        "source_id",
        "native_id",
        "native_version",
        "source",
        "origins",
    )
    for key in sorted(before.keys() & after.keys()):
        left = before[key]
        right = after[key]
        if _projection(left, identity_fields) != _projection(right, identity_fields):
            categories[kind]["modified"].append(str(key))
        if _projection(left, ("type", "status", "options")) != _projection(
            right, ("type", "status", "options")
        ):
            categories["option_status_classification"]["modified"].append(str(key))
        if _projection(left, ("title", "content")) != _projection(right, ("title", "content")):
            categories["content"]["modified"].append(str(key))
        if left.get("wrapper_key") != right.get("wrapper_key"):
            categories["containment"]["modified"].append(str(key))


def compare_artifacts(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    verify_self_digest(before, "/before")
    verify_self_digest(after, "/after")
    categories: dict[str, Any] = {name: _empty_changes() for name in CATEGORIES}
    before_index = before.get("index", before)
    after_index = after.get("index", after)
    _classify_entities(
        categories,
        "wrapper",
        _entities(before, "wrappers"),
        _entities(after, "wrappers"),
    )
    _classify_entities(
        categories,
        "need",
        _entities(before, "needs"),
        _entities(after, "needs"),
    )
    categories["relation"] = _changed(
        {
            f"{x['source']}:{x['field']}:{x['raw_selector']}": x
            for x in before_index.get("relations", [])
        },
        {
            f"{x['source']}:{x['field']}:{x['raw_selector']}": x
            for x in after_index.get("relations", [])
        },
    )
    if before_index.get("snapshot") != after_index.get("snapshot"):
        categories["baseline"]["modified"] = ["snapshot"]
    if before_index.get("profile") != after_index.get("profile"):
        categories["template_profile"]["modified"] = ["artifact_profile"]
    before_receipt = before_index.get("native_receipt", {})
    after_receipt = after_index.get("native_receipt", {})
    receipt_fields = ("validator", "commands")
    if {field: before_receipt.get(field) for field in receipt_fields} != {
        field: after_receipt.get(field) for field in receipt_fields
    }:
        categories["native_validator"]["modified"] = ["native_receipt"]
    before_report = before.get("report")
    after_report = after.get("report")
    for category, field in (
        ("obligation", "obligations"),
        ("coverage", "coverage"),
        ("impact", "impact"),
    ):
        left = before_report.get(field) if isinstance(before_report, dict) else None
        right = after_report.get(field) if isinstance(after_report, dict) else None
        if left != right:
            categories[category]["modified"] = [field]
    if before.get("base_files") != after.get("base_files") or before.get(
        "overlay_files"
    ) != after.get("overlay_files"):
        categories["file_bytes"]["modified"] = ["candidate_files"]
    for changes in categories.values():
        for key in changes:
            changes[key] = sorted(set(changes[key]))
    equivalent = not any(
        any(value for value in changes.values()) for changes in categories.values()
    )
    result = {
        "schema_version": 1,
        "kind": "artifact_diff",
        "before": before["digest"],
        "after": after["digest"],
        "categories": categories,
        "equivalent": equivalent,
        "capabilities": unevaluated_capabilities(),
    }
    result["digest"] = semantic_digest(result)
    return result
