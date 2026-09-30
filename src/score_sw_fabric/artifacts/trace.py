"""Typed trace matching and deletion-invariant expected-set coverage."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.artifacts.models import Finding, finding


def evaluate_trace(
    obligations: list[dict[str, Any]], index: dict[str, Any], trace_profile: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], bool]:
    entities = {item["native_id"]: item for item in [*index["wrappers"], *index["needs"]]}
    relations = index["relations"]
    evaluated: list[dict[str, Any]] = []
    findings: list[Finding] = []
    path_rules = {item["id"]: item for item in trace_profile.get("path_rules", [])}
    for source in obligations:
        obligation = dict(source)
        state = "expected"
        required_id = obligation.get("required_native_id")
        classification = obligation.get("classification")
        if classification in {"non_native_record", "external_boundary"}:
            state = "excluded"
        elif obligation.get("kind") == "relation":
            rule = path_rules.get(str(obligation.get("path_rule_id")))
            if rule is None:
                state = "mismatched"
            else:
                allowed = {hop["relation"] for hop in rule.get("hops", [])}
                source_role = obligation.get("source_role")
                state = (
                    "satisfied"
                    if any(
                        item["field"] in allowed
                        and (item["target"] or item["external"])
                        and entities.get(item["source_native_id"], {}).get("type") == source_role
                        for item in relations
                    )
                    else "unresolved"
                )
        elif required_id:
            state = "satisfied" if required_id in entities else "unresolved"
        elif obligation.get("target_role"):
            matches = [
                item for item in entities.values() if item["type"] == obligation["target_role"]
            ]
            state = "satisfied" if matches else "unresolved"
        else:
            state = "unresolved"
        path_rule_id = obligation.get("path_rule_id")
        if state == "satisfied" and path_rule_id and obligation.get("kind") != "relation":
            rule = path_rules.get(path_rule_id)
            if rule is None:
                state = "mismatched"
            else:
                allowed = {hop["relation"] for hop in rule.get("hops", [])}
                if not any(
                    item["field"] in allowed and (item["target"] or item["external"])
                    for item in relations
                ):
                    state = "unresolved"
        obligation["state"] = state
        if state in {"unresolved", "mismatched"} and obligation.get("mandatory", True):
            item = finding(
                "TRACE_UNRESOLVED" if state == "unresolved" else "TRACE_MISMATCH",
                f"Mandatory expected obligation is {state}",
                obligation["id"],
            )
            findings.append(item)
            obligation["findings"] = [item]
        evaluated.append(obligation)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for obligation in evaluated:
        key = (
            str(obligation.get("scope")),
            str(obligation.get("path_rule_id") or obligation.get("kind")),
        )
        grouped.setdefault(key, []).append(obligation)
    coverage: list[dict[str, Any]] = []
    for (scope, metric), items in sorted(grouped.items()):
        denominator = [item["id"] for item in items if item["state"] != "excluded"]
        numerator = [item["id"] for item in items if item["state"] == "satisfied"]
        coverage.append(
            {
                "metric_id": f"{scope}:{metric}",
                "scope": scope,
                "path": metric,
                "denominator": denominator,
                "numerator": numerator,
                "partial": [item["id"] for item in items if item["state"] == "partial"],
                "excluded": [item["id"] for item in items if item["state"] == "excluded"],
                "unresolved": [item["id"] for item in items if item["state"] == "unresolved"],
                "mismatched": [item["id"] for item in items if item["state"] == "mismatched"],
                "counts": {"numerator": len(numerator), "denominator": len(denominator)},
                "source_refs": [item["authority"] for item in items if item.get("authority")],
                "valid": all(
                    item["state"] not in {"unresolved", "mismatched"}
                    or not item.get("mandatory", True)
                    for item in items
                ),
            }
        )
    observed = [
        {
            "source": relation["source"],
            "field": relation["field"],
            "target": relation["target"],
            "raw_selector": relation["raw_selector"],
            "source_location": relation["source_location"],
        }
        for relation in relations
    ]
    return evaluated, coverage, observed, not findings
