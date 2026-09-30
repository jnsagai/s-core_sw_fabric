"""008 review packet and separate design/closure gates (AC008-12–15)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.safety.gates import evaluate, gate
from score_sw_fabric.safety.packet import packet
from score_sw_fabric.safety.profile import load_profile
from tests.agent_support import ROOT, ref, write_json, write_yaml
from tests.safety_support import FIXTURES, PROFILE, copy_version, replace, report

PROFILE_RECORD = load_profile(PROFILE.read_bytes())
ASSESSMENT = ROOT / "tests/fixtures/assurance/passing-scope/out/assessment.json"
CONTEXT = ROOT / "tests/fixtures/assurance/fixture-trust/context.json"
DFA_NAMES = [
    ("requirements.rst", "requirements"),
    ("architecture.rst", "architecture"),
    ("dfa.rst", "analysis"),
    ("platform_dfa.rst", "allocation"),
]


def build_packet(
    tmp: Path, record: dict[str, Any], evidence: list[Any] | None = None
) -> tuple[int, dict[str, Any]]:
    report_ref = write_json(tmp / "control/report.json", record)
    request = tmp / "control/packet.yaml"
    write_yaml(
        request,
        {
            "schema_version": 1,
            "kind": "safety_packet_request",
            "profile": ref(PROFILE),
            "report": report_ref,
            "evidence": evidence or [],
            "protected_roots": [str(ROOT)],
        },
    )
    status, value, _, _ = packet(request)
    return status, value


def test_packet_states_scope_and_pending_evidence(tmp_path: Path) -> None:
    record = report(tmp_path, FIXTURES / "v2", baseline=FIXTURES / "v1", iteration=2)
    evidence = [
        {
            "id": "ev.unit",
            "kind": "unit_test",
            "ref": "tests/test_timeout.cpp",
            "origin": "agent_assertion",
            "requirement": "comp_req__telemetry_guard__stale_detection",
        }
    ]
    status, value = build_packet(tmp_path, record, evidence)
    assert status == 0 and value["packet_state"] == "review_requestable"
    changed = {entry["item"]: entry["fields"] for entry in value["native_diff"]["changed"]}
    late = changed["comp_saf_fmea__telemetry_guard__late_sample"]
    assert late["mitigation_state"] == {"from": "missing", "to": "linked_pending_review"}
    assert "comp_arc_dyn__telemetry_guard__timeout_check" in value["affected"]["architecture"]
    assert "comp_req__telemetry_guard__stale_detection" in value["affected"]["requirements"]
    assert all(item["answer"] == "pending_human" for item in value["checklist"])
    assert len(value["checklist"]) == 6
    design = value["approval_scopes"]["design_acceptance"]
    closure = value["approval_scopes"]["closure"]
    assert design["requestable"] is True and "final safety closure" in design["does_not_authorize"]
    assert {item["role"] for item in design["subject_files"]} == {
        "requirements",
        "architecture",
        "analysis",
    }
    assert closure["requestable"] is False
    assert set(closure["pending"]) == {
        "comp_req__telemetry_guard__report_missing",
        "comp_req__telemetry_guard__stale_detection",
        "aou_req__telemetry_guard__consumer_check",
    }
    states = {item["requirement"]: item["state"] for item in value["missing_evidence"]}
    assert states["comp_req__telemetry_guard__stale_detection"] == "supplied_unverified"
    assert value["verification_evidence"][0]["verification"] == "not_verified"
    assert value["engineering_readiness"] == "not_evaluated"


def test_blocked_report_packet_is_not_requestable(tmp_path: Path) -> None:
    status, value = build_packet(tmp_path, report(tmp_path, FIXTURES / "v1"))
    assert status == 1 and value["packet_state"] == "blocked_prerequisites"
    assert value["approval_scopes"]["design_acceptance"]["pending"] == ["MITIGATION_UNRESOLVED"]


def test_demo03_packet_shows_dependency_concern(tmp_path: Path) -> None:
    record = report(
        tmp_path,
        FIXTURES / "dfa",
        analysis="dfa",
        names=DFA_NAMES,
        allocation="doc__platform_dfa_fixture",
    )
    _, value = build_packet(tmp_path, record)
    concern = value["dependency_concerns"][0]
    assert concern["failure_id"] == "SI_01_02" and concern["disposition"] == "pending_review"
    assert concern["violates"] == ["comp_arc_sta__telemetry_guard__monitor"]
    assert value["packet_state"] == "blocked_prerequisites"


def summary(gate_id: str, **changes: Any) -> dict[str, Any]:
    value = {
        "assessment_digest": "0" * 64,
        "gate_id": gate_id,
        "assurance_domain": "fixture_contract",
        "outcome": "pass",
        "reproduced": True,
        "binding": "exact",
        "design_basis_binding": "exact",
    }
    value.update(changes)
    return value


@pytest.fixture
def ready_packet(tmp_path: Path) -> dict[str, Any]:
    record = report(tmp_path, FIXTURES / "v2", baseline=FIXTURES / "v1", iteration=2)
    return build_packet(tmp_path, record)[1]


def test_no_decision_awaits_and_closure_blocks(ready_packet: dict[str, Any]) -> None:
    result = evaluate(PROFILE_RECORD, ready_packet, [])
    assert result["design_acceptance"]["state"] == "awaiting_decision"
    assert result["closure"]["state"] == "blocked"
    assert set(result["closure"]["reasons"]) == {
        "DESIGN_NOT_ACCEPTED",
        "ITEMS_NOT_CLAIMED_SUFFICIENT",
        "MITIGATION_EVIDENCE_MISSING",
    }


def test_design_accepted_keeps_closure_blocked_on_evidence(ready_packet: dict[str, Any]) -> None:
    result = evaluate(PROFILE_RECORD, ready_packet, [summary("safety_design_acceptance")])
    assert result["design_acceptance"]["state"] == "accepted"
    assert result["design_acceptance"]["domain"] == "fixture_contract"
    closure = result["closure"]
    assert closure["state"] == "blocked" and "MITIGATION_EVIDENCE_MISSING" in closure["reasons"]
    assert "DESIGN_NOT_ACCEPTED" not in closure["reasons"]
    assert "comp_req__telemetry_guard__stale_detection" in closure["missing_evidence"]


@pytest.mark.parametrize(
    ("decision", "state", "note"),
    [
        (
            summary(
                "safety_design_acceptance",
                binding="other_subject",
                design_basis_binding="other_subject",
            ),
            "stale",
            None,
        ),
        (
            summary("safety_design_acceptance", reproduced=False),
            "awaiting_decision",
            "DECISION_NOT_REPRODUCED",
        ),
        (
            summary("safety_design_acceptance", assurance_domain="production"),
            "awaiting_decision",
            "PRODUCTION_AUTHORITY_UNAVAILABLE",
        ),
        (
            summary("safety_design_acceptance", outcome="blocked"),
            "awaiting_decision",
            "DECISION_NOT_PASS",
        ),
        (summary("component-verification"), "awaiting_decision", None),
    ],
)
def test_ineligible_decisions_do_not_accept(
    ready_packet: dict[str, Any], decision: dict[str, Any], state: str, note: str | None
) -> None:
    result = evaluate(PROFILE_RECORD, ready_packet, [decision])
    assert result["design_acceptance"]["state"] == state
    if note:
        assert note in result["decision_notes"]


def test_blocked_prerequisites_block_design_even_with_decision(tmp_path: Path) -> None:
    _, blocked = build_packet(tmp_path, report(tmp_path, FIXTURES / "v1"))
    result = evaluate(PROFILE_RECORD, blocked, [summary("safety_design_acceptance")])
    assert result["design_acceptance"]["state"] == "blocked"
    assert "MITIGATION_UNRESOLVED" in result["design_acceptance"]["reasons"]


def test_closure_accepts_only_with_design_basis_sufficiency_and_closure_decision(
    tmp_path: Path,
) -> None:
    current = copy_version(tmp_path, "v2")
    for old in (
        "report_missing\n   :sufficient: no\n   :status: invalid",
        "consumer_check\n   :sufficient: no\n   :status: invalid",
        "issues/12\n   :sufficient: no\n   :status: invalid",
    ):
        replace(
            current / "fmea.rst",
            old,
            old.replace("sufficient: no", "sufficient: yes").replace(
                "status: invalid", "status: valid"
            ),
        )
    record = report(tmp_path, current, baseline=FIXTURES / "v2", iteration=2)
    _, promoted = build_packet(tmp_path, record)
    decisions = [
        summary("safety_design_acceptance", binding="other_subject"),
        summary("safety_closure"),
    ]
    result = evaluate(PROFILE_RECORD, promoted, decisions)
    assert result["closure"]["state"] == "accepted"
    assert result["design_acceptance"]["state"] == "stale"
    without_closure = evaluate(PROFILE_RECORD, promoted, decisions[:1])
    assert without_closure["closure"]["reasons"] == ["MITIGATION_EVIDENCE_MISSING"]


def _gate_request(tmp: Path, packet_value: dict[str, Any], decisions: list[dict[str, Any]]) -> Path:
    request = tmp / "control/gate.yaml"
    write_yaml(
        request,
        {
            "schema_version": 1,
            "kind": "safety_gate_request",
            "profile": ref(PROFILE),
            "packet": write_json(tmp / "control/packet.json", packet_value),
            "decisions": decisions,
            "protected_roots": [str(ROOT)],
        },
    )
    return request


def test_real_005_assessment_replays_but_does_not_bind_other_subject(
    tmp_path: Path, ready_packet: dict[str, Any]
) -> None:
    status, value, _, _ = gate(
        _gate_request(
            tmp_path, ready_packet, [{"assessment": ref(ASSESSMENT), "trust_context": ref(CONTEXT)}]
        )
    )
    assert status == 1
    decision = value["decisions"][0]
    assert decision["reproduced"] is True and decision["outcome"] == "pass"
    assert (
        decision["gate_id"] == "component-verification" and decision["binding"] == "other_subject"
    )
    assert value["design_acceptance"]["state"] == "awaiting_decision"
    assert value["closure"]["state"] == "blocked"


def test_tampered_assessment_is_refused(tmp_path: Path, ready_packet: dict[str, Any]) -> None:
    assessment = json.loads(ASSESSMENT.read_text())
    assessment["gate_results"][0]["gate_id"] = "safety_design_acceptance"
    tampered = write_json(tmp_path / "control/tampered.json", assessment)
    with pytest.raises(InputError):
        gate(
            _gate_request(
                tmp_path, ready_packet, [{"assessment": tampered, "trust_context": ref(CONTEXT)}]
            )
        )


def test_resealed_forgery_does_not_reproduce(tmp_path: Path, ready_packet: dict[str, Any]) -> None:
    assessment = json.loads(ASSESSMENT.read_text())
    result = dict(assessment["gate_results"][0])
    result["gate_id"] = "safety_design_acceptance"
    assessment["gate_results"] = [
        seal({key: value for key, value in result.items() if key != "digest"})
    ]
    forged = write_json(
        tmp_path / "control/forged.json",
        seal({key: value for key, value in assessment.items() if key != "digest"}),
    )
    request = _gate_request(
        tmp_path, ready_packet, [{"assessment": forged, "trust_context": ref(CONTEXT)}]
    )
    with pytest.raises(InputError) as error:
        gate(request)
    assert error.value.code == "SUBJECT_MISMATCH"
