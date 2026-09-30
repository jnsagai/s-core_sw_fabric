"""Evaluate one exact scoped gate with complete predicate results and stable precedence."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.decisions import classify_decision, reconcile_decisions
from score_sw_fabric.assurance.evidence import classify_evidence
from score_sw_fabric.assurance.freshness import assess_freshness
from score_sw_fabric.assurance.models import (
    MAX_DECISIONS,
    MAX_EVIDENCE,
    MAX_REFERENCES,
    digest,
    seal,
    sha,
)
from score_sw_fabric.assurance.origins import replayed_payloads, validate_profile
from score_sw_fabric.assurance.predicates import expected_predicates
from score_sw_fabric.process_source.reader import InputError

ACTIONS = {
    "PREDICATE_FAILED": "Repair the measured failure or obtain a new authenticated decision.",
    "PREDICATE_BLOCKED": "Obtain the missing eligible evidence or authorized human decision.",
    "PRODUCTION_ORIGIN_UNAVAILABLE": (
        "Provision an owner-controlled production trust and time context."
    ),
    "TRACE_NOT_EVALUATED": "Run and bind a matching 004 trace report.",
}


def _receipts(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for receipt in records:
        key = sha(receipt.get("payload_digest"), "/receipt/payload_digest")
        if key in result:
            raise InputError("DUPLICATE_ID", "Duplicate receipt for one payload")
        result[key] = receipt
    return result


def evaluate_gate(
    subject: dict[str, Any],
    policy: dict[str, Any],
    profile: dict[str, Any],
    evidence: list[dict[str, Any]],
    evidence_receipts: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    decision_receipts: list[dict[str, Any]],
    *,
    requested_domain: str,
    requested_scope: dict[str, str],
    gate_id: str,
    as_of: datetime,
    raw_root: Path,
    mode: str = "normal",
    prior_assessment: dict[str, Any] | None = None,
    artifact_impact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if mode not in {"normal", "not_started", "reuse_prior", "whole_gate_not_applicable"}:
        raise InputError("FIELD_UNKNOWN", "Unknown gate evaluation mode")
    predicates = expected_predicates(
        subject,
        policy,
        gate_id=gate_id,
        requested_domain=requested_domain,
        requested_scope=requested_scope,
    )
    validate_profile(profile)
    if len(predicates) > profile["limits"]["predicates"]:
        raise InputError("LIMIT_EXCEEDED", "Gate predicate count exceeds trust bound")
    if len(evidence_receipts) + len(decision_receipts) > min(
        MAX_REFERENCES, profile["limits"]["references"]
    ):
        raise InputError("LIMIT_EXCEEDED", "Gate receipt count exceeds trust bound")
    if len(evidence) > min(
        MAX_EVIDENCE, policy["limits"]["evidence"], profile["limits"]["evidence"]
    ) or len(decisions) > min(
        MAX_DECISIONS, policy["limits"]["decisions"], profile["limits"]["decisions"]
    ):
        raise InputError("LIMIT_EXCEEDED", "Gate input count exceeds policy or trust bounds")
    if mode == "reuse_prior":
        if prior_assessment is None:
            raise InputError("CLOSURE_MISSING", "Prior assessment is required for reuse")
        freshness = assess_freshness(
            prior_assessment,
            subject,
            policy,
            profile,
            evidence,
            decisions,
            as_of=as_of.isoformat().replace("+00:00", "Z"),
            decision_receipts=decision_receipts,
            current_receipts=evidence_receipts + decision_receipts,
            artifact_impact=artifact_impact,
        )
        if freshness["state"] == "stale":
            previous = prior_assessment["gate_results"][0]
            stale_results = [
                {
                    **item,
                    "state": "stale",
                    "reason_codes": ["ASSESSMENT_STALE"],
                    "required_action": "Reassess the changed current baseline.",
                }
                for item in previous["predicate_results"]
            ]
            return seal(
                {
                    **previous,
                    "subject_digest": subject["digest"],
                    "policy_digest": policy["digest"],
                    "trust_profile_digest": profile["digest"],
                    "as_of": as_of.isoformat().replace("+00:00", "Z"),
                    "outcome": "stale",
                    "evaluation_mode": mode,
                    "predicate_results": stale_results,
                    "evidence_digests": sorted(item["digest"] for item in evidence),
                    "decision_digests": sorted(item["digest"] for item in decisions),
                    "unmet_predicate_ids": [item["predicate_id"] for item in stale_results],
                    "unmet_obligation_ids": sorted(
                        {item["obligation_id"] for item in stale_results}
                    ),
                    "reason_codes": ["ASSESSMENT_STALE"],
                    "required_actions": ["Reassess the changed current baseline."],
                    "next_route": policy["outcome_routes"].get("stale", "reassess"),
                    "freshness": freshness,
                    "digest": None,
                }
            )
    evidence_lookup = _receipts(evidence_receipts)
    decision_lookup = _receipts(decision_receipts)
    observations = (
        [
            classify_evidence(
                item,
                evidence_lookup.get(digest(item, exclude="__none__")),
                subject,
                policy,
                profile,
                requested_domain=requested_domain,
                requested_scope=requested_scope,
                as_of=as_of,
                raw_root=raw_root,
            )
            for item in evidence
        ]
        if mode != "not_started"
        else []
    )
    replayed = replayed_payloads(evidence_receipts + decision_receipts)
    for source, item in zip(evidence if mode != "not_started" else [], observations, strict=True):
        if digest(source, exclude="__none__") in replayed:
            item["eligible"] = False
            item["reason_codes"] = sorted(set(item["reason_codes"] + ["RECEIPT_REPLAY"]))
    judgments = (
        reconcile_decisions(
            [
                classify_decision(
                    item,
                    decision_lookup.get(digest(item, exclude="__none__")),
                    subject,
                    policy,
                    profile,
                    requested_domain=requested_domain,
                    requested_scope=requested_scope,
                    gate_id=gate_id,
                    as_of=as_of,
                    discharged_conditions={
                        observation["evidence_id"]
                        for observation in observations
                        if observation["eligible"]
                    },
                )
                for item in decisions
            ]
        )
        if mode != "not_started"
        else []
    )
    for source, item in zip(decisions if mode != "not_started" else [], judgments, strict=True):
        if digest(source, exclude="__none__") in replayed:
            item["eligible"] = False
            item["approves"] = False
            item["reason_codes"] = sorted(set(item["reason_codes"] + ["RECEIPT_REPLAY"]))
    if len({item["evidence_id"] for item in observations}) != len(observations):
        raise InputError("DUPLICATE_ID", "Duplicate evidence ID")
    evidence_by_id = {item["evidence_id"]: item for item in observations}
    results: list[dict[str, Any]] = []
    for predicate in predicates:
        kind = predicate["predicate_class"]
        obligation = predicate["obligation_id"]
        reasons: list[str] = []
        evidence_ids: list[str] = []
        decision_ids: list[str] = []
        if mode == "not_started":
            state = "not_evaluated"
            reasons.append("EVALUATION_NOT_STARTED")
        elif kind == "deterministic_check":
            if predicate["check"] == "candidate_valid":
                satisfied = bool(subject["artifact_candidate"].get("index_digest"))
            elif predicate["check"] == "trace_obligation_satisfied":
                report = subject.get("artifact_report")
                satisfied = (
                    isinstance(report, dict)
                    and report.get("status") == "passed"
                    and obligation in report.get("expected_obligation_ids", [])
                )
            else:
                raise InputError("FIELD_UNKNOWN", "Unsupported deterministic check")
            state = "satisfied" if satisfied else "blocked"
            if state == "blocked":
                reasons.append("PREDICATE_BLOCKED")
        elif kind == "trusted_evidence":
            selected = evidence_by_id.get(predicate["evidence_id"])
            if selected is None or obligation not in selected["obligation_ids"]:
                state = "blocked"
                reasons.append("PREDICATE_BLOCKED")
            else:
                evidence_ids.append(selected["evidence_id"])
                if not selected["eligible"]:
                    state = "blocked"
                    reasons.extend(selected["reason_codes"])
                elif selected["result"] == predicate["acceptable_result"]:
                    state = "satisfied"
                elif selected["result"] == "fail":
                    state = "failed"
                    reasons.append("PREDICATE_FAILED")
                else:
                    state = "blocked"
                    reasons.append("RESULT_UNKNOWN")
        else:
            selected_judgments = [
                item
                for item in judgments
                if gate_id in item["gate_ids"]
                and obligation in item["obligation_ids"]
                and item["role"] == predicate["role"]
            ]
            if not selected_judgments:
                state = "blocked"
                reasons.append(
                    "ROLE_UNAUTHORIZED"
                    if any(
                        gate_id in item["gate_ids"] and obligation in item["obligation_ids"]
                        for item in judgments
                    )
                    else "PREDICATE_BLOCKED"
                )
            elif any(not item["eligible"] for item in selected_judgments):
                state = "blocked"
                decision_ids = [item["decision_id"] for item in selected_judgments]
                reasons.extend(code for item in selected_judgments for code in item["reason_codes"])
            elif any(
                item["outcome"] in {"reject", "request_changes"} for item in selected_judgments
            ):
                state = "failed"
                reasons.append("PREDICATE_FAILED")
                decision_ids = [item["decision_id"] for item in selected_judgments]
            elif any(item["approves"] for item in selected_judgments):
                state = "satisfied"
                decision_ids = [item["decision_id"] for item in selected_judgments]
            else:
                state = "blocked"
                reasons.append("PREDICATE_BLOCKED")
        if requested_domain == "production" and mode != "not_started":
            state = "blocked"
            reasons.append("PRODUCTION_ORIGIN_UNAVAILABLE")
        results.append(
            {
                "predicate_id": predicate["predicate_id"],
                "obligation_id": obligation,
                "state": state,
                "evidence_ids": sorted(evidence_ids),
                "decision_ids": sorted(decision_ids),
                "reason_codes": sorted(set(reasons)),
                "required_action": ACTIONS["PREDICATE_BLOCKED"]
                if state == "blocked"
                else (ACTIONS["PREDICATE_FAILED"] if state == "failed" else "None"),
            }
        )
    states = {item["state"] for item in results}
    if mode == "not_started":
        outcome = "not_evaluated"
    elif mode == "whole_gate_not_applicable":
        rule = policy["not_applicable_rules"]
        tailoring_decisions = [
            item
            for item in judgments
            if item["decision_id"] == rule.get("decision_id")
            and item["eligible"]
            and item["approves"]
            and set(item["obligation_ids"]) == set(subject["expected_obligation_ids"])
        ]
        authorized = (
            rule.get("whole_gate") is True
            and rule.get("gate_id") == gate_id
            and rule.get("subject_digest") == subject["digest"]
            and len(tailoring_decisions) == 1
            and requested_domain != "production"
        )
        outcome = "not_applicable" if authorized else "blocked"
        for item in results:
            item["state"] = "not_applicable" if authorized else "blocked"
            item["reason_codes"] = [] if authorized else ["TAILORING_UNVERIFIED"]
            item["required_action"] = (
                "None" if authorized else "Obtain exact authenticated tailoring."
            )
            item["decision_ids"] = [tailoring_decisions[0]["decision_id"]] if authorized else []
    elif "blocked" in states:
        outcome = "blocked"
    elif "failed" in states:
        outcome = "fail"
    else:
        outcome = "pass"
    reason_codes = sorted({code for item in results for code in item["reason_codes"]})
    unmet = sorted(item["predicate_id"] for item in results if item["state"] != "satisfied")
    result = {
        "schema_version": 1,
        "kind": "assurance_gate_result",
        "gate_id": gate_id,
        "assurance_domain": requested_domain,
        "scope": requested_scope,
        "subject_digest": subject["digest"],
        "policy_digest": policy["digest"],
        "trust_profile_digest": profile["digest"],
        "evaluator_identity": "score-sw-fabric-assurance-v1",
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "time_basis_ref": "fixture-request-time"
        if requested_domain == "fixture_contract"
        else "untrusted-request-time",
        "outcome": outcome,
        "evaluation_mode": mode,
        "expected_predicate_ids": [item["predicate_id"] for item in predicates],
        "predicate_results": results,
        "evidence_digests": sorted(item["digest"] for item in evidence),
        "decision_digests": sorted(item["digest"] for item in decisions),
        "unmet_predicate_ids": unmet,
        "unmet_obligation_ids": sorted(
            {item["obligation_id"] for item in results if item["state"] != "satisfied"}
        ),
        "reason_codes": reason_codes,
        "required_actions": sorted(
            {ACTIONS.get(code, ACTIONS["PREDICATE_BLOCKED"]) for code in reason_codes}
        ),
        "next_route": policy["outcome_routes"][outcome],
        "limitations": ["Fixture contract result; no production acceptance."]
        if requested_domain == "fixture_contract"
        else ["Production authority and protected time remain unavailable."],
    }
    return seal(result)
