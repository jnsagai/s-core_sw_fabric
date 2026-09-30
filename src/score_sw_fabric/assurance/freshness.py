"""Conservative immutable current-use comparison over every bound identity."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.assurance.models import (
    MAX_FINDINGS,
    digest,
    exact,
    instant,
    seal,
    verify_digest,
)
from score_sw_fabric.process_source.reader import InputError


def _differences(before: Any, after: Any, pointer: str, result: list[str]) -> None:
    if len(result) > MAX_FINDINGS:
        raise InputError("LIMIT_EXCEEDED", "Freshness changes exceed finding limit")
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            if key not in before or key not in after:
                result.append(f"{pointer}/{key}")
            else:
                _differences(before[key], after[key], f"{pointer}/{key}", result)
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            result.append(pointer)
        else:
            for index, (left, right) in enumerate(zip(before, after, strict=True)):
                _differences(left, right, f"{pointer}/{index}", result)
    elif before != after:
        result.append(pointer)
    if len(result) > MAX_FINDINGS:
        raise InputError("LIMIT_EXCEEDED", "Freshness changes exceed finding limit")


def _reviewed_no_impact(
    prior: dict[str, Any],
    subject: dict[str, Any],
    policy: dict[str, Any],
    profile: dict[str, Any],
    decision: dict[str, Any],
    receipts: list[dict[str, Any]],
    changed: list[str],
    as_of: str,
) -> bool:
    """A signed scoped review may narrow impact, never revive an old gate result."""
    from score_sw_fabric.assurance.decisions import classify_decision
    from score_sw_fabric.assurance.origins import replayed_payloads

    rule = policy.get("freshness_rules", {}).get("no_impact")
    if not isinstance(rule, dict):
        return False
    exact(rule, {"role", "authority_ref", "allowed_paths"}, "/policy/freshness_rules/no_impact")
    allowed = rule["allowed_paths"]
    if (
        not isinstance(allowed, list)
        or len(allowed) > MAX_FINDINGS
        or any(
            not isinstance(path, str)
            or not (path.startswith(("/subject/", "/policy/")) or path == "/as_of")
            for path in allowed
        )
        or allowed != sorted(set(allowed))
    ):
        raise InputError("FIELD_TYPE", "Invalid no-impact policy paths")
    if not changed or not set(changed).issubset(allowed):
        return False
    previous_policy = prior["policy_refs"][0]["record"]
    policy_paths = [path for path in changed if path.startswith("/policy/")]
    expected_policy_paths = ["/policy/digest"] + [
        f"/policy/predicates/{index}/subject_ref"
        for index in range(len(previous_policy["predicates"]))
    ]
    if policy_paths:
        if (
            policy_paths != sorted(expected_policy_paths)
            or len(previous_policy["predicates"]) != len(policy["predicates"])
            or previous_policy["freshness_rules"] != policy["freshness_rules"]
            or any(
                old.get("subject_ref") != prior["subject"]["manifest"]["digest"]
                or new.get("subject_ref") != subject["digest"]
                for old, new in zip(
                    previous_policy["predicates"], policy["predicates"], strict=True
                )
            )
        ):
            return False
    previous_gate = prior["gate_results"][0]
    binding = decision.get("baseline_change")
    if not isinstance(binding, dict) or binding != {
        "prior_assessment_digest": prior["digest"],
        "prior_subject_digest": prior["subject"]["manifest"]["digest"],
        "current_subject_digest": subject["digest"],
        "prior_policy_digest": previous_policy["digest"],
        "current_policy_digest": policy["digest"],
        "changed_bindings": changed,
    }:
        return False
    if (
        decision.get("role") != rule["role"]
        or decision.get("authority_ref") != rule["authority_ref"]
        or decision.get("conditions") != []
        or decision.get("supersedes") is not None
        or decision.get("scope") != previous_gate["scope"]
        or decision.get("gate_ids") != [previous_gate["gate_id"]]
        or decision.get("obligation_ids") != sorted(subject["expected_obligation_ids"])
    ):
        return False
    selected = [
        receipt
        for receipt in receipts
        if receipt.get("payload_digest") == digest(decision, exclude="__none__")
    ]
    if len(selected) != 1 or digest(decision, exclude="__none__") in replayed_payloads(
        prior["receipts"] + receipts
    ):
        return False
    result = classify_decision(
        decision,
        selected[0],
        subject,
        policy,
        profile,
        requested_domain=subject["assurance_domain"],
        requested_scope=subject["scope"],
        gate_id=previous_gate["gate_id"],
        as_of=instant(as_of, "/as_of"),
        allow_no_impact=True,
    )
    return bool(result["eligible"])


def assess_freshness(
    prior: dict[str, Any],
    current_subject: dict[str, Any],
    current_policy: dict[str, Any],
    current_profile: dict[str, Any],
    current_evidence: list[dict[str, Any]],
    current_decisions: list[dict[str, Any]],
    *,
    as_of: str,
    decision_receipts: list[dict[str, Any]] | None = None,
    current_receipts: list[dict[str, Any]] | None = None,
    artifact_impact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare current bindings without changing the prior assessment or signed facts."""
    verify_digest(prior, "/prior_assessment")
    if prior.get("kind") != "assurance_assessment" or len(prior.get("gate_results", [])) != 1:
        raise InputError("KIND_MISMATCH", "Expected one prior portable assessment")
    verify_digest(current_subject, "/current_subject")
    verify_digest(current_policy, "/current_policy")
    verify_digest(current_profile, "/current_trust_profile")
    for index, item in enumerate(current_evidence):
        verify_digest(item, f"/current_evidence/{index}")
    for index, item in enumerate(current_decisions):
        verify_digest(item, f"/current_decisions/{index}")
    instant(as_of, "/as_of")
    previous_gate = prior["gate_results"][0]
    previous_subject = prior["subject"]["manifest"]
    previous_policy = prior["policy_refs"][0]["record"]
    previous_profile = prior["trust_context_refs"][0]["record"]
    impact_decisions = [item for item in current_decisions if item.get("outcome") == "no_impact"]
    regular_decisions = [item for item in current_decisions if item.get("outcome") != "no_impact"]
    selected_receipts = prior["receipts"] if current_receipts is None else current_receipts
    for index, receipt in enumerate(selected_receipts):
        verify_digest(receipt, f"/current_receipts/{index}", field="receipt_digest")
    review_payloads = {digest(item, exclude="__none__") for item in impact_decisions}

    def sorted_receipts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(records, key=lambda item: (item["payload_kind"], item["payload_digest"]))

    old_receipts = sorted_receipts(prior["receipts"])
    regular_receipts = sorted_receipts(
        [item for item in selected_receipts if item["payload_digest"] not in review_payloads]
    )
    baseline_changed: list[str] = []
    _differences(
        {
            "subject": previous_subject,
            "policy": previous_policy,
            "trust_profile": previous_profile,
            "evidence": sorted(prior["evidence_records"], key=lambda item: item["evidence_id"]),
            "decisions": sorted(prior["decision_records"], key=lambda item: item["decision_id"]),
            "receipts": old_receipts,
            "as_of": previous_gate["as_of"],
        },
        {
            "subject": current_subject,
            "policy": current_policy,
            "trust_profile": current_profile,
            "evidence": sorted(current_evidence, key=lambda item: item["evidence_id"]),
            "decisions": sorted(regular_decisions, key=lambda item: item["decision_id"]),
            "receipts": regular_receipts,
            "as_of": as_of,
        },
        "",
        baseline_changed,
    )
    baseline_changed = sorted(set(baseline_changed))
    reviewed = (
        len(impact_decisions) == 1
        and bool(baseline_changed)
        and all(
            path.startswith(("/subject/", "/policy/")) or path == "/as_of"
            for path in baseline_changed
        )
        and _reviewed_no_impact(
            prior,
            current_subject,
            current_policy,
            current_profile,
            impact_decisions[0],
            decision_receipts or [],
            baseline_changed,
            as_of,
        )
    )
    compared_decisions = regular_decisions if reviewed else current_decisions
    old_bindings = {
        "subject": previous_subject,
        "policy": previous_policy,
        "trust_profile": previous_profile,
        "evidence": sorted(prior["evidence_records"], key=lambda item: item["evidence_id"]),
        "decisions": sorted(prior["decision_records"], key=lambda item: item["decision_id"]),
        "receipts": old_receipts,
        "as_of": previous_gate["as_of"],
    }
    new_bindings = {
        "subject": current_subject,
        "policy": current_policy,
        "trust_profile": current_profile,
        "evidence": sorted(current_evidence, key=lambda item: item["evidence_id"]),
        "decisions": sorted(compared_decisions, key=lambda item: item["decision_id"]),
        "receipts": regular_receipts,
        "as_of": as_of,
    }
    changed: list[str] = []
    _differences(old_bindings, new_bindings, "", changed)
    changed = sorted(set(changed))
    if len(changed) > MAX_FINDINGS:
        raise InputError("LIMIT_EXCEEDED", "Freshness changes exceed finding limit")
    subject_changed = any(item.startswith("/subject/") for item in changed)
    trust_changed = any(item.startswith("/trust_profile/") for item in changed)
    policy_changed = any(item.startswith("/policy/") for item in changed)
    time_changed = "/as_of" in changed
    receipt_changed = any(path.startswith("/receipts") for path in changed)

    def receipt_keys(records: list[dict[str, Any]]) -> set[tuple[str, str]]:
        return {(item["payload_kind"], item["payload_digest"]) for item in records}

    receipt_unlinked = receipt_keys(old_receipts) != receipt_keys(regular_receipts)
    native_paths: list[str] = []
    native_unknown = False
    if artifact_impact is not None:
        from score_sw_fabric.compiler.reader import verify_self_digest

        verify_self_digest(artifact_impact, "/artifact_impact")
        if (
            artifact_impact.get("before") != previous_subject["artifact_candidate"]["index_digest"]
            or artifact_impact.get("after") != current_subject["artifact_candidate"]["index_digest"]
        ):
            raise InputError("IMPACT_MISMATCH", "004 impact is not bound to old/new native indexes")
        for entry in artifact_impact["dependency_paths"]:
            native_path = "/native/" + "/".join(
                str(key).replace("~", "~0").replace("/", "~1") for key in entry["path"]
            )
            if len(native_path) > 4096:
                raise InputError("LIMIT_EXCEEDED", "004 dependency path exceeds assurance limit")
            native_paths.append(native_path)
        native_unknown = bool(
            artifact_impact["blockers"]
            or artifact_impact["unknown_dependencies"]
            or artifact_impact["newly_unlinked"]
        )

    def identities(records: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
        selected: dict[str, dict[str, Any]] = {}
        for record in records:
            identifier = record.get(field)
            if not isinstance(identifier, str) or identifier in selected:
                raise InputError("DUPLICATE_ID", f"Invalid or duplicate {field} in freshness set")
            selected[identifier] = record
        return selected

    previous_evidence = identities(prior["evidence_records"], "evidence_id")
    current_evidence_by_id = identities(current_evidence, "evidence_id")
    previous_decisions = identities(prior["decision_records"], "decision_id")
    current_decisions_by_id = identities(compared_decisions, "decision_id")
    all_evidence_ids = set(previous_evidence) | set(current_evidence_by_id)
    all_decision_ids = set(previous_decisions) | set(current_decisions_by_id)
    unlinked = set(previous_evidence) != set(current_evidence_by_id) or set(
        previous_decisions
    ) != set(current_decisions_by_id)
    broad = (
        ((subject_changed or policy_changed) and not reviewed)
        or trust_changed
        or unlinked
        or receipt_unlinked
        or native_unknown
    )
    whole_gate = broad or time_changed or receipt_changed
    impact_paths = sorted(set((["/"] if whole_gate else changed) + native_paths))
    if len(impact_paths) > MAX_FINDINGS:
        raise InputError("LIMIT_EXCEEDED", "Assurance impact exceeds finding limit")
    changed_evidence_ids = {
        identifier
        for identifier in all_evidence_ids
        if previous_evidence.get(identifier) != current_evidence_by_id.get(identifier)
    }
    changed_decision_ids = {
        identifier
        for identifier in all_decision_ids
        if previous_decisions.get(identifier) != current_decisions_by_id.get(identifier)
    }
    evidence_ids = sorted(
        all_evidence_ids if whole_gate or subject_changed else changed_evidence_ids
    )
    decision_ids = sorted(
        all_decision_ids
        if whole_gate or subject_changed or changed_evidence_ids
        else changed_decision_ids
    )
    result = {
        "schema_version": 1,
        "kind": "assurance_freshness",
        "prior_assessment_digest": prior["digest"],
        "prior_subject_digest": previous_subject["digest"],
        "current_subject_digest": current_subject["digest"],
        "changed_bindings": changed,
        "affected_evidence_ids": evidence_ids,
        "affected_decision_ids": decision_ids,
        "affected_gate_ids": [previous_gate["gate_id"]] if changed else [],
        "impact_paths": impact_paths,
        "unknown_dependencies": broad,
        "scope_expansion": "whole_gate"
        if whole_gate
        else ("reviewed_no_impact" if reviewed else "exact_changed_refs"),
        "state": "stale" if changed else "current",
        "reasons": ["ASSESSMENT_STALE"] if changed else [],
    }
    if reviewed:
        result["no_impact_decision_digest"] = impact_decisions[0]["digest"]
    return seal(result)
