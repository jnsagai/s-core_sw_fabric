"""Freeze source-cited expected predicates before consulting observations."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.assurance.models import (
    MAX_DECISIONS,
    MAX_EVIDENCE,
    MAX_FINDINGS,
    MAX_PREDICATES,
    bounded_limits,
    bounded_list,
    domain,
    exact,
    nonempty,
    scope,
    unique_strings,
    verify_digest,
    version,
)
from score_sw_fabric.process_source.reader import InputError

POLICY_FIELDS = {
    "id",
    "assurance_domain",
    "authority_source",
    "applicable_scopes",
    "subject_requirements",
    "expected_set_rule",
    "predicates",
    "required_roles",
    "independence_rules",
    "allowed_evidence",
    "freshness_rules",
    "not_applicable_rules",
    "outcome_routes",
    "limits",
    "status",
    "digest",
}
PREDICATE_COMMON = {
    "predicate_id",
    "gate_id",
    "subject_ref",
    "obligation_id",
    "scope",
    "predicate_class",
    "required",
    "source_ref",
    "policy_rule_ref",
    "acceptable_result",
    "applicability",
    "authority_ref",
}
PREDICATE_EXTRAS = {
    "trusted_evidence": {"evidence_id"},
    "human_decision": {"role"},
    "deterministic_check": {"check"},
}


def expected_predicates(
    subject: dict[str, Any],
    policy: Any,
    *,
    gate_id: str,
    requested_domain: str,
    requested_scope: dict[str, str],
) -> list[dict[str, Any]]:
    record = version(policy, "assurance_gate_policy", POLICY_FIELDS, "/policy")
    verify_digest(record, "/policy")
    verify_digest(subject, "/subject")
    if subject.get("kind") != "assurance_subject" or subject.get("schema_version") != 1:
        raise InputError("KIND_MISMATCH", "Expected sealed assurance subject")
    selected_domain = domain(requested_domain, "/assurance_domain")
    scope(requested_scope, "/scope")
    if record["assurance_domain"] != subject["assurance_domain"]:
        raise InputError("DOMAIN_MISMATCH", "Subject and policy domains differ")
    if record["assurance_domain"] != selected_domain and not (
        record["assurance_domain"] == "fixture_contract" and selected_domain == "production"
    ):
        raise InputError("DOMAIN_MISMATCH", "Subject, policy and request domains differ")
    if requested_scope != subject["scope"] or requested_scope not in record["applicable_scopes"]:
        raise InputError("SCOPE_MISMATCH", "Policy does not cover exact subject scope")
    if selected_domain == "fixture_contract" and record["status"] != "fixture_only":
        raise InputError("DOMAIN_MISMATCH", "Fixture policy must remain fixture_only")
    if record["status"] not in {"fixture_only", "pending_production_review", "reviewed"}:
        raise InputError("FIELD_UNKNOWN", "Unknown gate policy status")
    authority = exact(
        record["authority_source"], {"kind", "source_ref"}, "/policy/authority_source"
    )
    nonempty(authority["kind"], "/policy/authority_source/kind", max_length=256)
    nonempty(authority["source_ref"], "/policy/authority_source/source_ref", max_length=256)
    if record["assurance_domain"] == "fixture_contract" and authority["kind"] != "fixture_contract":
        raise InputError("TAILORING_UNVERIFIED", "Fixture policy lacks fixture authority")
    exact(
        record["expected_set_rule"],
        {"plan_instances", "artifact_obligations"},
        "/policy/expected_set_rule",
    )
    if record["expected_set_rule"] != {"plan_instances": "all", "artifact_obligations": "all"}:
        raise InputError(
            "OBLIGATION_SET_INCOMPLETE", "Expected-set rule must include all bound obligations"
        )
    freshness = record["freshness_rules"]
    freshness_fields = {"max_age_seconds"}
    if isinstance(freshness, dict) and "no_impact" in freshness:
        freshness_fields.add("no_impact")
    freshness = exact(freshness, freshness_fields, "/policy/freshness_rules")
    age = freshness["max_age_seconds"]
    if type(age) is not int or age < 0 or age > 2**31 - 1:
        raise InputError("LIMIT_EXCEEDED", "Invalid policy freshness age")
    if "no_impact" in freshness:
        review = exact(
            freshness["no_impact"],
            {"role", "authority_ref", "allowed_paths"},
            "/policy/freshness_rules/no_impact",
        )
        nonempty(review["role"], "/policy/freshness_rules/no_impact/role", max_length=256)
        nonempty(
            review["authority_ref"],
            "/policy/freshness_rules/no_impact/authority_ref",
            max_length=256,
        )
        paths = bounded_list(
            review["allowed_paths"], MAX_FINDINGS, "/policy/freshness_rules/no_impact/allowed_paths"
        )
        if (
            not paths
            or any(
                not isinstance(path, str)
                or len(path) > 4096
                or not (path.startswith(("/subject/", "/policy/")) or path == "/as_of")
                for path in paths
            )
            or paths != sorted(set(paths))
        ):
            raise InputError("FIELD_TYPE", "Invalid no-impact policy paths")
    obligations = unique_strings(
        subject["expected_obligation_ids"], MAX_PREDICATES, "/subject/expected_obligation_ids"
    )
    if not obligations:
        raise InputError("OBLIGATION_SET_INCOMPLETE", "Subject has no obligations")
    limits = bounded_limits(
        record["limits"],
        {
            "predicates": MAX_PREDICATES,
            "evidence": MAX_EVIDENCE,
            "decisions": MAX_DECISIONS,
        },
        "/policy/limits",
    )
    raw = bounded_list(
        record["predicates"], min(MAX_PREDICATES, limits["predicates"]), "/policy/predicates"
    )
    if not raw:
        raise InputError("OBLIGATION_SET_INCOMPLETE", "Gate policy has no predicates")
    selected: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, value in enumerate(raw):
        pointer = f"/policy/predicates/{index}"
        if not isinstance(value, dict) or value.get("predicate_class") not in PREDICATE_EXTRAS:
            raise InputError("FIELD_UNKNOWN", f"Unknown predicate class at {pointer}")
        kind = value["predicate_class"]
        item = exact(value, PREDICATE_COMMON | PREDICATE_EXTRAS[kind], pointer)
        identifier = nonempty(item["predicate_id"], pointer + "/predicate_id", max_length=256)
        if identifier in ids:
            raise InputError("DUPLICATE_ID", f"Duplicate predicate {identifier}")
        ids.add(identifier)
        if item["gate_id"] != gate_id or item["subject_ref"] != subject["digest"]:
            raise InputError("SUBJECT_MISMATCH", "Predicate references another gate or subject")
        if item["scope"] != requested_scope or item["obligation_id"] not in obligations:
            raise InputError(
                "OBLIGATION_SET_INCOMPLETE", "Predicate scope or obligation is unbound"
            )
        if type(item["required"]) is not bool or item["required"] is not True:
            raise InputError("OBLIGATION_SET_INCOMPLETE", "Version-1 predicates must be mandatory")
        if item["applicability"] != "required" or item["authority_ref"] != record["id"]:
            raise InputError(
                "TAILORING_UNVERIFIED", "Predicate applicability lacks reviewed authority"
            )
        for field in ("source_ref", "policy_rule_ref"):
            nonempty(item[field], pointer + "/" + field)
        selected.append(item)
    if {item["obligation_id"] for item in selected} != set(obligations):
        raise InputError("OBLIGATION_SET_INCOMPLETE", "One or more obligations are unclassified")
    return sorted(selected, key=lambda item: item["predicate_id"])
