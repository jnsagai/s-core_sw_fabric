"""Evaluate finite, source-cited applicability mappings."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.catalog.reader import CatalogueIndex
from score_sw_fabric.planning.models import (
    CoverageEntry,
    CoverageState,
    Finding,
    PlanningInputs,
    WorkProductInstance,
)
from score_sw_fabric.process_source.reader import InputError

ALLOWED_SELECTORS = {
    "self",
    "owning_module",
    "owning_platform",
    "affected_components",
    "affected_features",
}
BLOCKED_PROFILE_FACTS = (
    "language",
    "environment",
    "safety_classification",
    "security_relevance",
)


def finding(
    code: str,
    location: str,
    message: str,
    action: str,
    *,
    instance_id: str | None = None,
    native_ref: dict[str, Any] | None = None,
) -> Finding:
    return {
        "code": code,
        "location": location,
        "message": message,
        "required_action": action,
        "instance_id": instance_id,
        "native_ref": native_ref,
    }


def scope_key(scope: dict[str, Any]) -> str:
    return f"{scope['kind']}:{scope['id']}"


def instance_identity(
    target_namespace: str,
    native: dict[str, Any],
    scope: dict[str, Any],
    purpose: str,
) -> tuple[dict[str, str], str]:
    identity = {
        "target_namespace": target_namespace,
        "native_source_id": native["source_id"],
        "native_work_product_id": native["native_id"],
        "scope_kind": scope["kind"],
        "scope_id": scope["id"],
        "purpose": purpose,
    }
    return identity, hashlib.sha256(canonical(identity)).hexdigest()


def _scopes(inputs: PlanningInputs) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    scopes = sorted(inputs.intake["scopes"], key=lambda item: (item["kind"], item["id"]))
    return scopes, {scope_key(scope): scope for scope in scopes}


def _selected_scopes(
    selector: str,
    origin: dict[str, Any],
    scopes: list[dict[str, Any]],
    by_key: dict[str, dict[str, Any]],
    affected: set[str],
) -> list[dict[str, Any]]:
    if selector not in ALLOWED_SELECTORS:
        raise InputError("MAPPING_SELECTOR", f"Unsupported scope selector {selector}")
    if selector == "self":
        return [origin]
    if selector.startswith("affected_"):
        wanted = "component" if selector == "affected_components" else "feature"
        return [
            scope for scope in scopes if scope["kind"] == wanted and scope_key(scope) in affected
        ]
    wanted = "module" if selector == "owning_module" else "platform"
    current = origin
    seen: set[str] = set()
    while current["kind"] != wanted:
        key = scope_key(current)
        if key in seen or current["parent"] is None:
            return []
        seen.add(key)
        parent = current["parent"]
        parent_key = f"{parent['kind']}:{parent['id']}"
        if parent_key not in by_key:
            return []
        current = by_key[parent_key]
    return [current]


def _condition(condition: Any, scope: dict[str, Any]) -> bool | None:
    if not isinstance(condition, dict) or set(condition) != {"field", "op", "value"}:
        raise InputError("MAPPING_CONDITION", "Conditions require field/op/value")
    field, operation, expected = condition["field"], condition["op"], condition["value"]
    if not isinstance(field, str) or operation not in ("eq", "in"):
        raise InputError("MAPPING_CONDITION", "Only typed eq/in predicates are supported")
    if field in ("scope_kind", "scope_id"):
        actual = scope["kind" if field == "scope_kind" else "id"]
    elif field in {
        "development_origin",
        "language",
        "environment",
        "safety_classification",
        "security_relevance",
        "reuse_route",
        "has_subcomponents",
        "relevant_interactions",
    }:
        actual = scope["facts"].get(field)
    else:
        raise InputError("MAPPING_CONDITION", f"Unsupported fact {field}")
    if actual is None or actual == "unknown" or actual == "unresolved":
        return None
    if operation == "eq":
        return bool(actual == expected)
    if not isinstance(expected, list):
        raise InputError("MAPPING_CONDITION", "in predicate value must be an array")
    return bool(actual in expected)


def _evaluate(conditions: Any, scope: dict[str, Any]) -> bool | None:
    if not isinstance(conditions, list):
        raise InputError("MAPPING_CONDITION", "Rule conditions must be an array")
    outcomes = [_condition(condition, scope) for condition in conditions]
    if False in outcomes:
        return False
    if None in outcomes:
        return None
    return True


def _native_ref(entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": entity["source_id"],
        "native_id": entity["native_id"],
        "native_version": entity["native_version"],
    }


def _validate_profile(
    index: CatalogueIndex, inputs: PlanningInputs, scopes: list[dict[str, Any]]
) -> tuple[dict[tuple[str, str], int], list[Finding]]:
    profile = inputs.profile
    required = {
        "schema_version",
        "id",
        "version",
        "status",
        "catalogue_digest",
        "expected_workproduct_count",
        "supported",
        "active_revisions",
        "limits",
        "source_refs",
    }
    if set(profile) != required:
        raise InputError(
            "PROFILE_FIELDS", f"Profile fields differ: {sorted(set(profile) ^ required)}"
        )
    if profile["catalogue_digest"] != index.digest:
        raise InputError("CATALOGUE_BASELINE", "Profile/catalogue digest mismatch")
    if profile["expected_workproduct_count"] != len(index.workproducts):
        raise InputError("PROFILE_COVERAGE", "Profile work-product count does not match catalogue")
    supported = profile["supported"]
    if not isinstance(supported, dict):
        raise InputError("PROFILE_FIELDS", "supported must be a mapping")
    findings: list[Finding] = []
    for scope in scopes:
        for field in BLOCKED_PROFILE_FACTS:
            actual = scope["facts"].get(field)
            allowed = supported.get(field, [])
            if actual in (None, "unknown", "unresolved"):
                findings.append(
                    finding(
                        "CLASSIFICATION_UNKNOWN" if field != "language" else "PROFILE_UNSUPPORTED",
                        f"scope:{scope_key(scope)}:{field}",
                        f"{field} is unresolved for {scope_key(scope)}",
                        "Provide an authorized, profile-supported scope fact.",
                    )
                )
            elif not isinstance(allowed, list) or actual not in allowed:
                findings.append(
                    finding(
                        "PROFILE_UNSUPPORTED",
                        f"scope:{scope_key(scope)}:{field}",
                        f"{field}={actual!r} is outside profile support",
                        "Select a reviewed supported profile or extend it explicitly.",
                    )
                )
    active: dict[tuple[str, str], int] = {}
    revisions = profile["active_revisions"]
    if not isinstance(revisions, list):
        raise InputError("PROFILE_REVISION", "active_revisions must be an array")
    for position, raw in enumerate(revisions):
        if not isinstance(raw, dict) or set(raw) != {"source_id", "native_id", "native_version"}:
            raise InputError("PROFILE_REVISION", f"Invalid active revision at {position}")
        revision = raw["native_version"]
        if type(revision) is not int:
            raise InputError("PROFILE_REVISION", f"Revision must be integer at {position}")
        key = raw["source_id"], raw["native_id"]
        if key in active or (*key, revision) not in index.entities:
            raise InputError("PROFILE_REVISION", f"Invalid/duplicate active revision {raw}")
        active[key] = revision
    grouped: dict[tuple[str, str], set[int]] = defaultdict(set)
    for entity in index.workproducts:
        grouped[(entity["source_id"], entity["native_id"])].add(entity["native_version"])
    for key, available in grouped.items():
        if len(available) > 1 and key not in active:
            findings.append(
                finding(
                    "PROFILE_REVISION_AMBIGUOUS",
                    f"native:{key[0]}:{key[1]}",
                    f"Multiple revisions available: {sorted(available)}",
                    "Select one exact native revision in the reviewed profile.",
                    native_ref={"source_id": key[0], "native_id": key[1]},
                )
            )
        elif key not in active:
            active[key] = next(iter(available))
    return active, findings


def build_coverage(
    index: CatalogueIndex, inputs: PlanningInputs
) -> tuple[
    list[CoverageEntry], dict[str, WorkProductInstance], list[Finding], dict[str, dict[str, Any]]
]:
    """Build complete native-work-product/scope coverage and initial instances."""

    scopes, by_key = _scopes(inputs)
    active, findings = _validate_profile(index, inputs, scopes)
    mapping = inputs.mapping
    if set(mapping) != {"schema_version", "coverage_basis", "rules", "source_conflicts"}:
        raise InputError("MAPPING_FIELDS", "Applicability mapping fields differ")
    rules = mapping["rules"]
    if not isinstance(rules, list) or len(rules) > 10000:
        raise InputError("MAPPING_RULES", "Mapping requires at most 10,000 rules")
    rules_by_native: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    rules_by_id: dict[str, dict[str, Any]] = {}
    for position, raw in enumerate(rules):
        if not isinstance(raw, dict):
            raise InputError("MAPPING_RULE", f"Rule {position} is not a mapping")
        required = {
            "id",
            "native",
            "scope_kinds",
            "scope_selector",
            "when",
            "purposes",
            "dependencies",
            "rationale",
            "source_refs",
            "template_refs",
            "required_reviews",
        }
        if set(raw) != required or not isinstance(raw["id"], str) or raw["id"] in rules_by_id:
            raise InputError("MAPPING_RULE", f"Invalid/duplicate rule at {position}")
        native = raw["native"]
        if not isinstance(native, dict) or set(native) != {
            "source_id",
            "native_id",
            "native_version",
        }:
            raise InputError("MAPPING_RULE", f"Invalid native ref in {raw['id']}")
        key = native["source_id"], native["native_id"], native["native_version"]
        if key not in index.entities or index.entities[key]["type"] != "workproduct":
            raise InputError("MAPPING_REFERENCE", f"Dangling work-product ref in {raw['id']}")
        if raw["scope_selector"] not in ALLOWED_SELECTORS:
            raise InputError("MAPPING_SELECTOR", f"Invalid selector in {raw['id']}")
        if not isinstance(raw["scope_kinds"], list) or any(
            kind not in ("feature", "component", "module", "platform")
            for kind in raw["scope_kinds"]
        ):
            raise InputError("MAPPING_RULE", f"Invalid scope kinds in {raw['id']}")
        if (
            not isinstance(raw["purposes"], list)
            or not raw["purposes"]
            or any(not isinstance(purpose, str) or not purpose for purpose in raw["purposes"])
        ):
            raise InputError("MAPPING_RULE", f"Rule {raw['id']} needs purposes")
        rules_by_native[key].append(raw)
        rules_by_id[raw["id"]] = raw
    if len(index.workproducts) * len(scopes) > 100000:
        raise InputError("COVERAGE_LIMIT", "Coverage matrix exceeds 100,000 rows")

    affected = {f"{item['kind']}:{item['id']}" for item in inputs.intake["affected_scopes"]}
    coverage: list[CoverageEntry] = []
    instances: dict[str, WorkProductInstance] = {}
    for entity in index.workproducts:
        native = _native_ref(entity)
        key2 = entity["source_id"], entity["native_id"]
        selected_revision = active.get(key2)
        for scope in scopes:
            codes: list[str] = []
            if selected_revision != entity["native_version"]:
                coverage.append(
                    {
                        "native_ref": native,
                        "scope": {"kind": scope["kind"], "id": scope["id"]},
                        "state": "outside_scope",
                        "rule_ids": [],
                        "rationale": (
                            f"REVISION_NOT_SELECTED: active revision is {selected_revision}"
                        ),
                        "instance_ids": [],
                        "finding_codes": [],
                    }
                )
                continue
            native_rules = rules_by_native.get(
                (entity["source_id"], entity["native_id"], entity["native_version"]), []
            )
            if not native_rules:
                code = "MAPPING_COVERAGE_GAP"
                findings.append(
                    finding(
                        code,
                        f"coverage:{entity['source_id']}:{entity['native_id']}:{scope_key(scope)}",
                        "No source-backed mapping rule covers this native work product",
                        "Add a reviewed mapping rule or explicit source-backed scope exclusion.",
                        native_ref=native,
                    )
                )
                coverage.append(
                    {
                        "native_ref": native,
                        "scope": {"kind": scope["kind"], "id": scope["id"]},
                        "state": "unresolved",
                        "rule_ids": [],
                        "rationale": "No explicit mapping rule",
                        "instance_ids": [],
                        "finding_codes": [code],
                    }
                )
                continue
            applicable = [rule for rule in native_rules if scope["kind"] in rule["scope_kinds"]]
            if not applicable:
                coverage.append(
                    {
                        "native_ref": native,
                        "scope": {"kind": scope["kind"], "id": scope["id"]},
                        "state": "outside_scope",
                        "rule_ids": [rule["id"] for rule in native_rules],
                        "rationale": "Source-backed rules do not apply to this scope kind",
                        "instance_ids": [],
                        "finding_codes": [],
                    }
                )
                continue
            outcomes = [(rule, _evaluate(rule["when"], scope)) for rule in applicable]
            selected = [rule for rule, outcome in outcomes if outcome is True]
            unknown = [rule for rule, outcome in outcomes if outcome is None]
            instance_ids: list[str] = []
            for rule in [*selected, *unknown]:
                targets = _selected_scopes(rule["scope_selector"], scope, scopes, by_key, affected)
                if not targets:
                    code = "SCOPE_CONTEXT_MISSING"
                    codes.append(code)
                    findings.append(
                        finding(
                            code,
                            f"rule:{rule['id']}:scope:{scope_key(scope)}",
                            "Rule target scope is unavailable",
                            "Declare the required parent/member scope or external owner.",
                            native_ref=native,
                        )
                    )
                for target in targets:
                    for purpose in sorted(set(rule["purposes"])):
                        identity, identifier = instance_identity(
                            inputs.intake["target_namespace"], native, target, purpose
                        )
                        instance_ids.append(identifier)
                        candidate: WorkProductInstance = {
                            "instance_id": identifier,
                            "identity": identity,
                            "binding": {
                                **native,
                                "catalogue_digest": index.digest,
                                "source_ref": entity["source_ref"],
                            },
                            "purpose": purpose,
                            "requesting_scopes": [scope_key(scope)],
                            "origin_rule_ids": [rule["id"]],
                            "applicability": ("unresolved" if rule in unknown else "required"),
                            "requested_disposition": "unresolved",
                            "effective_disposition": "unresolved",
                            "rationale": rule["rationale"],
                            "artifact_bindings": [],
                            "decision_refs": [],
                            "required_reviews": rule["required_reviews"],
                            "template_refs": rule["template_refs"],
                            "dependency_ids": [],
                            "finding_codes": (
                                ["CLASSIFICATION_UNKNOWN"] if rule in unknown else []
                            ),
                        }
                        previous = instances.get(identifier)
                        if previous is None:
                            instances[identifier] = candidate
                        elif previous["binding"] != candidate["binding"]:
                            findings.append(
                                finding(
                                    "MAPPING_CONFLICT",
                                    f"instance:{identifier}",
                                    "Rules bind one logical instance incompatibly",
                                    "Resolve the source-backed mapping conflict.",
                                    instance_id=identifier,
                                    native_ref=native,
                                )
                            )
                        else:
                            previous["requesting_scopes"] = sorted(
                                set(previous["requesting_scopes"] + candidate["requesting_scopes"])
                            )
                            previous["origin_rule_ids"] = sorted(
                                set(previous["origin_rule_ids"] + candidate["origin_rule_ids"])
                            )
                            if candidate["applicability"] == "required":
                                previous["applicability"] = "required"
            if unknown:
                code = "CLASSIFICATION_UNKNOWN"
                codes.append(code)
                findings.append(
                    finding(
                        code,
                        f"coverage:{entity['source_id']}:{entity['native_id']}:{scope_key(scope)}",
                        "A mapping predicate depends on an unresolved fact",
                        "Provide the source/decision-backed fact; retain the potential obligation.",
                        native_ref=native,
                    )
                )
            state: CoverageState = (
                "selected"
                if selected and not unknown
                else "unresolved"
                if unknown
                else "outside_scope"
            )
            coverage.append(
                {
                    "native_ref": native,
                    "scope": {"kind": scope["kind"], "id": scope["id"]},
                    "state": state,
                    "rule_ids": sorted(rule["id"] for rule in applicable),
                    "rationale": "Matched source-backed mapping"
                    if selected
                    else "Mapping predicate excluded or unresolved",
                    "instance_ids": sorted(set(instance_ids)),
                    "finding_codes": sorted(set(codes)),
                }
            )

    conflicts = mapping["source_conflicts"]
    if not isinstance(conflicts, list):
        raise InputError("MAPPING_CONFLICT", "source_conflicts must be an array")
    for position, conflict in enumerate(conflicts):
        if not isinstance(conflict, dict) or set(conflict) != {
            "id",
            "native_refs",
            "message",
            "required_action",
        }:
            raise InputError("MAPPING_CONFLICT", f"Invalid source conflict at {position}")
        findings.append(
            finding(
                "NATIVE_SOURCE_CONFLICT",
                f"source_conflict:{conflict['id']}",
                conflict["message"],
                conflict["required_action"],
            )
        )
    return (
        sorted(coverage, key=lambda item: canonical(item)),
        instances,
        sorted(findings, key=lambda item: canonical(item)),
        rules_by_id,
    )
