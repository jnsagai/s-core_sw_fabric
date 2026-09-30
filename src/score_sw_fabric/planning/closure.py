"""Assemble deterministic coverage, dependency closure, and draft plan results."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.catalog.reader import load_catalogue
from score_sw_fabric.planning.dispositions import apply_dispositions
from score_sw_fabric.planning.mapping import build_coverage, finding
from score_sw_fabric.planning.models import Finding, PlanningInputs, WorkProductInstance
from score_sw_fabric.process_source.reader import InputError


def _scope_key(kind: str, identifier: str) -> str:
    return f"{kind}:{identifier}"


def _dependency_scope(
    origin: WorkProductInstance,
    selector: str,
    scopes: dict[str, dict[str, Any]],
) -> str | None:
    start = _scope_key(origin["identity"]["scope_kind"], origin["identity"]["scope_id"])
    if selector == "self":
        return start
    wanted = (
        "module"
        if selector == "owning_module"
        else "platform"
        if selector == "owning_platform"
        else None
    )
    if wanted is None:
        raise InputError("MAPPING_SELECTOR", f"Unsupported dependency selector {selector}")
    current = scopes[start]
    seen: set[str] = set()
    while current["kind"] != wanted:
        key = _scope_key(current["kind"], current["id"])
        if key in seen or current["parent"] is None:
            return None
        seen.add(key)
        parent = current["parent"]
        parent_key = _scope_key(parent["kind"], parent["id"])
        if parent_key not in scopes:
            return None
        current = scopes[parent_key]
    return _scope_key(current["kind"], current["id"])


def _close_dependencies(
    instances: dict[str, WorkProductInstance],
    rules: dict[str, dict[str, Any]],
    inputs: PlanningInputs,
) -> list[Finding]:
    scopes = {_scope_key(scope["kind"], scope["id"]): scope for scope in inputs.intake["scopes"]}
    by_rule_scope_purpose: dict[tuple[str, str, str], list[str]] = {}
    for identifier, instance in sorted(instances.items()):
        scope = _scope_key(instance["identity"]["scope_kind"], instance["identity"]["scope_id"])
        for rule_id in instance["origin_rule_ids"]:
            by_rule_scope_purpose.setdefault((rule_id, scope, instance["purpose"]), []).append(
                identifier
            )
    findings: list[Finding] = []
    edge_count = 0
    for identifier, instance in sorted(instances.items()):
        dependencies: set[str] = set()
        for rule_id in instance["origin_rule_ids"]:
            rule = rules[rule_id]
            raw_dependencies = rule["dependencies"]
            if not isinstance(raw_dependencies, list):
                raise InputError(
                    "MAPPING_DEPENDENCY", f"Dependencies in {rule_id} must be an array"
                )
            for position, dependency in enumerate(raw_dependencies):
                if not isinstance(dependency, dict) or set(dependency) != {
                    "target_rule",
                    "purpose",
                    "scope_selector",
                }:
                    raise InputError(
                        "MAPPING_DEPENDENCY", f"Invalid dependency {rule_id}/{position}"
                    )
                target_rule = dependency["target_rule"]
                if target_rule not in rules:
                    raise InputError("MAPPING_REFERENCE", f"Dangling dependency rule {target_rule}")
                target_scope = _dependency_scope(instance, dependency["scope_selector"], scopes)
                if target_scope is None:
                    code = "SCOPE_CONTEXT_MISSING"
                    instance["finding_codes"].append(code)
                    findings.append(
                        finding(
                            code,
                            f"instance:{identifier}:dependency:{target_rule}",
                            "Dependency target scope is unavailable",
                            "Declare the required scope or external owner.",
                            instance_id=identifier,
                        )
                    )
                    continue
                targets = by_rule_scope_purpose.get(
                    (target_rule, target_scope, dependency["purpose"]), []
                )
                if not targets:
                    code = "MAPPING_CONFLICT"
                    instance["finding_codes"].append(code)
                    findings.append(
                        finding(
                            code,
                            f"instance:{identifier}:dependency:{target_rule}",
                            "Mapped dependency did not produce a target instance",
                            "Align dependency conditions, purpose, and scope selection.",
                            instance_id=identifier,
                        )
                    )
                dependencies.update(targets)
        edge_count += len(dependencies)
        if edge_count > 100000:
            findings.append(
                finding(
                    "CLOSURE_LIMIT",
                    "closure:dependency_edges",
                    "Dependency closure exceeds 100,000 edges",
                    "Reduce or partition the declared scope and mapping.",
                )
            )
            break
        instance["dependency_ids"] = sorted(dependencies)
    return sorted(findings, key=canonical)


def build_plan(inputs: PlanningInputs) -> dict[str, Any]:
    """Build a complete or explicitly blocked draft planning payload."""

    catalogue = load_catalogue(
        inputs.catalogue_path,
        transport_sha256=inputs.catalogue_transport_sha256,
        expected_digest=inputs.catalogue_digest,
    )
    coverage, instances, findings, rules = build_coverage(catalogue, inputs)
    if len(instances) > 10000:
        findings.append(
            finding(
                "CLOSURE_LIMIT",
                "closure:instances",
                "Instance closure exceeds 10,000 entries",
                "Reduce or partition the declared scope and mapping.",
            )
        )
        instances = dict(sorted(instances.items())[:10000])
    findings.extend(_close_dependencies(instances, rules, inputs))
    findings.extend(apply_dispositions(instances, inputs))
    findings = sorted({canonical(item): item for item in findings}.values(), key=canonical)
    semantic_inputs = {
        "catalogue_digest": catalogue.digest,
        **{
            f"{name}_semantic_digest": value
            for name, value in sorted(inputs.semantic_digests.items())
        },
    }
    scope_rows = [
        {
            "kind": scope["kind"],
            "id": scope["id"],
            "parent": scope["parent"],
            "facts": scope["facts"],
        }
        for scope in inputs.intake["scopes"]
    ]
    return {
        "schema_version": 1,
        "plan_kind": "draft",
        "planning_status": "blocked" if findings else "complete",
        "closure_complete": not any(item["code"] == "CLOSURE_LIMIT" for item in findings),
        "engineering_readiness": "not_evaluated",
        "target_namespace": inputs.intake["target_namespace"],
        "change": inputs.intake["change"],
        "semantic_inputs": semantic_inputs,
        "scopes": sorted(scope_rows, key=canonical),
        "coverage": coverage,
        "instances": [instances[key] for key in sorted(instances)],
        "findings": findings,
    }
