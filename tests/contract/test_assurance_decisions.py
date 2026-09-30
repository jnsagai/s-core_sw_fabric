"""A human decision needs authenticated actor authority and exact independence."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.decisions import (
    DECISION_FIELDS,
    classify_decision,
    reconcile_decisions,
)
from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml
from tests.assurance_support import fixture_receipt

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "tests/fixtures/assurance/passing-scope"
NOW = datetime(2026, 9, 29, 10, tzinfo=UTC)


def _inputs() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    return (
        read_json(BASE / "decision.json"),
        read_json(BASE / "decision-receipt.json"),
        read_json(BASE / "out/subject.json"),
        read_json(BASE / "policy.json"),
        read_yaml(ROOT / "profiles/assurance-fixture-v1.yaml"),
    )


def _check(
    decision: dict[str, Any] | None = None,
    receipt: dict[str, Any] | None = None,
    *,
    domain: str = "fixture_contract",
    as_of: datetime = NOW,
) -> dict[str, Any]:
    original, signed, subject, policy, profile = _inputs()
    return classify_decision(
        original if decision is None else decision,
        signed if receipt is None else receipt,
        subject,
        policy,
        profile,
        requested_domain=domain,
        requested_scope=subject["scope"],
        gate_id="component-verification",
        as_of=as_of,
    )


def _resigned(**updates: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    decision = deepcopy(_inputs()[0])
    decision.update(updates)
    decision = seal(decision)
    return decision, fixture_receipt(
        decision, payload_kind="assurance_decision", issued_at=decision["issued_at"]
    )


def test_fixture_human_decision_is_eligible_only_in_fixture_domain() -> None:
    assert _check()["eligible"] is True
    assert _check(domain="production")["eligible"] is False


def test_unsigned_actor_edit_cannot_authenticate() -> None:
    decision = deepcopy(_inputs()[0])
    decision["actor_id"] = "fixture-author-005"
    decision = seal(decision)
    assert "SUBJECT_MISMATCH" in _check(decision)["reason_codes"]


@pytest.mark.parametrize(
    "updates,code",
    [
        ({"role": "release_owner"}, "ROLE_UNAUTHORIZED"),
        ({"subject_digest": "0" * 64}, "SUBJECT_MISMATCH"),
        ({"gate_ids": ["other-gate"]}, "SCOPE_MISMATCH"),
        ({"policy_digest": "0" * 64}, "POLICY_MISMATCH"),
        ({"actor_id": "fixture-author-005"}, "INDEPENDENCE_FAILED"),
        ({"authority_ref": "other-authority"}, "ROLE_UNAUTHORIZED"),
        ({"identity_provider": "other-provider"}, "ACTOR_UNAUTHENTICATED"),
        ({"authentication_method": "unverified-string"}, "ACTOR_UNAUTHENTICATED"),
        (
            {"scope": {"kind": "component", "id": "sibling", "purpose": "fixture verification"}},
            "SCOPE_MISMATCH",
        ),
        ({"obligation_ids": ["other-obligation"]}, "SCOPE_MISMATCH"),
        (
            {
                "independence": {
                    "rule_ids": ["independent_from_author"],
                    "checked_relationships": ["author:fixture-author-005"],
                    "result": "failed",
                }
            },
            "INDEPENDENCE_FAILED",
        ),
        ({"conditions": ["missing-discharge"]}, "CONDITION_UNMET"),
    ],
)
def test_wrong_authority_or_scope_blocks_even_when_signed(
    updates: dict[str, Any], code: str
) -> None:
    decision, receipt = _resigned(**updates)
    assert code in _check(decision, receipt)["reason_codes"]


def test_expiry_blocks_current_eligibility() -> None:
    assert "DECISION_EXPIRED" in _check(as_of=datetime(2026, 10, 1, tzinfo=UTC))["reason_codes"]


def test_rejection_is_authenticated_negative_outcome() -> None:
    decision, receipt = _resigned(outcome="reject")
    result = _check(decision, receipt)
    assert result["eligible"] is True and result["approves"] is False


def test_request_changes_is_authenticated_negative_outcome() -> None:
    decision, receipt = _resigned(outcome="request_changes")
    result = _check(decision, receipt)
    assert result["eligible"] is True and result["approves"] is False


def test_withdrawal_is_new_event_without_mutating_old_record() -> None:
    original = _inputs()[0]
    old = repr(original)
    withdrawal, receipt = _resigned(
        decision_id="fixture-withdraw-005", outcome="withdraw", supersedes=original["decision_id"]
    )
    current = reconcile_decisions([_check(), _check(withdrawal, receipt)])
    assert current[0]["eligible"] is False
    assert "DECISION_WITHDRAWN" in current[0]["reason_codes"]
    assert repr(original) == old


def test_supersession_preserves_old_event_and_invalidates_current_use() -> None:
    original = _inputs()[0]
    old = deepcopy(original)
    replacement, receipt = _resigned(
        decision_id="fixture-replacement-005", supersedes=original["decision_id"]
    )
    current = reconcile_decisions([_check(), _check(replacement, receipt)])
    assert current[0]["eligible"] is False
    assert "DECISION_SUPERSEDED" in current[0]["reason_codes"]
    assert current[1]["eligible"] is True
    assert original == old


@pytest.mark.parametrize(
    ("change", "code"),
    [("revoked_key", "ISSUER_UNTRUSTED"), ("expired_role", "ROLE_UNAUTHORIZED")],
)
def test_revoked_or_expired_authority_blocks_decision(change: str, code: str) -> None:
    decision, receipt, subject, policy, profile = _inputs()
    if change == "revoked_key":
        profile["revocations"] = [
            {
                "key_id": "fixture-key-005",
                "effective_at": "2026-09-29T09:01:00Z",
            }
        ]
    else:
        profile["role_assignments"][0]["valid_until"] = "2026-09-29T09:30:00Z"
    result = classify_decision(
        decision,
        receipt,
        subject,
        policy,
        seal(profile),
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        gate_id="component-verification",
        as_of=NOW,
    )
    assert result["eligible"] is False
    assert code in result["reason_codes"]


def test_unknown_outcome_is_malformed() -> None:
    decision, receipt = _resigned(outcome="pretend_approve")
    with pytest.raises(InputError):
        _check(decision, receipt)


def test_conditional_approval_requires_exact_discharge() -> None:
    decision, receipt = _resigned(
        outcome="conditional_approve", conditions=["fixture-evidence-005"]
    )
    assert "CONDITION_UNMET" in _check(decision, receipt)["reason_codes"]
    _, _, subject, policy, profile = _inputs()
    result = classify_decision(
        decision,
        receipt,
        subject,
        policy,
        profile,
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        gate_id="component-verification",
        as_of=NOW,
        discharged_conditions={"fixture-evidence-005"},
    )
    assert result["eligible"] is True and result["approves"] is True


def test_conflicting_live_signed_decisions_block_current_use() -> None:
    first = _check()
    second, receipt = _resigned(decision_id="fixture-rejection-005", outcome="reject")
    current = reconcile_decisions([first, _check(second, receipt)])
    assert all(not item["eligible"] for item in current)
    assert all("DECISION_CONFLICT" in item["reason_codes"] for item in current)


@pytest.mark.parametrize(
    "claim",
    [
        {"claimed_actor": "fixture-reviewer-005", "outcome": "approve"},
        {"answer": "approve", "actor": "fixture-reviewer-005", "source": "fabro_interview"},
    ],
)
def test_unverified_claims_cannot_become_human_decisions(claim: dict[str, Any]) -> None:
    _, receipt, subject, policy, profile = _inputs()
    with pytest.raises(InputError):
        classify_decision(
            claim,
            receipt,
            subject,
            policy,
            profile,
            requested_domain="fixture_contract",
            requested_scope=subject["scope"],
            gate_id="component-verification",
            as_of=NOW,
        )


@pytest.mark.parametrize("field", sorted(DECISION_FIELDS))
def test_every_missing_decision_field_is_rejected(field: str) -> None:
    decision = _inputs()[0]
    decision.pop(field)
    with pytest.raises(InputError) as error:
        _check(decision)
    assert error.value.code == "FIELD_UNKNOWN"
    assert error.value.pointer == "/decision"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("subject_digest", "wrong", "HASH_FORMAT"),
        ("policy_digest", "wrong", "HASH_FORMAT"),
        ("issued_at", "2026-09-29", "TIME_FORMAT"),
        ("valid_until", "2026-09-29", "TIME_FORMAT"),
        ("actor_id", "", "FIELD_TYPE"),
        ("rationale", "", "FIELD_TYPE"),
        ("receipt_ref", "wrong", "HASH_FORMAT"),
    ],
)
def test_resigned_decision_one_field_format_matrix(field: str, value: object, code: str) -> None:
    decision = _inputs()[0]
    decision[field] = value
    with pytest.raises(InputError) as error:
        _check(seal(decision))
    assert error.value.code == code


def test_public_replayed_human_receipts_are_order_independent_and_all_ineligible(
    capsys: pytest.CaptureFixture[str],
) -> None:
    import hashlib
    import json
    from tempfile import TemporaryDirectory

    from score_sw_fabric.catalog.export import canonical
    from score_sw_fabric.cli import main

    first = read_json(BASE / "decision.json")
    second = deepcopy(first)
    second["decision_id"] = "another-decision-005"
    second["outcome"] = "reject"
    second = seal(second)
    records = [first, second]
    receipts = [
        read_json(BASE / "decision-receipt.json"),
        fixture_receipt(
            second,
            payload_kind="assurance_decision",
            issued_at=second["issued_at"],
            nonce="fixture-decision-sequence-1",
        ),
    ]
    with TemporaryDirectory(prefix=".assurance-decision-order-", dir=ROOT) as directory:
        scratch = Path(directory)
        request = read_yaml(BASE / "decision-request.yaml")
        for field, values in (("decisions", records), ("receipts", receipts)):
            refs = []
            for index, record in enumerate(values):
                content = canonical(record)
                name = f"{field}-{index}.json"
                (scratch / name).write_bytes(content)
                refs.append(
                    {
                        "path": name,
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "semantic_digest": record[
                            "receipt_digest" if field == "receipts" else "digest"
                        ],
                    }
                )
            request["inputs"][field] = refs
        request["output_root"] = f"{scratch.name}/out"
        path = scratch / "request.json"
        out = scratch / "out/decision-result.json"
        outputs = []
        for reverse in (False, True):
            for field in ("decisions", "receipts"):
                request["inputs"][field] = sorted(
                    request["inputs"][field], key=lambda item: item["path"], reverse=reverse
                )
            path.write_text(json.dumps(request))
            assert (
                main(
                    [
                        "assurance",
                        "decision",
                        "--request",
                        str(path),
                        "--out",
                        str(out),
                        "--json",
                    ]
                )
                == 1
            )
            capsys.readouterr()
            outputs.append(out.read_bytes())
        assert outputs[0] == outputs[1]
        eligibility = read_json(out)["eligibility"]
        assert [item["decision_id"] for item in eligibility] == [
            "another-decision-005",
            "fixture-decision-005",
        ]
        assert all("RECEIPT_REPLAY" in item["reason_codes"] for item in eligibility)
