"""Validated semantic comparison of workflow packages."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.package import validate_package

CATEGORIES = (
    "obligation",
    "node_action",
    "edge_control_flow",
    "gate",
    "permission",
    "loop_bound",
    "fan_group",
    "generated_file",
    "compiler_baseline",
    "validator_baseline",
)


def _indexed(values: list[dict[str, Any]], key: str = "id") -> dict[str, dict[str, Any]]:
    return {str(item.get(key)): item for item in values}


def _changes(category: str, before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for subject in sorted(before.keys() | after.keys()):
        left = before.get(subject)
        right = after.get(subject)
        if canonical(left) == canonical(right):
            continue
        kind = "added" if left is None else "removed" if right is None else "modified"
        result.append(
            {"category": category, "kind": kind, "subject": subject, "before": left, "after": right}
        )
    return result


def _node_projection(graph: dict[str, Any], fields: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    return {node["id"]: {field: node[field] for field in fields} for node in graph["nodes"]}


def compare_packages(
    before: dict[str, Any], after: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    validate_package(before, profile)
    validate_package(after, profile)
    left_graph = before["manifest"]["ir"]
    right_graph = after["manifest"]["ir"]
    changes: list[dict[str, Any]] = []
    changes += _changes(
        "obligation",
        _node_projection(left_graph, ("instance_ids",)),
        _node_projection(right_graph, ("instance_ids",)),
    )
    action_fields = (
        "key",
        "ref",
        "action_type",
        "native_type",
        "purpose",
        "label",
        "role",
        "completion_predicate",
        "evidence_expectation",
        "fallible_outcomes",
        "support_files",
        "origins",
    )
    changes += _changes(
        "node_action",
        _node_projection(left_graph, action_fields),
        _node_projection(right_graph, action_fields),
    )
    permission_fields = (
        "allowed_inputs",
        "allowed_paths",
        "expected_outputs",
        "data_destinations",
        "write_scope",
        "tool_profile",
        "model_capability",
        "budget",
        "prohibited_authority",
        "origins",
    )
    changes += _changes(
        "permission",
        _node_projection(left_graph, permission_fields),
        _node_projection(right_graph, permission_fields),
    )
    changes += _changes(
        "edge_control_flow", _indexed(left_graph["edges"]), _indexed(right_graph["edges"])
    )
    changes += _changes(
        "gate", _indexed(left_graph["gates"], "node_id"), _indexed(right_graph["gates"], "node_id")
    )
    changes += _changes(
        "loop_bound", _indexed(left_graph["loop_policies"]), _indexed(right_graph["loop_policies"])
    )
    changes += _changes(
        "fan_group", _indexed(left_graph["fan_groups"]), _indexed(right_graph["fan_groups"])
    )
    changes += _changes("generated_file", before["files"], after["files"])
    changes += _changes(
        "compiler_baseline",
        {"compiler": before["manifest"]["compiler"]},
        {"compiler": after["manifest"]["compiler"]},
    )
    changes += _changes(
        "validator_baseline",
        {"validator": before["manifest"]["validator"]},
        {"validator": after["manifest"]["validator"]},
    )
    order = {name: index for index, name in enumerate(CATEGORIES)}
    changes.sort(key=lambda item: (order[item["category"]], item["subject"], item["kind"]))
    return {
        "schema_version": 1,
        "before_identity": before["manifest"]["package_identity"],
        "after_identity": after["manifest"]["package_identity"],
        "changes": changes,
        "summary": {name: sum(item["category"] == name for item in changes) for name in CATEGORIES},
        "equivalent": not changes,
    }
