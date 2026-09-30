"""Scoped gates freeze a complete expected set and apply fail-closed precedence."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.gates import evaluate_gate
from score_sw_fabric.assurance.models import seal
from score_sw_fabric.assurance.predicates import POLICY_FIELDS
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml
from tests.assurance_support import fixture_receipt

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "tests/fixtures/assurance/passing-scope"
NOW = datetime(2026, 9, 29, 10, tzinfo=UTC)


def _inputs() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    return (
        read_json(BASE / "out/subject.json"),
        read_json(BASE / "policy.json"),
        read_yaml(ROOT / "profiles/assurance-fixture-v1.yaml"),
        [read_json(BASE / "evidence.json")],
        [read_json(BASE / "evidence-receipt.json")],
        [read_json(BASE / "decision.json")],
        [read_json(BASE / "decision-receipt.json")],
    )


def _gate(
    *,
    evidence: list[dict[str, Any]] | None = None,
    evidence_receipts: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    decision_receipts: list[dict[str, Any]] | None = None,
    policy: dict[str, Any] | None = None,
    domain: str = "fixture_contract",
    mode: str = "normal",
    prior_assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    subject, p, profile, e, er, d, dr = _inputs()
    return evaluate_gate(
        subject,
        p if policy is None else policy,
        profile,
        e if evidence is None else evidence,
        er if evidence_receipts is None else evidence_receipts,
        d if decisions is None else decisions,
        dr if decision_receipts is None else decision_receipts,
        requested_domain=domain,
        requested_scope=subject["scope"],
        gate_id="component-verification",
        as_of=NOW,
        raw_root=BASE / "raw",
        mode=mode,
        prior_assessment=prior_assessment,
    )


def test_complete_fixture_gate_passes_with_nonempty_matrix() -> None:
    result = _gate()
    assert result["outcome"] == "pass"
    assert result["assurance_domain"] == "fixture_contract"
    assert len(result["predicate_results"]) == 3
    assert set(result["expected_predicate_ids"]) == {
        item["predicate_id"] for item in result["predicate_results"]
    }
    assert {item["predicate_class"] for item in _inputs()[1]["predicates"]} == {
        "deterministic_check",
        "trusted_evidence",
        "human_decision",
    }
    assert set(_inputs()[0]["expected_obligation_ids"]) == {
        item["obligation_id"] for item in _inputs()[1]["predicates"]
    }


def test_missing_human_review_blocks() -> None:
    result = _gate(decisions=[], decision_receipts=[])
    assert result["outcome"] == "blocked"
    assert "fixture-review" in result["unmet_predicate_ids"]
    assert result["expected_predicate_ids"] == _gate()["expected_predicate_ids"]


@pytest.mark.parametrize(
    ("authority", "code"),
    [
        ({}, "FIELD_UNKNOWN"),
        ({"kind": "fixture_contract", "source_ref": ""}, "FIELD_TYPE"),
        ({"kind": "agent_assertion", "source_ref": "fixture-claim"}, "TAILORING_UNVERIFIED"),
    ],
)
def test_policy_authority_cannot_be_empty_or_agent_claim(
    authority: dict[str, str], code: str
) -> None:
    policy = _inputs()[1]
    policy["authority_source"] = authority
    with pytest.raises(InputError) as error:
        _gate(policy=seal(policy))
    assert error.value.code == code


def test_measurement_failure_fails_when_review_complete() -> None:
    evidence = deepcopy(_inputs()[3][0])
    evidence["result"] = "fail"
    evidence["measurements"] = {"obligation-a": False}
    evidence = seal(evidence)
    receipt = fixture_receipt(evidence, payload_kind="assurance_evidence")
    result = _gate(evidence=[evidence], evidence_receipts=[receipt])
    assert result["outcome"] == "fail"
    assert "fixture-measurement-a" in result["unmet_predicate_ids"]


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("unknown", "RESULT_UNKNOWN"),
        ("timeout", "RESULT_TIMEOUT"),
        ("agent_assertion", "EVIDENCE_UNTRUSTED"),
        ("missing_raw", "RAW_OUTPUT_MISSING"),
    ],
)
def test_one_unavailable_measurement_blocks_gate_with_exact_action(
    change: str, reason: str
) -> None:
    evidence = _inputs()[3][0]
    if change == "unknown":
        evidence["result"] = "unknown"
        evidence["measurements"] = {}
    elif change == "timeout":
        evidence["termination"] = "timeout"
        evidence["result"] = "unknown"
        evidence["measurements"] = {}
    elif change == "agent_assertion":
        evidence["origin_class"] = "agent_assertion"
    else:
        evidence["raw_outputs"] = []
    evidence = seal(evidence)
    receipt = fixture_receipt(evidence, payload_kind="assurance_evidence")
    result = _gate(evidence=[evidence], evidence_receipts=[receipt])
    assert result["outcome"] == "blocked"
    assert reason in result["reason_codes"]
    assert result["reason_codes"] == sorted(set(result["reason_codes"]))
    affected = next(
        item
        for item in result["predicate_results"]
        if item["predicate_id"] == "fixture-measurement-a"
    )
    assert affected["state"] == "blocked"
    assert reason in affected["reason_codes"]
    assert affected["required_action"] == (
        "Obtain the missing eligible evidence or authorized human decision."
    )
    assert result["next_route"] == "obtain_evidence"


def test_measured_failure_plus_missing_review_is_blocked_but_retains_failure() -> None:
    evidence = deepcopy(_inputs()[3][0])
    evidence["result"] = "fail"
    evidence["measurements"] = {"obligation-a": False}
    evidence = seal(evidence)
    receipt = fixture_receipt(evidence, payload_kind="assurance_evidence")
    result = _gate(
        evidence=[evidence], evidence_receipts=[receipt], decisions=[], decision_receipts=[]
    )
    assert result["outcome"] == "blocked"
    assert {item["state"] for item in result["predicate_results"]} == {
        "satisfied",
        "failed",
        "blocked",
    }


def test_empty_or_unclassified_expected_set_cannot_pass() -> None:
    policy = deepcopy(_inputs()[1])
    policy["predicates"] = []
    policy = seal(policy)
    with pytest.raises(InputError):
        _gate(policy=policy)


@pytest.mark.parametrize(
    "change",
    ["selected_plan_only", "missing_obligation", "unclassified_obligation"],
)
def test_policy_cannot_shrink_or_leave_expected_denominator_unclassified(change: str) -> None:
    policy = _inputs()[1]
    if change == "selected_plan_only":
        policy["expected_set_rule"]["plan_instances"] = "selected"
    elif change == "missing_obligation":
        policy["predicates"] = [
            item for item in policy["predicates"] if item["obligation_id"] != "obligation-a"
        ]
    else:
        policy["predicates"] = [
            item for item in policy["predicates"] if item["obligation_id"] != "obligation-b"
        ]
    with pytest.raises(InputError) as error:
        _gate(policy=seal(policy))
    assert error.value.code == "OBLIGATION_SET_INCOMPLETE"


def test_production_request_rejects_fixture_inputs() -> None:
    assert _gate(domain="production")["outcome"] == "blocked"


def test_not_started_gate_is_not_evaluated_not_vacuous_pass() -> None:
    result = _gate(
        evidence=[], evidence_receipts=[], decisions=[], decision_receipts=[], mode="not_started"
    )
    assert result["outcome"] == "not_evaluated"
    assert len(result["predicate_results"]) == 3
    assert all(item["state"] == "not_evaluated" for item in result["predicate_results"])


def test_changed_prior_assessment_is_stale() -> None:
    evidence = deepcopy(_inputs()[3][0])
    evidence["result"] = "fail"
    evidence["measurements"] = {"obligation-a": False}
    evidence = seal(evidence)
    receipt = fixture_receipt(evidence, payload_kind="assurance_evidence")
    prior = read_json(BASE / "out/assessment.json")
    result = _gate(
        evidence=[evidence], evidence_receipts=[receipt], mode="reuse_prior", prior_assessment=prior
    )
    assert result["outcome"] == "stale"
    assert "ASSESSMENT_STALE" in result["reason_codes"]


def test_whole_gate_not_applicable_needs_exact_signed_tailoring() -> None:
    subject, policy, _, _, _, decisions, _ = _inputs()
    policy = deepcopy(policy)
    policy["not_applicable_rules"] = {
        "whole_gate": True,
        "gate_id": "component-verification",
        "subject_digest": subject["digest"],
        "decision_id": "fixture-decision-005",
    }
    policy = seal(policy)
    decision = deepcopy(decisions[0])
    decision["policy_digest"] = policy["digest"]
    decision["rationale"] = "Fixture-only explicit whole-gate tailoring."
    decision = seal(decision)
    receipt = fixture_receipt(
        decision,
        payload_kind="assurance_decision",
        issued_at=decision["issued_at"],
        nonce="fixture-decision-sequence-1",
    )
    tailored = _gate(
        policy=policy,
        decisions=[decision],
        decision_receipts=[receipt],
        mode="whole_gate_not_applicable",
    )
    assert tailored["outcome"] == "not_applicable"
    assert tailored["expected_predicate_ids"] == _gate(policy=policy)["expected_predicate_ids"]
    assert (
        _gate(policy=policy, decisions=[], decision_receipts=[], mode="whole_gate_not_applicable")[
            "outcome"
        ]
        == "blocked"
    )


def test_replayed_receipt_sequence_blocks_even_original_eligible_evidence() -> None:
    original = _inputs()[3][0]
    second = deepcopy(original)
    second["evidence_id"] = "fixture-evidence-replay"
    second = seal(second)
    replay = fixture_receipt(second, payload_kind="assurance_evidence", nonce="fixture-sequence-1")
    result = _gate(evidence=[original, second], evidence_receipts=[_inputs()[4][0], replay])
    assert result["outcome"] == "blocked"
    assert "RECEIPT_REPLAY" in result["reason_codes"]


def test_replayed_supersession_cannot_change_reason_with_input_order() -> None:
    original = _inputs()[5][0]
    replacement = deepcopy(original)
    replacement["decision_id"] = "fixture-replacement-005"
    replacement["supersedes"] = original["decision_id"]
    replacement = seal(replacement)
    receipts = [
        _inputs()[6][0],
        fixture_receipt(
            replacement,
            payload_kind="assurance_decision",
            issued_at=replacement["issued_at"],
            nonce="fixture-decision-sequence-1",
        ),
    ]
    forward = _gate(
        decisions=[original, replacement],
        decision_receipts=receipts,
    )
    reversed_order = _gate(
        decisions=[replacement, original],
        decision_receipts=list(reversed(receipts)),
    )
    assert forward == reversed_order
    assert forward["outcome"] == "blocked"
    assert "RECEIPT_REPLAY" in forward["reason_codes"]


def test_wrong_human_role_cannot_satisfy_specific_review_predicate() -> None:
    subject, policy, profile, _, _, decisions, _ = _inputs()
    policy = deepcopy(policy)
    policy["required_roles"] = ["component_reviewer", "alternate_reviewer"]
    policy = seal(policy)
    profile = deepcopy(profile)
    profile["role_assignments"].append(
        {
            "actor_id": "fixture-reviewer-005",
            "authority_ref": "fixture-authority-005",
            "role": "alternate_reviewer",
            "scope_ids": ["component-005"],
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_until": "2027-01-01T00:00:00Z",
        }
    )
    profile = seal(profile)
    decision = deepcopy(decisions[0])
    decision["role"] = "alternate_reviewer"
    decision["policy_digest"] = policy["digest"]
    decision = seal(decision)
    receipt = fixture_receipt(
        decision,
        payload_kind="assurance_decision",
        issued_at=decision["issued_at"],
        nonce="fixture-decision-sequence-1",
    )
    evidence = deepcopy(_inputs()[3][0])
    evidence["execution_policy_digest"] = policy["digest"]
    evidence = seal(evidence)
    evidence_receipt = fixture_receipt(evidence, payload_kind="assurance_evidence")
    result = evaluate_gate(
        subject,
        policy,
        profile,
        [evidence],
        [evidence_receipt],
        [decision],
        [receipt],
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        gate_id="component-verification",
        as_of=NOW,
        raw_root=BASE / "raw",
    )
    assert result["outcome"] == "blocked"
    assert "ROLE_UNAUTHORIZED" in result["reason_codes"]


def test_conditioned_approval_uses_only_eligible_unreplayed_evidence() -> None:
    decision = deepcopy(_inputs()[5][0])
    decision["outcome"] = "conditional_approve"
    decision["conditions"] = ["fixture-evidence-005"]
    decision = seal(decision)
    receipt = fixture_receipt(
        decision,
        payload_kind="assurance_decision",
        issued_at=decision["issued_at"],
        nonce="fixture-decision-sequence-1",
    )
    assert _gate(decisions=[decision], decision_receipts=[receipt])["outcome"] == "pass"
    original = _inputs()[3][0]
    replayed = deepcopy(original)
    replayed["evidence_id"] = "fixture-evidence-replay"
    replayed = seal(replayed)
    replay_receipt = fixture_receipt(
        replayed, payload_kind="assurance_evidence", nonce="fixture-sequence-1"
    )
    result = _gate(
        evidence=[original, replayed],
        evidence_receipts=[_inputs()[4][0], replay_receipt],
        decisions=[decision],
        decision_receipts=[receipt],
    )
    assert result["outcome"] == "blocked"
    assert "CONDITION_UNMET" in result["reason_codes"]


@pytest.mark.parametrize("field", sorted(POLICY_FIELDS))
def test_every_missing_gate_policy_field_is_rejected(field: str) -> None:
    policy = _inputs()[1]
    policy.pop(field)
    with pytest.raises(InputError) as error:
        _gate(policy=policy)
    assert error.value.code == "FIELD_UNKNOWN"
    assert error.value.pointer == "/policy"


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("missing_predicate_field", "FIELD_UNKNOWN"),
        ("duplicate_predicate", "DUPLICATE_ID"),
        ("optional_predicate", "OBLIGATION_SET_INCOMPLETE"),
        ("unknown_predicate_class", "FIELD_UNKNOWN"),
        ("unbound_obligation", "OBLIGATION_SET_INCOMPLETE"),
        ("unreviewed_applicability", "TAILORING_UNVERIFIED"),
    ],
)
def test_one_predicate_change_cannot_pass(change: str, code: str) -> None:
    policy = _inputs()[1]
    predicate = policy["predicates"][0]
    if change == "missing_predicate_field":
        predicate.pop("source_ref")
    elif change == "duplicate_predicate":
        policy["predicates"].append(deepcopy(predicate))
    elif change == "optional_predicate":
        predicate["required"] = False
    elif change == "unknown_predicate_class":
        predicate["predicate_class"] = "self_attested"
    elif change == "unbound_obligation":
        predicate["obligation_id"] = "not-in-subject"
    else:
        predicate["applicability"] = "assumed"
    with pytest.raises(InputError) as error:
        _gate(policy=seal(policy))
    assert error.value.code == code
