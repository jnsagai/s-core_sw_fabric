"""Expected-set-first plan/package obligation derivation."""

from __future__ import annotations

import fnmatch
import hashlib
from typing import Any

from score_sw_fabric.artifacts.models import ArtifactSemanticError, enforce_limit, finding
from score_sw_fabric.catalog.export import canonical


def _rule(value: str, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [item for item in rules if fnmatch.fnmatchcase(value, str(item.get("pattern", "")))]
    if len(matches) != 1:
        return None
    return matches[0]


def _identifier(value: dict[str, Any]) -> str:
    semantic = {key: item for key, item in value.items() if key not in {"id", "state", "findings"}}
    return "OBL-" + hashlib.sha256(canonical(semantic)).hexdigest()[:20].upper()


def derive_obligations(
    plan: dict[str, Any], package: dict[str, Any], trace_profile: dict[str, Any]
) -> list[dict[str, Any]]:
    output_rules = trace_profile.get("output_rules", [])
    artifact_rules = trace_profile.get("artifact_rules", [])
    if not isinstance(output_rules, list) or not isinstance(artifact_rules, list):
        raise ArtifactSemanticError("TRACE_PROFILE", "Trace profile rules must be arrays")
    obligations: list[dict[str, Any]] = []
    for instance in sorted(plan.get("instances", []), key=lambda item: item["instance_id"]):
        applicable = [
            rule
            for rule in artifact_rules
            if rule.get("selector", {}).get("applicability")
            in {None, instance.get("applicability")}
        ]
        if len(applicable) != 1:
            raise ArtifactSemanticError(
                "ARTIFACT_RULE",
                (
                    f"Plan instance {instance['instance_id']} has missing or conflicting "
                    "artifact rules"
                ),
            )
        rule = applicable[0]
        obligation = {
            "kind": "artifact",
            "plan_instance": instance["instance_id"],
            "scope": instance.get("scope", "fixture"),
            "purpose": instance.get("purpose", "planned work product"),
            "disposition": instance.get("effective_disposition"),
            "artifact_rule_id": rule["id"],
            "output_rule_id": None,
            "source_role": None,
            "target_role": rule.get("need_type"),
            "required_native_id": instance.get("native_id"),
            "path_rule_id": None,
            "package_action": None,
            "package_value": None,
            "classification": "native_artifact",
            "mandatory": True,
            "authority": rule.get("origin"),
            "state": "expected",
            "findings": [],
        }
        obligation["id"] = _identifier(obligation)
        obligations.append(obligation)
        path_rules = {item["id"]: item for item in trace_profile.get("path_rules", [])}
        for path_rule_id in sorted(rule.get("required_paths", [])):
            path_rule = path_rules.get(path_rule_id)
            if path_rule is None:
                raise ArtifactSemanticError(
                    "TRACE_PATH_RULE",
                    f"Artifact rule selects missing path rule {path_rule_id}",
                )
            path_obligation = {
                "kind": "relation",
                "plan_instance": instance["instance_id"],
                "scope": instance.get("scope", "fixture"),
                "purpose": path_rule_id,
                "disposition": instance.get("effective_disposition"),
                "artifact_rule_id": rule["id"],
                "output_rule_id": None,
                "source_role": rule.get("need_type"),
                "target_role": None,
                "required_native_id": None,
                "path_rule_id": path_rule_id,
                "package_action": None,
                "package_value": None,
                "classification": "native_artifact",
                "mandatory": True,
                "authority": path_rule.get("origin"),
                "state": "expected",
                "findings": [],
            }
            path_obligation["id"] = _identifier(path_obligation)
            obligations.append(path_obligation)
    graph = package.get("manifest", {}).get("ir", {})
    for node in sorted(graph.get("nodes", []), key=lambda item: str(item.get("id"))):
        instance_ids = node.get("instance_ids", [])
        for field in ("expected_outputs", "data_destinations"):
            for value in sorted(node.get(field, [])):
                rule = _rule(value, output_rules)
                if rule is None:
                    raise ArtifactSemanticError(
                        "OUTPUT_UNCLASSIFIED",
                        f"Package {field[:-1]} {value!r} has no unique reviewed classification",
                        findings=[
                            finding(
                                "OUTPUT_UNCLASSIFIED",
                                "Package output/destination is unclassified",
                                str(node.get("id")),
                                value,
                            )
                        ],
                    )
                for instance_id in sorted(instance_ids or [None]):
                    obligation = {
                        "kind": "artifact"
                        if rule["classification"] == "native_artifact"
                        else rule["classification"],
                        "plan_instance": instance_id,
                        "scope": "package",
                        "purpose": field,
                        "disposition": "create",
                        "artifact_rule_id": None,
                        "output_rule_id": rule["id"],
                        "source_role": None,
                        "target_role": rule.get("native_role"),
                        "required_native_id": rule.get("native_id"),
                        "path_rule_id": None,
                        "package_action": node.get("id"),
                        "package_value": value,
                        "classification": rule["classification"],
                        "mandatory": rule["classification"] == "native_artifact",
                        "authority": rule.get("origin"),
                        "state": "expected",
                        "findings": [],
                    }
                    obligation["id"] = _identifier(obligation)
                    obligations.append(obligation)
    unique: dict[str, dict[str, Any]] = {}
    for obligation in obligations:
        if obligation["id"] in unique and unique[obligation["id"]] != obligation:
            raise ArtifactSemanticError(
                "OBLIGATION_COLLISION", "Expected-obligation identity collision"
            )
        unique[obligation["id"]] = obligation
    enforce_limit(
        trace_profile["limits"],
        "obligations",
        len(unique),
        "OBLIGATION_LIMIT",
        "Expected obligation limit exceeded",
        semantic=True,
    )
    return [unique[key] for key in sorted(unique)]
