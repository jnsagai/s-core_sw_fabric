"""Projection of reviewed execution mappings into explicit action records."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.commands import command_binding
from score_sw_fabric.compiler.models import CompilerSemanticError
from score_sw_fabric.process_source.reader import InputError

ACTION_FIELDS = {
    "ref",
    "purpose",
    "type",
    "label",
    "instance_ids",
    "role",
    "allowed_inputs",
    "allowed_paths",
    "expected_outputs",
    "data_destinations",
    "write_scope",
    "tool_profile",
    "model_capability",
    "budget",
    "completion_predicate",
    "evidence_expectation",
    "fallible_outcomes",
    "prohibited_authority",
    "support_files",
    "origin",
}
BUDGET_FIELDS = {
    "wall_time_seconds",
    "attempts",
    "tool_calls",
    "input_tokens",
    "output_tokens",
    "cost_microunits",
}
MODEL_ACTIONS = {"agent", "prompt"}


def _strings(value: Any, pointer: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise InputError("MAPPING_FIELD", f"Expected string array at {pointer}", pointer)
    if nonempty and not value:
        raise InputError("MAPPING_FIELD", f"Expected nonempty array at {pointer}", pointer)
    if len(set(value)) != len(value):
        raise InputError("MAPPING_DUPLICATE", f"Duplicate value at {pointer}", pointer)
    return sorted(value)


def _origin(value: Any, pointer: str) -> dict[str, Any]:
    fields = {"kind", "source_ref", "pointer", "decision_ref", "rationale"}
    if not isinstance(value, dict) or set(value) != fields:
        raise InputError("MAPPING_ORIGIN", f"Invalid origin at {pointer}", pointer)
    if value["kind"] not in {
        "upstream_process",
        "reviewed_project_configuration",
        "authorized_human_decision",
    }:
        raise InputError("MAPPING_ORIGIN", f"Invalid origin kind at {pointer}", pointer)
    if not isinstance(value["source_ref"], dict) or not isinstance(value["pointer"], str):
        raise InputError("MAPPING_ORIGIN", f"Invalid origin reference at {pointer}", pointer)
    if value["decision_ref"] is not None and not isinstance(value["decision_ref"], str):
        raise InputError("MAPPING_ORIGIN", f"Invalid decision reference at {pointer}", pointer)
    if not isinstance(value["rationale"], str) or not value["rationale"]:
        raise InputError("MAPPING_ORIGIN", f"Missing rationale at {pointer}", pointer)
    return value


def _budget(value: Any, ceilings: dict[str, Any], pointer: str, *, model: bool) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != BUDGET_FIELDS:
        raise InputError("ACTION_BUDGET", f"Invalid budget fields at {pointer}", pointer)
    result: dict[str, int] = {}
    for name in sorted(BUDGET_FIELDS):
        item = value[name]
        if type(item) is not int or item < 0 or item > ceilings[name]:
            raise CompilerSemanticError("ACTION_BUDGET", f"Invalid {name} at {pointer}/{name}")
        if name in {"wall_time_seconds", "attempts"} and item == 0:
            raise CompilerSemanticError("ACTION_BUDGET", f"{name} must be positive")
        if model and name in {"input_tokens", "output_tokens", "cost_microunits"} and item == 0:
            raise CompilerSemanticError("ACTION_BUDGET", f"Model budget {name} must be positive")
        if not model and name in {"input_tokens", "output_tokens", "cost_microunits"} and item != 0:
            raise CompilerSemanticError("ACTION_BUDGET", f"Non-model budget {name} must be zero")
        result[name] = item
    return result


def project_mapping(
    plan: dict[str, Any], mapping: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    """Return normalized actions and controls from an already reviewed mapping."""

    plan_ids = {item["instance_id"] for item in plan["instances"]}
    allowed_actions = set(profile.get("allowed_actions", []))
    capabilities = {item["id"]: item for item in profile.get("model_capabilities", [])}
    ceilings = profile.get("limits", {}).get("action_budget", {})
    if set(ceilings) != BUDGET_FIELDS:
        raise InputError("COMPILER_PROFILE", "Compiler action-budget ceilings are incomplete")

    actions: list[dict[str, Any]] = []
    refs: dict[str, bytes] = {}
    coverage: dict[str, int] = {item: 0 for item in plan_ids}
    rule_ids: set[str] = set()
    for rule_index, rule in enumerate(mapping["rules"]):
        pointer = f"/rules/{rule_index}"
        if not isinstance(rule, dict) or set(rule) != {"id", "instance_ids", "actions"}:
            raise InputError("MAPPING_RULE", f"Invalid rule fields at {pointer}", pointer)
        rule_id = rule["id"]
        if not isinstance(rule_id, str) or not rule_id or rule_id in rule_ids:
            raise InputError("MAPPING_RULE", f"Invalid or duplicate rule id at {pointer}", pointer)
        rule_ids.add(rule_id)
        selected = _strings(rule["instance_ids"], pointer + "/instance_ids", nonempty=True)
        if "*" in selected:
            selected = sorted(plan_ids)
        if not set(selected) <= plan_ids:
            raise CompilerSemanticError(
                "MAPPING_SELECTOR", f"Rule {rule_id} selects unknown instances"
            )
        raw_actions = rule["actions"]
        if not isinstance(raw_actions, list) or not raw_actions:
            raise CompilerSemanticError("MAPPING_GAP", f"Rule {rule_id} has no actions")
        rule_covered: set[str] = set()
        for action_index, raw in enumerate(raw_actions):
            action_pointer = f"{pointer}/actions/{action_index}"
            if not isinstance(raw, dict) or set(raw) - {"command_file"} != ACTION_FIELDS:
                raise InputError("MAPPING_ACTION", f"Invalid action fields at {action_pointer}")
            action_type = raw["type"]
            if action_type not in allowed_actions:
                raise CompilerSemanticError(
                    "UNSUPPORTED_ACTION", f"Unsupported action type {action_type}"
                )
            instances = _strings(
                raw["instance_ids"], action_pointer + "/instance_ids", nonempty=True
            )
            if not set(instances) <= set(selected):
                raise CompilerSemanticError("MAPPING_SELECTOR", f"Action escapes rule {rule_id}")
            rule_covered.update(instances)
            capability = raw["model_capability"]
            if capability not in capabilities:
                raise CompilerSemanticError("MODEL_CAPABILITY", f"Unknown capability {capability}")
            model = action_type in MODEL_ACTIONS
            if capabilities[capability].get("model_allowed") is not model:
                raise CompilerSemanticError(
                    "MODEL_CAPABILITY", f"Capability {capability} conflicts with {action_type}"
                )
            action = dict(raw)
            for field in (
                "allowed_inputs",
                "allowed_paths",
                "expected_outputs",
                "data_destinations",
                "write_scope",
                "fallible_outcomes",
                "prohibited_authority",
                "support_files",
            ):
                action[field] = _strings(raw[field], f"{action_pointer}/{field}")
            for field in (
                "ref",
                "purpose",
                "label",
                "role",
                "tool_profile",
                "completion_predicate",
                "evidence_expectation",
            ):
                if not isinstance(raw[field], str) or not raw[field]:
                    raise InputError(
                        "MAPPING_ACTION", f"Expected nonempty {field} at {action_pointer}"
                    )
            for required_boundary in ("allowed_inputs", "allowed_paths", "data_destinations"):
                if not action[required_boundary]:
                    raise CompilerSemanticError(
                        "ACTION_BOUNDARY", f"Action {raw['ref']} needs {required_boundary}"
                    )
            if not action["fallible_outcomes"] or "success" not in action["fallible_outcomes"]:
                raise CompilerSemanticError(
                    "OUTCOME_GAP", f"Action {raw['ref']} must declare success"
                )
            action["instance_ids"] = instances
            action["budget"] = _budget(
                raw["budget"], ceilings, action_pointer + "/budget", model=model
            )
            action["origin"] = _origin(raw["origin"], action_pointer + "/origin")
            command_binding(action, action_type)
            action["rule_id"] = rule_id
            ref = raw["ref"]
            signature = canonical(
                {key: action[key] for key in action if key not in {"origin", "rule_id"}}
            )
            if ref in refs and refs[ref] != signature:
                raise CompilerSemanticError("MAPPING_CONFLICT", f"Conflicting action ref {ref}")
            if ref not in refs:
                refs[ref] = signature
                actions.append(action)
        if rule_covered != set(selected):
            missing = sorted(set(selected) - rule_covered)
            raise CompilerSemanticError("MAPPING_GAP", f"Rule {rule_id} omits {missing}")
        for instance in selected:
            coverage[instance] += 1
    gaps = sorted(item for item, count in coverage.items() if count == 0)
    overlaps = sorted(item for item, count in coverage.items() if count > 1)
    if gaps:
        raise CompilerSemanticError("MAPPING_GAP", f"Unmapped plan instances: {gaps}")
    if overlaps:
        raise CompilerSemanticError(
            "MAPPING_CONFLICT", f"Instances selected by multiple rules: {overlaps}"
        )

    return {
        "actions": sorted(actions, key=lambda item: (item["rule_id"], item["ref"])),
        "edges": mapping["edges"],
        "loop_policies": mapping["loop_policies"],
        "fan_groups": mapping["fan_groups"],
        "support_files": mapping["support_files"],
    }
