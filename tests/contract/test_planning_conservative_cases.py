"""Additional fail-closed applicability and reuse route cases."""

from __future__ import annotations

from score_sw_fabric.planning.closure import build_plan
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


def test_unknown_mapping_predicate_retains_candidate_instance(tmp_path) -> None:
    scope = default_scopes()[2]
    scope["parent"] = None
    scope["facts"]["safety_classification"] = "unknown"
    rule = native_rule("wp__plan")
    rule["when"] = [{"field": "safety_classification", "op": "eq", "value": "ASIL_B"}]
    intake, _ = prepare_case(
        tmp_path / "case",
        native_ids=("wp__plan",),
        scopes=[scope],
        rules=[rule],
    )
    result = build_plan(load_planning_inputs(intake))
    assert result["coverage"][0]["state"] == "unresolved"
    assert len(result["instances"]) == 1
    assert result["instances"][0]["applicability"] == "unresolved"
    assert result["instances"][0]["effective_disposition"] == "unresolved"


def test_dangling_declared_parent_is_a_blocked_draft_not_invalid_input(tmp_path) -> None:
    scope = default_scopes()[2]
    scope["parent"] = {"kind": "module", "id": "undeclared-module"}
    rule = native_rule("wp__plan", selector="owning_module")
    intake, _ = prepare_case(
        tmp_path / "case",
        native_ids=("wp__plan",),
        scopes=[scope],
        rules=[rule],
    )
    result = build_plan(load_planning_inputs(intake))
    assert "SCOPE_CONTEXT_MISSING" in {item["code"] for item in result["findings"]}
    assert result["planning_status"] == "blocked"


def test_reuse_requires_exact_binding_and_separate_decision_references(tmp_path) -> None:
    artifact = {
        "identity": _identity(),
        "requested_disposition": "reuse",
        "artifact_bindings": [{"revision": "old", "content_digest": "2" * 64}],
        "decision_refs": [],
        "accepted_revision": "new",
        "applicability_rationale": "Declared applicable to this exact component.",
        "dependencies_current": True,
        "classification_approval_ref": "classification",
        "accepted_change_request_ref": "change-request",
        "reuse_route": "Q",
    }
    inventory = {"schema_version": 1, "completeness": "complete", "artifacts": [artifact]}
    decisions = {"schema_version": 1, "references": [{"id": "classification"}]}
    intake, _ = prepare_case(
        tmp_path / "case",
        inventory=inventory,
        decisions=decisions,
    )
    result = build_plan(load_planning_inputs(intake))
    instance = next(item for item in result["instances"] if item["identity"] == _identity())
    assert {
        "REUSE_BINDING_STALE",
        "CHANGE_REQUEST_ACCEPTANCE_MISSING",
        "AUTHORITY_UNVERIFIED",
    } <= set(instance["finding_codes"])


def test_nq_safety_reuse_and_modified_reuse_keep_independent_blockers(tmp_path) -> None:
    scopes = default_scopes()
    scopes[2]["facts"].update(
        {
            "development_origin": "modified_reused",
            "safety_classification": "ASIL_B",
            "reuse_route": "NQ",
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
        "reuse_route": "NQ",
    }
    decisions = {
        "schema_version": 1,
        "references": [{"id": "classification"}, {"id": "change-request"}],
    }
    inventory = {"schema_version": 1, "completeness": "complete", "artifacts": [artifact]}
    intake, _ = prepare_case(
        tmp_path / "case",
        scopes=scopes,
        inventory=inventory,
        decisions=decisions,
    )
    result = build_plan(load_planning_inputs(intake))
    instance = next(item for item in result["instances"] if item["identity"] == _identity())
    assert {
        "CLASSIFICATION_ROUTE_UNSUPPORTED",
        "REUSE_REASSESSMENT_REQUIRED",
        "AUTHORITY_UNVERIFIED",
    } <= set(instance["finding_codes"])
