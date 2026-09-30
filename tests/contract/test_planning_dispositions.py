"""Disposition tests preserve evidence and authority boundaries."""

from __future__ import annotations

import pytest

from score_sw_fabric.planning.closure import build_plan
from score_sw_fabric.planning.reader import load_planning_inputs
from score_sw_fabric.process_source.reader import InputError
from tests.planning_support import prepare_case


def identity() -> dict[str, str]:
    return {
        "target_namespace": "fixture-target",
        "native_source_id": "process",
        "native_work_product_id": "wp__plan",
        "scope_kind": "component",
        "scope_id": "component",
        "purpose": "primary",
    }


def test_partial_inventory_never_proves_absence(tmp_path) -> None:
    inventory = {"schema_version": 1, "completeness": "partial", "artifacts": []}
    intake, _ = prepare_case(tmp_path / "case", inventory=inventory)
    result = build_plan(load_planning_inputs(intake))
    assert "INVENTORY_INCOMPLETE" in {item["code"] for item in result["findings"]}
    assert all(item["effective_disposition"] == "unresolved" for item in result["instances"])


def test_reuse_keeps_exact_proposal_but_cannot_claim_authority(tmp_path) -> None:
    artifact = {
        "identity": identity(),
        "requested_disposition": "reuse",
        "artifact_bindings": [{"revision": "abc", "content_digest": "2" * 64}],
        "decision_refs": [],
        "accepted_revision": "abc",
        "applicability_rationale": "Exact component remains applicable.",
        "dependencies_current": True,
        "classification_approval_ref": "classification-1",
        "accepted_change_request_ref": "change-request-1",
    }
    inventory = {"schema_version": 1, "completeness": "complete", "artifacts": [artifact]}
    intake, _ = prepare_case(tmp_path / "case", inventory=inventory)
    result = build_plan(load_planning_inputs(intake))
    instance = next(item for item in result["instances"] if item["identity"] == identity())
    assert instance["requested_disposition"] == "reuse"
    assert instance["effective_disposition"] == "unresolved"
    assert "AUTHORITY_UNVERIFIED" in instance["finding_codes"]


def test_tailoring_reports_permission_impact_and_authority_separately(tmp_path) -> None:
    artifact = {
        "identity": identity(),
        "requested_disposition": "tailored_out",
        "artifact_bindings": [],
        "decision_refs": [],
        "impact_analysis_state": "stale",
    }
    inventory = {"schema_version": 1, "completeness": "complete", "artifacts": [artifact]}
    intake, _ = prepare_case(tmp_path / "case", inventory=inventory)
    result = build_plan(load_planning_inputs(intake))
    instance = next(item for item in result["instances"] if item["identity"] == identity())
    assert {
        "TAILORING_PERMISSION_MISSING",
        "TAILORING_IMPACT_MISSING",
        "TAILORING_IMPACT_STALE",
        "AUTHORITY_UNVERIFIED",
    } <= set(instance["finding_codes"])


def test_external_obligation_requires_named_boundary_evidence(tmp_path) -> None:
    artifact = {
        "identity": identity(),
        "requested_disposition": "external_obligation",
        "artifact_bindings": [],
        "decision_refs": [],
        "owner": "supplier",
        "interface": "supplier-interface",
        "evidence_owed": "signed report",
        "boundary": "release-gate",
    }
    inventory = {"schema_version": 1, "completeness": "complete", "artifacts": [artifact]}
    intake, _ = prepare_case(tmp_path / "case", inventory=inventory)
    result = build_plan(load_planning_inputs(intake))
    instance = next(item for item in result["instances"] if item["identity"] == identity())
    assert instance["effective_disposition"] == "external_obligation"


@pytest.mark.parametrize("forged", [{"trusted": True}, {"approved": True}])
def test_local_decision_trust_flags_are_invalid_input(tmp_path, forged) -> None:
    decision = {"id": "forged", **forged}
    decisions = {"schema_version": 1, "references": [decision]}
    intake, _ = prepare_case(tmp_path / "case", decisions=decisions)
    with pytest.raises(InputError) as raised:
        build_plan(load_planning_inputs(intake))
    assert raised.value.code == "DECISION_REFERENCE"
