"""Authenticate human judgment and derive current-use lifecycle without mutation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from score_sw_fabric.assurance.models import (
    MAX_DECISIONS,
    MAX_FINDINGS,
    bounded_list,
    domain,
    exact,
    instant,
    nonempty,
    scope,
    sha,
    unique_strings,
    verify_digest,
    version,
)
from score_sw_fabric.assurance.origins import validate_profile, verify_receipt
from score_sw_fabric.process_source.reader import InputError

DECISION_FIELDS = {
    "decision_id",
    "assurance_domain",
    "actor_id",
    "role",
    "authority_ref",
    "identity_provider",
    "authentication_method",
    "independence",
    "subject_digest",
    "scope",
    "obligation_ids",
    "gate_ids",
    "policy_digest",
    "outcome",
    "rationale",
    "conditions",
    "issued_at",
    "valid_from",
    "valid_until",
    "supersedes",
    "receipt_ref",
    "digest",
}
OUTCOMES = {"approve", "reject", "conditional_approve", "request_changes", "withdraw", "no_impact"}


def classify_decision(
    value: Any,
    receipt: Any,
    subject: dict[str, Any],
    policy: dict[str, Any],
    profile: dict[str, Any],
    *,
    requested_domain: str,
    requested_scope: dict[str, str],
    gate_id: str,
    as_of: datetime,
    seen_sequences: set[tuple[str, str, str]] | None = None,
    discharged_conditions: set[str] | None = None,
    allow_no_impact: bool = False,
) -> dict[str, Any]:
    is_no_impact = isinstance(value, dict) and value.get("outcome") == "no_impact"
    record = version(
        value,
        "assurance_decision",
        DECISION_FIELDS | ({"baseline_change"} if is_no_impact else set()),
        "/decision",
    )
    verify_digest(record, "/decision")
    verify_digest(subject, "/subject")
    verify_digest(policy, "/policy")
    validate_profile(profile)
    selected_domain = domain(requested_domain, "/assurance_domain")
    scope(requested_scope, "/scope")
    if record["outcome"] not in OUTCOMES:
        raise InputError("FIELD_UNKNOWN", "Unknown human decision outcome")
    if is_no_impact:
        change = exact(
            record["baseline_change"],
            {
                "prior_assessment_digest",
                "prior_subject_digest",
                "current_subject_digest",
                "prior_policy_digest",
                "current_policy_digest",
                "changed_bindings",
            },
            "/decision/baseline_change",
        )
        for name in (
            "prior_assessment_digest",
            "prior_subject_digest",
            "current_subject_digest",
            "prior_policy_digest",
            "current_policy_digest",
        ):
            sha(change[name], f"/decision/baseline_change/{name}")
        paths = bounded_list(
            change["changed_bindings"], MAX_FINDINGS, "/decision/baseline_change/changed_bindings"
        )
        if (
            not paths
            or any(
                not isinstance(path, str)
                or not (path.startswith(("/subject/", "/policy/")) or path == "/as_of")
                for path in paths
            )
            or paths != sorted(set(paths))
        ):
            raise InputError("FIELD_TYPE", "No-impact paths must be unique sorted subject bindings")
    for field in (
        "decision_id",
        "actor_id",
        "role",
        "authority_ref",
        "identity_provider",
        "authentication_method",
        "rationale",
    ):
        nonempty(record[field], "/decision/" + field, max_length=4096)
    sha(record["subject_digest"], "/decision/subject_digest")
    sha(record["policy_digest"], "/decision/policy_digest")
    if record["receipt_ref"] is not None:
        sha(record["receipt_ref"], "/decision/receipt_ref")
    if record["supersedes"] is not None:
        nonempty(record["supersedes"], "/decision/supersedes", max_length=256)
    ids = unique_strings(record["obligation_ids"], MAX_DECISIONS, "/decision/obligation_ids")
    gates = unique_strings(record["gate_ids"], MAX_DECISIONS, "/decision/gate_ids")
    conditions = bounded_list(record["conditions"], MAX_DECISIONS, "/decision/conditions")
    independence = exact(
        record["independence"],
        {"rule_ids", "checked_relationships", "result"},
        "/decision/independence",
    )
    rules = unique_strings(
        independence["rule_ids"], MAX_DECISIONS, "/decision/independence/rule_ids"
    )
    bounded_list(
        independence["checked_relationships"],
        MAX_DECISIONS,
        "/decision/independence/checked_relationships",
    )
    issued = instant(record["issued_at"], "/decision/issued_at")
    start = instant(record["valid_from"], "/decision/valid_from")
    end = instant(record["valid_until"], "/decision/valid_until")
    reasons: list[str] = []
    if is_no_impact and not allow_no_impact:
        reasons.append("NO_IMPACT_CONTEXT_REQUIRED")
    if (
        record["assurance_domain"] != selected_domain
        or subject["assurance_domain"] != selected_domain
    ):
        reasons.append("DOMAIN_MISMATCH")
    if record["subject_digest"] != subject["digest"]:
        reasons.append("SUBJECT_MISMATCH")
    if record["policy_digest"] != policy["digest"]:
        reasons.append("POLICY_MISMATCH")
    if record["scope"] != requested_scope or subject["scope"] != requested_scope:
        reasons.append("SCOPE_MISMATCH")
    if gate_id not in gates or not ids or not set(ids).issubset(subject["expected_obligation_ids"]):
        reasons.append("SCOPE_MISMATCH")
    if not start <= issued <= end or as_of > end or as_of < start:
        reasons.append("DECISION_EXPIRED")
    if conditions and not set(conditions).issubset(discharged_conditions or set()):
        reasons.append("CONDITION_UNMET")
    role_assignments = [
        item
        for item in profile["role_assignments"]
        if item.get("actor_id") == record["actor_id"]
        and item.get("role") == record["role"]
        and item.get("authority_ref") == record["authority_ref"]
        and requested_scope["id"] in item.get("scope_ids", [])
        and instant(item.get("valid_from"), "/role/valid_from") <= issued
        and as_of <= instant(item.get("valid_until"), "/role/valid_until")
    ]
    if len(role_assignments) != 1 or record["role"] not in policy["required_roles"]:
        reasons.append("ROLE_UNAUTHORIZED")
    providers = [
        item
        for item in profile["identity_providers"]
        if item.get("id") == record["identity_provider"]
        and item.get("authentication_method") == record["authentication_method"]
        and isinstance(receipt, dict)
        and item.get("issuer_id") == receipt.get("issuer_id")
    ]
    if len(providers) != 1:
        reasons.append("ACTOR_UNAUTHENTICATED")
    applicable_rules = [item for item in profile["independence_rules"] if item.get("id") in rules]
    if (
        not set(policy["independence_rules"]).issubset(rules)
        or len(applicable_rules) != len(rules)
        or independence["result"] != "passed"
        or any(
            record["actor_id"] in item.get("disallowed_actor_ids", []) for item in applicable_rules
        )
    ):
        reasons.append("INDEPENDENCE_FAILED")
    if not isinstance(receipt, dict):
        reasons.append("ORIGIN_UNVERIFIED")
    else:
        if receipt.get("issued_at") != record["issued_at"]:
            reasons.append("TIME_BASIS_UNTRUSTED")
        reasons.extend(
            verify_receipt(
                record,
                receipt,
                profile,
                payload_kind="assurance_decision",
                requested_domain=selected_domain,
                requested_scope=requested_scope,
                as_of=as_of,
                seen_sequences=seen_sequences,
            )
        )
    return {
        "decision_id": record["decision_id"],
        "decision_digest": record["digest"],
        "assurance_domain": selected_domain,
        "subject_digest": record["subject_digest"],
        "gate_ids": gates,
        "obligation_ids": ids,
        "scope": record["scope"],
        "outcome": record["outcome"],
        "role": record["role"],
        "policy_digest": record["policy_digest"],
        "supersedes": record["supersedes"],
        "eligible": not reasons,
        "approves": not reasons and record["outcome"] in {"approve", "conditional_approve"},
        "reason_codes": sorted(set(reasons)),
    }


def reconcile_decisions(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute current use; preserve source records and input classification dictionaries."""
    current = [{**item, "reason_codes": list(item["reason_codes"])} for item in results]
    ids = [item["decision_id"] for item in current]
    if len(ids) != len(set(ids)):
        raise InputError("DUPLICATE_ID", "Duplicate decision ID")
    by_id = {item["decision_id"]: item for item in current}
    for item in current:
        prior_id = item["supersedes"]
        if not item["eligible"] or prior_id is None:
            continue
        prior = by_id.get(prior_id)
        if prior is None or prior["subject_digest"] != item["subject_digest"]:
            item["reason_codes"].append("SUPERSESSION_UNVERIFIED")
            item["eligible"] = False
            item["approves"] = False
            continue
        prior["reason_codes"].append(
            "DECISION_WITHDRAWN" if item["outcome"] == "withdraw" else "DECISION_SUPERSEDED"
        )
        prior["eligible"] = False
        prior["approves"] = False
    live = [
        item
        for item in current
        if item["eligible"] and item["outcome"] not in {"withdraw", "no_impact"}
    ]
    if len(live) > 1:
        for item in live:
            item["reason_codes"].append("DECISION_CONFLICT")
            item["eligible"] = False
            item["approves"] = False
    for item in current:
        item["reason_codes"] = sorted(set(item["reason_codes"]))
    return current
