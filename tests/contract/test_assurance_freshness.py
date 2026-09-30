"""Prior assessments stay immutable while current-use bindings are compared exactly."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.freshness import assess_freshness
from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "tests/fixtures/assurance/passing-scope"


def _inputs() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    return (
        read_json(BASE / "out/assessment.json"),
        read_json(BASE / "out/subject.json"),
        read_json(BASE / "policy.json"),
        read_yaml(ROOT / "profiles/assurance-fixture-v1.yaml"),
        [read_json(BASE / "evidence.json")],
        [read_json(BASE / "decision.json")],
    )


def _check(
    *,
    subject: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    as_of: str = "2026-09-29T10:00:00Z",
) -> dict[str, Any]:
    old, s, p, t, e, d = _inputs()
    return assess_freshness(
        old,
        s if subject is None else subject,
        p if policy is None else policy,
        t if profile is None else profile,
        e if evidence is None else evidence,
        d if decisions is None else decisions,
        as_of=as_of,
    )


def test_same_exact_binding_is_current() -> None:
    assert _check()["state"] == "current"


@pytest.mark.parametrize(
    "path",
    [
        ("artifact_candidate", "digest"),
        ("artifact_report",),
        ("source_baselines", 0, "commit"),
        ("process_baseline",),
        ("toolchain",),
        ("profiles", "artifact"),
        ("expected_obligation_ids",),
    ],
)
def test_subject_binding_mutation_is_stale(path: tuple[Any, ...]) -> None:
    subject = deepcopy(_inputs()[1])
    target = subject
    for part in path[:-1]:
        target = target[part]
    last = path[-1]
    if isinstance(target, dict):
        if last == "artifact_report":
            target[last] = {"digest": "0" * 64}
        elif last == "process_baseline":
            target[last] = {"changed": True}
        elif last == "toolchain":
            target[last] = {"changed": True}
        elif last == "expected_obligation_ids":
            target[last] = ["new-obligation"]
        else:
            target[last] = "0" * 64 if last != "commit" else "a" * 40
    subject = seal(subject)
    result = _check(subject=subject)
    assert result["state"] == "stale"
    assert result["affected_gate_ids"] == ["component-verification"]


def test_policy_trust_evidence_decision_and_time_changes_are_stale() -> None:
    old, s, p, t, e, d = _inputs()
    policy = deepcopy(p)
    policy["status"] = "pending_production_review"
    policy = seal(policy)
    trust = deepcopy(t)
    trust["revocations"] = [{"key_id": "fixture-key-005", "effective_at": "2026-09-29T09:30:00Z"}]
    trust = seal(trust)
    evidence = deepcopy(e)
    evidence[0]["result"] = "fail"
    evidence[0] = seal(evidence[0])
    decisions = deepcopy(d)
    decisions[0]["outcome"] = "reject"
    decisions[0] = seal(decisions[0])
    assert _check(policy=policy)["state"] == "stale"
    assert _check(profile=trust)["state"] == "stale"
    assert _check(evidence=evidence)["state"] == "stale"
    assert _check(decisions=decisions)["state"] == "stale"
    assert _check(as_of="2026-09-30T10:00:00Z")["state"] == "stale"
    assert old == _inputs()[0]


def test_removed_evidence_remains_named_as_affected_and_widens_scope() -> None:
    result = _check(evidence=[])
    assert result["state"] == "stale"
    assert result["affected_evidence_ids"] == ["fixture-evidence-005"]
    assert result["affected_decision_ids"] == ["fixture-decision-005"]
    assert result["unknown_dependencies"] is True
    assert result["scope_expansion"] == "whole_gate"


def test_new_unlinked_decision_widens_scope_without_rewriting_history() -> None:
    before = _inputs()[0]
    decisions = deepcopy(_inputs()[5])
    new = deepcopy(decisions[0])
    new["decision_id"] = "new-unlinked-decision"
    decisions.append(seal(new))
    result = _check(decisions=decisions)
    assert result["state"] == "stale"
    assert result["unknown_dependencies"] is True
    assert result["scope_expansion"] == "whole_gate"
    assert result["affected_decision_ids"] == ["fixture-decision-005", "new-unlinked-decision"]
    assert before == _inputs()[0]


def test_time_change_rechecks_evidence_and_decision_validity() -> None:
    result = _check(as_of="2026-09-30T10:00:00Z")
    assert result["state"] == "stale"
    assert result["affected_evidence_ids"] == ["fixture-evidence-005"]
    assert result["affected_decision_ids"] == ["fixture-decision-005"]
    assert result["scope_expansion"] == "whole_gate"


@pytest.mark.parametrize(
    ("binding", "path", "replacement", "expected_pointer"),
    [
        ("subject", ("plan", "digest"), "0" * 64, "/subject/plan/digest"),
        ("subject", ("artifact_report",), {"digest": "0" * 64}, "/subject/artifact_report"),
        (
            "subject",
            ("artifact_candidate", "bindings", "workflow_package"),
            "0" * 64,
            "/subject/artifact_candidate/bindings/workflow_package",
        ),
        (
            "subject",
            ("artifact_candidate", "bindings", "artifact_profile"),
            "0" * 64,
            "/subject/artifact_candidate/bindings/artifact_profile",
        ),
        (
            "subject",
            ("file_closure", 0, "sha256"),
            "0" * 64,
            "/subject/file_closure/0/sha256",
        ),
        (
            "subject",
            ("toolchain", "commands", 0),
            "changed-native-command",
            "/subject/toolchain/commands/0",
        ),
        (
            "subject",
            ("expected_obligation_ids", 0),
            "changed-obligation",
            "/subject/expected_obligation_ids/0",
        ),
        (
            "subject",
            ("artifact_candidate", "bindings", "snapshot"),
            "0" * 64,
            "/subject/artifact_candidate/bindings/snapshot",
        ),
        (
            "subject",
            ("toolchain", "native_validator", "id"),
            "changed-validator",
            "/subject/toolchain/native_validator/id",
        ),
        ("subject", ("profiles", "artifact"), "0" * 64, "/subject/profiles/artifact"),
        (
            "policy",
            ("freshness_rules", "max_age_seconds"),
            1,
            "/policy/freshness_rules/max_age_seconds",
        ),
        (
            "profile",
            ("issuer_keys", 0, "public_key_base64"),
            "changed-key",
            "/trust_profile/issuer_keys/0/public_key_base64",
        ),
        (
            "profile",
            ("role_assignments", 0, "role"),
            "changed-role",
            "/trust_profile/role_assignments/0/role",
        ),
        (
            "profile",
            ("revocations",),
            [{"key_id": "fixture-key-005", "effective_at": "2026-09-29T09:30:00Z"}],
            "/trust_profile/revocations",
        ),
        (
            "evidence",
            (0, "tool", "executable_digest"),
            "0" * 64,
            "/evidence/0/tool/executable_digest",
        ),
        ("evidence", (0, "result"), "fail", "/evidence/0/result"),
        ("decision", (0, "outcome"), "reject", "/decisions/0/outcome"),
        ("decision", (0, "conditions"), ["new-condition"], "/decisions/0/conditions"),
        ("decision", (0, "valid_until"), "2026-09-30T00:00:00Z", "/decisions/0/valid_until"),
    ],
)
def test_single_binding_mutation_marks_exact_prior_use_stale(
    binding: str, path: tuple[Any, ...], replacement: Any, expected_pointer: str
) -> None:
    prior, subject, policy, profile, evidence, decisions = _inputs()
    before = deepcopy(prior)
    selected = {
        "subject": subject,
        "policy": policy,
        "profile": profile,
        "evidence": evidence,
        "decision": decisions,
    }
    target = selected[binding]
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = replacement
    if binding in {"subject", "policy", "profile"}:
        selected[binding] = seal(selected[binding])
    else:
        selected[binding][0] = seal(selected[binding][0])
    result = _check(
        subject=selected["subject"],
        policy=selected["policy"],
        profile=selected["profile"],
        evidence=selected["evidence"],
        decisions=selected["decision"],
    )
    assert result["state"] == "stale"
    assert expected_pointer in result["changed_bindings"]
    assert result["affected_gate_ids"] == ["component-verification"]
    assert prior == before


def _no_impact_case(
    *, rebind_policy: bool = False
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    from tests.assurance_support import fixture_receipt

    prior, subject, policy, profile, evidence, decisions = _inputs()
    subject["artifact_candidate"]["digest"] = "0" * 64
    subject = seal(subject)
    paths = ["/subject/artifact_candidate/digest", "/subject/digest"]
    if rebind_policy:
        paths = sorted(
            paths
            + ["/policy/digest"]
            + [
                f"/policy/predicates/{index}/subject_ref"
                for index in range(len(policy["predicates"]))
            ]
        )
    policy["freshness_rules"]["no_impact"] = {
        "role": "component_reviewer",
        "authority_ref": "fixture-authority-005",
        "allowed_paths": paths,
    }
    policy = seal(policy)
    prior["policy_refs"][0]["record"] = policy
    prior["policy_refs"][0]["selected_digest"] = policy["digest"]
    prior["gate_results"][0]["policy_digest"] = policy["digest"]
    prior["gate_results"][0] = seal(prior["gate_results"][0])
    prior = seal(prior)
    old_policy_digest = policy["digest"]
    if rebind_policy:
        policy = deepcopy(policy)
        for predicate in policy["predicates"]:
            predicate["subject_ref"] = subject["digest"]
        policy = seal(policy)
    review = deepcopy(decisions[0])
    review.update(
        {
            "decision_id": "fixture-no-impact-005",
            "outcome": "no_impact",
            "subject_digest": subject["digest"],
            "policy_digest": policy["digest"],
            "obligation_ids": sorted(subject["expected_obligation_ids"]),
            "rationale": "Reviewed exact baseline change for fixture scope.",
            "baseline_change": {
                "prior_assessment_digest": prior["digest"],
                "prior_subject_digest": prior["subject"]["manifest"]["digest"],
                "current_subject_digest": subject["digest"],
                "prior_policy_digest": old_policy_digest,
                "current_policy_digest": policy["digest"],
                "changed_bindings": paths,
            },
        }
    )
    review = seal(review)
    receipt = fixture_receipt(
        review,
        payload_kind="assurance_decision",
        issued_at=review["issued_at"],
        nonce="fixture-no-impact-sequence",
    )
    return prior, subject, policy, profile, evidence, decisions, review, receipt


def test_exact_signed_no_impact_review_narrows_scope_but_keeps_gate_stale() -> None:
    prior, subject, policy, profile, evidence, decisions, review, receipt = _no_impact_case()
    old_bytes = deepcopy(prior)
    result = assess_freshness(
        prior,
        subject,
        policy,
        profile,
        evidence,
        decisions + [review],
        as_of="2026-09-29T10:00:00Z",
        decision_receipts=[receipt],
    )
    assert result["state"] == "stale"
    assert result["scope_expansion"] == "reviewed_no_impact"
    assert result["unknown_dependencies"] is False
    assert result["no_impact_decision_digest"] == review["digest"]
    assert result["affected_evidence_ids"] == ["fixture-evidence-005"]
    assert result["affected_decision_ids"] == ["fixture-decision-005"]
    assert prior == old_bytes


def test_no_impact_changed_binding_exact_limit_and_one_over(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    from score_sw_fabric.assurance import decisions as module
    from score_sw_fabric.assurance.decisions import classify_decision

    _, subject, policy, profile, _, _, review, receipt = _no_impact_case()
    monkeypatch.setattr(module, "MAX_FINDINGS", 2)
    assert len(review["baseline_change"]["changed_bindings"]) == 2
    classify_decision(
        review,
        receipt,
        subject,
        policy,
        profile,
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        gate_id="component-verification",
        as_of=datetime(2026, 9, 29, 10, tzinfo=UTC),
        allow_no_impact=True,
    )
    review["baseline_change"]["changed_bindings"] = [
        *review["baseline_change"]["changed_bindings"],
        "/subject/new-binding",
    ]
    with pytest.raises(InputError) as error:
        classify_decision(
            seal(review),
            receipt,
            subject,
            policy,
            profile,
            requested_domain="fixture_contract",
            requested_scope=subject["scope"],
            gate_id="component-verification",
            as_of=datetime(2026, 9, 29, 10, tzinfo=UTC),
            allow_no_impact=True,
        )
    assert error.value.code == "LIMIT_EXCEEDED"
    assert error.value.pointer == "/decision/baseline_change/changed_bindings"


@pytest.mark.parametrize("change", ["old_digest", "scope", "role", "signature", "policy", "time"])
def test_no_impact_review_requires_exact_signed_policy_authority(change: str) -> None:
    prior, subject, policy, profile, evidence, decisions, review, receipt = _no_impact_case()
    if change == "old_digest":
        review["baseline_change"]["prior_subject_digest"] = "f" * 64
        review = seal(review)
    elif change == "scope":
        review["scope"]["id"] = "other-component"
        review = seal(review)
    elif change == "role":
        review["role"] = "unassigned-role"
        review = seal(review)
    elif change == "signature":
        receipt["signature"] = (
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
        )
        from score_sw_fabric.assurance.models import digest

        receipt["receipt_digest"] = digest(receipt, exclude="receipt_digest")
    elif change == "policy":
        policy = deepcopy(policy)
        policy["freshness_rules"].pop("no_impact")
        policy = seal(policy)
    result = assess_freshness(
        prior,
        subject,
        policy,
        profile,
        evidence,
        decisions + [review],
        as_of="2026-09-29T11:00:00Z" if change == "time" else "2026-09-29T10:00:00Z",
        decision_receipts=[receipt],
    )
    assert result["state"] == "stale"
    assert result["scope_expansion"] == "whole_gate"
    assert result["unknown_dependencies"] is True
    assert "no_impact_decision_digest" not in result


def test_mechanical_policy_rebind_stays_stale_with_exact_signed_no_impact_review() -> None:
    from datetime import UTC, datetime

    from score_sw_fabric.assurance.gates import evaluate_gate

    prior, subject, policy, profile, evidence, decisions, review, receipt = _no_impact_case(
        rebind_policy=True
    )
    result = evaluate_gate(
        subject,
        policy,
        profile,
        evidence,
        [item for item in prior["receipts"] if item["payload_kind"] == "assurance_evidence"],
        decisions + [review],
        [
            *[item for item in prior["receipts"] if item["payload_kind"] == "assurance_decision"],
            receipt,
        ],
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        gate_id="component-verification",
        as_of=datetime(2026, 9, 29, 10, tzinfo=UTC),
        raw_root=BASE / "raw",
        mode="reuse_prior",
        prior_assessment=prior,
    )
    assert result["outcome"] == "stale"
    assert result["freshness"]["scope_expansion"] == "reviewed_no_impact"
    assert result["freshness"]["no_impact_decision_digest"] == review["digest"]
    assert result["freshness"]["affected_evidence_ids"] == ["fixture-evidence-005"]


def test_no_impact_decision_is_not_standalone_human_approval() -> None:
    from datetime import UTC, datetime

    from score_sw_fabric.assurance.decisions import classify_decision

    _, subject, policy, profile, _, _, review, receipt = _no_impact_case()
    result = classify_decision(
        review,
        receipt,
        subject,
        policy,
        profile,
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        gate_id="component-verification",
        as_of=datetime(2026, 9, 29, 10, tzinfo=UTC),
    )
    assert not result["eligible"]
    assert not result["approves"]
    assert result["reason_codes"] == ["NO_IMPACT_CONTEXT_REQUIRED"]


def test_no_impact_receipt_cannot_reuse_prior_decision_sequence() -> None:
    from tests.assurance_support import fixture_receipt

    prior, subject, policy, profile, evidence, decisions, review, _ = _no_impact_case()
    replayed = fixture_receipt(
        review,
        payload_kind="assurance_decision",
        issued_at=review["issued_at"],
        nonce="fixture-decision-sequence-1",
    )
    result = assess_freshness(
        prior,
        subject,
        policy,
        profile,
        evidence,
        decisions + [review],
        as_of="2026-09-29T10:00:00Z",
        decision_receipts=[replayed],
    )
    assert result["scope_expansion"] == "whole_gate"
    assert "no_impact_decision_digest" not in result


def test_changed_receipt_identity_stales_current_use_without_editing_history() -> None:
    from score_sw_fabric.assurance.models import digest

    prior, subject, policy, profile, evidence, decisions = _inputs()
    before = deepcopy(prior)
    receipts = deepcopy(prior["receipts"])
    receipts[0]["signature"] = (
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
    )
    receipts[0]["receipt_digest"] = digest(receipts[0], exclude="receipt_digest")
    result = assess_freshness(
        prior,
        subject,
        policy,
        profile,
        evidence,
        decisions,
        as_of="2026-09-29T10:00:00Z",
        current_receipts=receipts,
    )
    assert result["state"] == "stale"
    assert any(path.endswith("/signature") for path in result["changed_bindings"])
    assert result["scope_expansion"] == "whole_gate"
    assert result["unknown_dependencies"] is False
    assert prior == before


def test_removed_receipt_widens_unknown_current_use() -> None:
    prior, subject, policy, profile, evidence, decisions = _inputs()
    result = assess_freshness(
        prior,
        subject,
        policy,
        profile,
        evidence,
        decisions,
        as_of="2026-09-29T10:00:00Z",
        current_receipts=prior["receipts"][1:],
    )
    assert result["state"] == "stale"
    assert "/receipts" in result["changed_bindings"]
    assert result["scope_expansion"] == "whole_gate"
    assert result["unknown_dependencies"] is True


def test_004_native_dependency_paths_survive_whole_gate_staleness() -> None:
    from score_sw_fabric.artifacts.impact import analyze_impact

    folder = ROOT / "tests/fixtures/assurance/no-impact-scope"
    prior = read_json(folder / "out/old-assessment.json")
    subject = read_json(BASE / "out/subject.json")
    policy = read_json(folder / "current-policy.json")
    profile = read_yaml(ROOT / "profiles/assurance-fixture-v1.yaml")
    evidence = [read_json(folder / "old-evidence.json")]
    decisions = [read_json(folder / "old-decision.json"), read_json(folder / "review.json")]
    receipts = [
        read_json(folder / "old-evidence-receipt.json"),
        read_json(folder / "old-decision-receipt.json"),
        read_json(folder / "review-receipt.json"),
    ]
    before_candidate = read_json(ROOT / "tests/fixtures/artifacts/out/before-candidate.json")
    after_candidate = read_json(ROOT / "tests/fixtures/artifacts/out/component-candidate.json")
    native = analyze_impact(before_candidate["index"], after_candidate["index"], {})
    result = assess_freshness(
        prior,
        subject,
        policy,
        profile,
        evidence,
        decisions,
        as_of="2026-09-29T11:00:00Z",
        decision_receipts=receipts[1:],
        current_receipts=receipts,
        artifact_impact=native,
    )
    assert result["state"] == "stale"
    assert result["impact_paths"][0] == "/"
    assert any("COMP_REQ_001@1" in path for path in result["impact_paths"])
    assert any("INTERFACE_001@1" in path for path in result["impact_paths"])
    assert any("TEST_CASE_001@1" in path for path in result["impact_paths"])
    assert result["unknown_dependencies"] is False
    from score_sw_fabric.compiler.reader import semantic_digest

    native["newly_unlinked"] = ["new-unlinked-interface"]
    native["blockers"] = ["new-unlinked-interface"]
    native["state"] = "blocked"
    native["valid"] = False
    native["digest"] = semantic_digest(native)
    widened = assess_freshness(
        prior,
        subject,
        policy,
        profile,
        evidence,
        decisions,
        as_of="2026-09-29T11:00:00Z",
        decision_receipts=receipts[1:],
        current_receipts=receipts,
        artifact_impact=native,
    )
    assert widened["scope_expansion"] == "whole_gate"
    assert widened["unknown_dependencies"] is True
