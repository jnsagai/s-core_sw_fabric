"""Supported reuse routes and deterministic bounded-closure behavior."""

from __future__ import annotations

import pytest

from score_sw_fabric.planning.closure import build_plan
from score_sw_fabric.planning.export import seal_plan
from score_sw_fabric.planning.reader import load_planning_inputs
from tests.planning_support import default_scopes, native_rule, prepare_case


def _identity() -> dict[str, str]:
    return {
        "target_namespace": "fixture-target",
        "native_source_id": "process",
        "native_work_product_id": "wp__plan",
        "scope_kind": "component",
        "scope_id": "component",
        "purpose": "primary",
    }


@pytest.mark.parametrize("route", ["Q", "QR"])
def test_supported_reuse_routes_still_stop_at_protected_authority(tmp_path, route) -> None:
    scope = default_scopes()[2]
    scope["parent"] = None
    scope["facts"].update(
        {
            "development_origin": "reused",
            "safety_classification": "ASIL_B",
            "reuse_route": route,
        }
    )
    artifact = {
        "identity": _identity(),
        "requested_disposition": "reuse",
        "artifact_bindings": [{"revision": "accepted", "content_digest": "2" * 64}],
        "decision_refs": ["classification", "change-request"],
        "accepted_revision": "accepted",
        "applicability_rationale": "Declared applicable to this exact component.",
        "dependencies_current": True,
        "classification_approval_ref": "classification",
        "accepted_change_request_ref": "change-request",
        "reuse_route": route,
    }
    decisions = {
        "schema_version": 1,
        "references": [{"id": "classification"}, {"id": "change-request"}],
    }
    inventory = {"schema_version": 1, "completeness": "complete", "artifacts": [artifact]}
    intake, _ = prepare_case(
        tmp_path / "case",
        native_ids=("wp__plan",),
        scopes=[scope],
        inventory=inventory,
        decisions=decisions,
    )
    result = build_plan(load_planning_inputs(intake))
    instance = result["instances"][0]
    assert instance["requested_disposition"] == "reuse"
    assert instance["effective_disposition"] == "unresolved"
    assert set(instance["finding_codes"]) == {"AUTHORITY_UNVERIFIED"}


def test_instance_limit_produces_a_deterministic_blocked_partial_draft(tmp_path) -> None:
    scope = default_scopes()[2]
    scope["parent"] = None
    rule = native_rule("wp__plan")
    rule["purposes"] = [f"purpose-{position:05d}" for position in range(10001)]
    intake, _ = prepare_case(
        tmp_path / "case",
        native_ids=("wp__plan",),
        scopes=[scope],
        rules=[rule],
    )
    first = build_plan(load_planning_inputs(intake))
    second = build_plan(load_planning_inputs(intake))
    assert first["closure_complete"] is False
    assert first["planning_status"] == "blocked"
    assert len(first["instances"]) == 10000
    assert "CLOSURE_LIMIT" in {item["code"] for item in first["findings"]}
    assert seal_plan(first)[1] == seal_plan(second)[1]
