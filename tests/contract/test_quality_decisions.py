"""Only exact independently replayed fixture decisions may dispose a fixture finding."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import decisions
from tests.quality_decision_support import (
    CONTEXT,
    controls,
    fixture_assessment,
    replace_policy,
    subject_request,
    with_assessment,
)
from tests.quality_disposition_support import change_request, write
from tests.quality_support import ref


@pytest.fixture
def selected(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    path = controls(tmp_path)
    _, binding, _, _ = decisions.subject(subject_request(path))
    return path, binding


@pytest.mark.parametrize("kind", ["false_positive", "deviation", "recategorization", "suppression"])
def test_exact_fixture_decision_replays_and_remains_fixture(tmp_path: Path, kind: str) -> None:
    path = controls(tmp_path, kind)
    _, binding, _, _ = decisions.subject(subject_request(path))
    with_assessment(path, fixture_assessment(tmp_path, binding))
    code, result, _, _ = decisions.assess(path)
    assert code == 0 and result["state"] == "accepted_fixture"
    assert result["decisions"][0]["replay"]["reproduced"] is True
    assert result["accepted_decision_digests"]
    assert result["engineering_readiness"] == "not_evaluated"
    assert result["assurance_eligibility"] == "not_eligible"


def test_names_without_decisions_leave_pending(selected: tuple[Path, dict[str, Any]]) -> None:
    path, _ = selected
    _, result, _, _ = decisions.assess(path)
    assert result["state"] == "pending_review" and not result["accepted_decision_digests"]


@pytest.mark.parametrize("permission", ["unknown", "prohibited"])
def test_unknown_or_prohibited_category_never_accepts(
    selected: tuple[Path, dict[str, Any]], permission: str
) -> None:
    path, binding = selected
    with_assessment(path, fixture_assessment(path.parent, binding))
    rows = copy.deepcopy(binding["policy"]["rules"])
    rows[0]["permission"] = permission
    replace_policy(path, rules=rows)
    code, result, _, _ = decisions.assess(path)
    assert code == 1 and result["state"] == "blocked"
    assert (
        "DEVIATION_POLICY_" + ("UNKNOWN" if permission == "unknown" else "PROHIBITED")
        in result["reasons"]
    )


def test_missing_policy_never_accepts(selected: tuple[Path, dict[str, Any]]) -> None:
    path, binding = selected
    with_assessment(path, fixture_assessment(path.parent, binding))
    change_request(path, policy=None)
    _, result, _, _ = decisions.assess(path)
    assert result["state"] == "blocked" and "DEVIATION_POLICY_UNKNOWN" in result["reasons"]


@pytest.mark.parametrize(
    "mutation", ["rationale", "native_id", "tool", "configuration", "suite", "source"]
)
def test_independently_passing_other_closure_never_accepts(
    selected: tuple[Path, dict[str, Any]], mutation: str
) -> None:
    path, binding = selected
    other = copy.deepcopy(binding)
    if mutation == "rationale":
        other["review"]["draft"]["rationale"] = "another proposal"
    elif mutation == "native_id":
        other["review"]["subject"]["finding"]["native_id"] = "fixture/another-check"
    elif mutation == "tool":
        other["current_context"]["toolchain"]["tool"]["sha256"] = "0" * 64
    elif mutation == "configuration":
        other["current_context"]["configuration_sha256"] = "0" * 64
    elif mutation == "suite":
        other["review"]["subject"]["finding"]["rule_component"] = {"suite": "fixture-other"}
    else:
        other["current_baseline"]["files"][0]["sha256"] = "0" * 64
    with_assessment(path, fixture_assessment(path.parent, seal(other)))
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture"
    assert "DECISION_SUBJECT_MISMATCH" in result["reasons"]


def test_old_passing_decision_is_reclassified_at_current_time(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    path, binding = selected
    with_assessment(path, fixture_assessment(path.parent, binding))
    change_request(path, as_of="2026-12-03T10:00:00Z")
    _, result, _, _ = decisions.assess(path)
    assert result["state"] == "stale" and "DECISION_EXPIRED" in result["reasons"]


@pytest.mark.parametrize(
    "changes",
    [
        {"actor_id": "fixture-author-005"},
        {"role": "release_owner"},
        {"authority_ref": "agent"},
        {"conditions": ["agent-claims-complete"], "outcome": "conditional_approve"},
        {"outcome": "reject"},
        {"outcome": "request_changes"},
    ],
)
def test_signed_ineligible_or_negative_judgments_never_accept(
    selected: tuple[Path, dict[str, Any]], changes: dict[str, Any]
) -> None:
    path, binding = selected
    with_assessment(path, fixture_assessment(path.parent, binding, decision_changes=changes))
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture" and not result["accepted_decision_digests"]


def test_passing_gate_without_human_decision_is_insufficient(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    path, binding = selected
    assessment = fixture_assessment(path.parent, binding, human=False)
    assert assessment["gate_results"][0]["outcome"] == "pass"
    with_assessment(path, assessment)
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture"


def test_signed_withdrawal_cannot_be_ignored(selected: tuple[Path, dict[str, Any]]) -> None:
    path, binding = selected
    assessment = fixture_assessment(
        path.parent,
        binding,
        extra_decisions=[
            {
                "decision_id": "fixture-withdrawal",
                "outcome": "withdraw",
                "supersedes": "fixture-decision-005",
            }
        ],
    )
    with_assessment(path, assessment)
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture" and not result["accepted_decision_digests"]


@pytest.mark.parametrize("missing", ["binding", "source", "policy"])
def test_incomplete_005_file_closure_blocks(
    selected: tuple[Path, dict[str, Any]], missing: str
) -> None:
    path, binding = selected
    paths = {
        "binding": binding["policy"]["binding_path"],
        "source": binding["policy"]["source_prefix"] + "/check.cpp",
        "policy": binding["policy"]["source_path"],
    }
    with_assessment(path, fixture_assessment(path.parent, binding, missing_files={paths[missing]}))
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture"


def test_broader_suppression_scope_blocks(selected: tuple[Path, dict[str, Any]]) -> None:
    path, binding = selected
    rows = copy.deepcopy(binding["policy"]["rules"])
    rows[0]["scope"]["files"].append("other.cpp")
    replace_policy(path, rules=rows)
    _, result, _, _ = decisions.assess(path)
    assert result["state"] == "blocked" and "DEVIATION_SCOPE_MISMATCH" in result["reasons"]


def test_production_cannot_promote_fixture_decision(selected: tuple[Path, dict[str, Any]]) -> None:
    path, binding = selected
    with_assessment(path, fixture_assessment(path.parent, binding))
    change_request(path, assurance_domain="production")
    _, result, _, _ = decisions.assess(path)
    assert result["state"] == "blocked" and "PRODUCTION_AUTHORITY_UNAVAILABLE" in result["reasons"]


def test_changed_current_source_stales_review(selected: tuple[Path, dict[str, Any]]) -> None:
    path, binding = selected
    with_assessment(path, fixture_assessment(path.parent, binding))
    r = json.loads(path.read_text())
    dr_path = Path(r["disposition_request"]["path"])
    dr = json.loads(dr_path.read_text())
    run_path = Path(dr["current"]["request"]["path"])
    run = json.loads(run_path.read_text())
    source = path.parent / "component/check.cpp"
    source.write_bytes(source.read_bytes() + b"\n// drift\n")
    run["files"] = [dict(ref(source), path="check.cpp")]
    write(run_path, run)
    dr["current"]["request"] = ref(run_path)
    write(dr_path, dr)
    change_request(path, disposition_request=ref(dr_path))
    _, result, _, _ = decisions.assess(path)
    assert result["state"] == "stale"


def test_correction_execution_request_is_refused_before_running(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    path, _ = selected
    r = json.loads(path.read_text())
    d = Path(r["disposition_request"]["path"])
    change_request(d, action="check_correction")
    change_request(path, disposition_request=ref(d))
    with pytest.raises(InputError):
        decisions.assess(path)


def test_invalid_input_preserves_previous_output(selected: tuple[Path, dict[str, Any]]) -> None:
    path, _ = selected
    change_request(path, schema_version=True)
    output = path.parent / "result.json"
    output.write_text("previous")
    assert main(["quality", "decision", "--request", str(path), "--out", str(output)]) == 2
    assert output.read_text() == "previous"


def test_current_gate_rechecks_shorter_evidence_lifetime(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    path, binding = selected
    assessment = fixture_assessment(path.parent, binding, evidence_max_age=3600)
    assert assessment["gate_results"][0]["outcome"] == "pass"
    with_assessment(path, assessment)
    change_request(path, as_of="2026-12-01T11:00:00Z")
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture"
    assert result["decisions"][0]["replay"]["outcome"] == "pass"
    assert result["decisions"][0]["current_gate"]["outcome"] != "pass"
    assert "CURRENT_GATE_NOT_PASSED" in result["reasons"]


@pytest.mark.parametrize("mutation", ["revoked", "key_expired", "role_expired"])
def test_current_trust_validity_is_separate_from_historical_pass(
    selected: tuple[Path, dict[str, Any]],
    mutation: str,
) -> None:
    path, binding = selected
    context = json.loads(CONTEXT.read_text())
    profile = context["profile"]
    if mutation == "revoked":
        profile["revocations"].append(
            {
                "key_id": "fixture-key-005",
                "effective_at": "2026-12-01T10:30:00Z",
            }
        )
    else:
        rows = profile["issuer_keys" if mutation == "key_expired" else "role_assignments"]
        rows[0]["valid_until"] = "2026-12-01T10:30:00Z"
    context["profile"] = seal(profile)
    context["profile_digest"] = context["profile"]["digest"]
    assessment = fixture_assessment(path.parent, binding, context=context)
    assert assessment["gate_results"][0]["outcome"] == "pass"
    with_assessment(path, assessment)
    r = json.loads(path.read_text())
    r["decisions"][0]["trust_context"] = write(path.parent / "context.json", context)
    r["as_of"] = "2026-12-01T11:00:00Z"
    write(path, r)
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture"
    assert result["decisions"][0]["replay"]["outcome"] == "pass"
    assert any(r in result["reasons"] for r in ("ISSUER_UNTRUSTED", "ROLE_UNAUTHORIZED"))


def test_dedicated_gate_is_required(selected: tuple[Path, dict[str, Any]]) -> None:
    path, binding = selected
    with_assessment(path, fixture_assessment(path.parent, binding, gate_id="another-gate"))
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture" and "DECISION_SCOPE_MISMATCH" in result["reasons"]


@pytest.mark.parametrize("changed_id", [False, True])
def test_cross_assessment_conflicts_or_replayed_sequences_block(
    selected: tuple[Path, dict[str, Any]],
    changed_id: bool,
) -> None:
    from score_sw_fabric.assurance.models import digest
    from tests.assurance_support import fixture_receipt

    path, binding = selected
    first = fixture_assessment(path.parent, binding)
    second = fixture_assessment(
        path.parent,
        binding,
        decision_changes={
            "decision_id": "another-judgment" if changed_id else "fixture-decision-005",
            "rationale": "another signed judgment",
        },
    )
    if changed_id:
        second["receipts"][0] = fixture_receipt(
            second["decision_records"][0],
            payload_kind="assurance_decision",
            issued_at=second["decision_records"][0]["issued_at"],
            nonce=first["receipts"][0]["nonce_or_sequence"],
        )
        second = seal(second)
        assert second["receipts"][0]["payload_digest"] == digest(
            second["decision_records"][0], exclude="__none__"
        )
    r = json.loads(path.read_text())
    r["decisions"] = [
        {
            "assessment": write(path.parent / (str(i) + ".json"), value),
            "trust_context": ref(CONTEXT),
        }
        for i, value in enumerate([first, second])
    ]
    write(path, r)
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture"
    assert ("RECEIPT_REPLAY" if changed_id else "DECISION_CONFLICT") in result["reasons"]


def test_binding_preparation_is_deterministic_and_runs_no_tool(
    selected: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from score_sw_fabric.quality import dispositions

    def refuse(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Decision preparation executed an analyzer")

    path, binding = selected
    monkeypatch.setattr(dispositions, "execute_current", refuse)
    assert decisions.subject(subject_request(path))[1] == binding
    assert decisions.assess(path)[1]["binding"] == binding


@pytest.mark.parametrize("target", ["review", "policy", "source"])
def test_publication_cannot_overwrite_input_closure(
    selected: tuple[Path, dict[str, Any]],
    target: str,
) -> None:
    path, _ = selected
    r = json.loads(path.read_text())
    out = path.parent / "component/check.cpp" if target == "source" else Path(r[target]["path"])
    old = out.read_bytes()
    assert main(["quality", "decision", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_bytes() == old


def test_null_native_category_cannot_be_declared_allowed(tmp_path: Path) -> None:
    from score_sw_fabric.quality import dispositions
    from tests.quality_disposition_support import change_draft

    path = controls(tmp_path)
    r = json.loads(path.read_text())
    selected = Path(r["disposition_request"]["path"])
    change_draft(selected, native_category=None)
    _, review, _, _ = dispositions.review(selected)
    r["disposition_request"] = ref(selected)
    r["review"] = write(tmp_path / "review.json", review)
    write(path, r)
    p = json.loads(Path(r["policy"]["path"]).read_text())
    p["rules"][0]["category"] = None
    replace_policy(path, rules=p["rules"])
    _, result, _, _ = decisions.assess(path)
    assert "DEVIATION_POLICY_UNKNOWN" in result["reasons"]


@pytest.mark.parametrize("which", ["pairs", "signed", "history"])
def test_aggregate_decision_limits_refuse(
    selected: tuple[Path, dict[str, Any]],
    which: str,
) -> None:
    path, binding = selected
    assessment = fixture_assessment(path.parent, binding)
    if which == "signed":
        assessment["decision_records"] *= 21
    if which == "history":
        assessment["history_refs"] = [
            {
                "decision_records": assessment["decision_records"] * 20,
                "history_refs": [],
            }
        ]
    with_assessment(path, assessment)
    if which == "pairs":
        r = json.loads(path.read_text())
        r["decisions"] *= 21
        write(path, r)
    with pytest.raises(InputError, match=".*"):
        decisions.assess(path)


def test_yaml_disposition_request_is_hash_verified(selected: tuple[Path, dict[str, Any]]) -> None:
    import yaml

    path, binding = selected
    r = json.loads(path.read_text())
    d = Path(r["disposition_request"]["path"])
    d.write_text(yaml.safe_dump(json.loads(d.read_text())))
    r["disposition_request"] = ref(d)
    write(path, r)
    assert decisions.assess(path)[1]["binding"] == binding


def test_historical_gate_time_cannot_be_reversed(selected: tuple[Path, dict[str, Any]]) -> None:
    path, binding = selected
    with_assessment(path, fixture_assessment(path.parent, binding))
    change_request(path, as_of="2026-12-01T09:30:00Z")
    _, result, _, _ = decisions.assess(path)
    assert result["state"] == "stale" and "DECISION_TIME_REVERSED" in result["reasons"]


def test_linked_review_ancestor_is_validated_and_protected(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    from score_sw_fabric.quality import dispositions

    path, _ = selected
    r = json.loads(path.read_text())
    previous = json.loads(Path(r["review"]["path"]).read_text())
    ancestor = path.parent / "ancestor.json"
    ancestor_ref = write(ancestor, previous)
    d = Path(r["disposition_request"]["path"])
    change_request(d, previous=ancestor_ref)
    _, reviewed, _, _ = dispositions.review(d)
    assert reviewed["revision"] == 2
    r["review"] = write(path.parent / "review.json", reviewed)
    r["disposition_request"] = ref(d)
    write(path, r)
    old = ancestor.read_bytes()
    assert main(["quality", "decision", "--request", str(path), "--out", str(ancestor)]) == 2
    assert ancestor.read_bytes() == old
    assert decisions.assess(path)[1]["binding"]["review"]["revision"] == 2


def test_each_context_keeps_its_current_validity_reasons(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    path, binding = selected
    context = json.loads(CONTEXT.read_text())
    context["profile"]["issuer_keys"][0]["valid_until"] = "2026-12-01T10:30:00Z"
    context["profile"] = seal(context["profile"])
    context["profile_digest"] = context["profile"]["digest"]
    first = fixture_assessment(path.parent, binding)
    second = fixture_assessment(path.parent, binding, context=context)
    r = json.loads(path.read_text())
    r["as_of"] = "2026-12-01T11:00:00Z"
    r["decisions"] = [
        {"assessment": write(path.parent / "first.json", first), "trust_context": ref(CONTEXT)},
        {
            "assessment": write(path.parent / "second.json", second),
            "trust_context": write(path.parent / "context.json", context),
        },
    ]
    write(path, r)
    _, result, _, _ = decisions.assess(path)
    assert result["state"] != "accepted_fixture"
    row = result["decisions"][1]["current"][0]
    assert row["eligible"] is False and "ISSUER_UNTRUSTED" in row["reason_codes"]


def test_context_drift_during_replay_preserves_previous_output(
    selected: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, binding = selected
    with_assessment(path, fixture_assessment(path.parent, binding))
    context_path = path.parent / "context.json"
    r = json.loads(path.read_text())
    r["decisions"][0]["trust_context"] = write(context_path, json.loads(CONTEXT.read_text()))
    write(path, r)
    verify = decisions.verify_assessment

    def drift(assessment: Any, context: Any) -> Any:
        result = verify(assessment, context)
        context_path.write_text("{}")
        return result

    monkeypatch.setattr(decisions, "verify_assessment", drift)
    output = path.parent / "result.json"
    output.write_text("previous")
    assert main(["quality", "decision", "--request", str(path), "--out", str(output)]) == 2
    assert output.read_text() == "previous"
