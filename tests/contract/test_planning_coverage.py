"""Coverage and conservative applicability contract tests."""

from __future__ import annotations

from score_sw_fabric.planning.closure import build_plan
from score_sw_fabric.planning.reader import load_planning_inputs
from tests.planning_support import default_scopes, native_rule, prepare_case


def _plan(path):
    return build_plan(load_planning_inputs(path))


def test_every_native_scope_pair_has_coverage_and_review_purposes_are_distinct(tmp_path) -> None:
    intake, _ = prepare_case(tmp_path / "case")
    result = _plan(intake)
    assert len(result["coverage"]) == 8
    assert len(result["instances"]) == 12
    review_instances = [
        item
        for item in result["instances"]
        if item["identity"]["native_work_product_id"] == "wp__fdr_reports"
    ]
    assert {item["purpose"] for item in review_instances} == {"plan", "package"}
    assert len({item["instance_id"] for item in review_instances}) == 8
    assert result["planning_status"] == "complete"


def test_inventory_deletion_does_not_delete_expected_obligations(tmp_path) -> None:
    intake, _ = prepare_case(tmp_path / "case")
    result = _plan(intake)
    assert len(result["instances"]) == 12
    assert {item["effective_disposition"] for item in result["instances"]} == {"create"}


def test_missing_mapping_and_unknown_profile_facts_remain_blocked(tmp_path) -> None:
    scopes = default_scopes()
    scopes[2]["facts"]["safety_classification"] = "unknown"
    intake, _ = prepare_case(
        tmp_path / "case",
        scopes=scopes,
        rules=[native_rule("wp__plan")],
    )
    result = _plan(intake)
    codes = {item["code"] for item in result["findings"]}
    assert {"CLASSIFICATION_UNKNOWN", "MAPPING_COVERAGE_GAP"} <= codes
    assert any(item["state"] == "unresolved" for item in result["coverage"])
    assert result["planning_status"] == "blocked"


def test_missing_scope_context_retains_a_blocked_coverage_cell(tmp_path) -> None:
    scope = default_scopes()[2]
    scope["parent"] = None
    rule = native_rule("wp__plan", selector="owning_platform")
    intake, _ = prepare_case(
        tmp_path / "case",
        native_ids=("wp__plan",),
        scopes=[scope],
        rules=[rule],
    )
    result = _plan(intake)
    assert result["coverage"][0]["state"] == "selected"
    assert "SCOPE_CONTEXT_MISSING" in {item["code"] for item in result["findings"]}


def test_source_conflict_is_never_normalized_away(tmp_path) -> None:
    conflict = {
        "id": "security-fdr",
        "native_refs": [
            {"source_id": "process", "native_id": "wp__fdr_reports_security"},
            {"source_id": "template", "native_id": "wp__fdr_reports"},
        ],
        "message": "Process and template use different security FDR native IDs.",
        "required_action": "Resolve upstream without local substitution.",
    }
    intake, _ = prepare_case(tmp_path / "case", source_conflicts=[conflict])
    result = _plan(intake)
    finding = next(item for item in result["findings"] if item["code"] == "NATIVE_SOURCE_CONFLICT")
    assert finding["location"] == "source_conflict:security-fdr"
    assert result["planning_status"] == "blocked"
