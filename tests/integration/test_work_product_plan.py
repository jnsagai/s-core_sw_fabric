"""End-to-end work-product planning journeys."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from score_sw_fabric.planning.closure import build_plan
from score_sw_fabric.planning.export import seal_plan
from score_sw_fabric.planning.reader import load_planning_inputs
from tests.planning_support import default_scopes, prepare_case, sha256, write_yaml


def test_new_component_journey_has_exact_expected_set(tmp_path) -> None:
    intake, _ = prepare_case(tmp_path / "case")
    result, data = seal_plan(build_plan(load_planning_inputs(intake)))
    assert len(result["coverage"]) == 8
    assert len(result["instances"]) == 12
    assert all(item["effective_disposition"] == "create" for item in result["instances"])
    assert data.endswith(b"\n")
    assert result["engineering_readiness"] == "not_evaluated"


def test_full_source_backed_policy_accounts_for_all_74_workproducts(tmp_path) -> None:
    configured = os.environ.get("SCORE_FULL_CATALOGUE")
    catalogue_source = (
        Path(configured) if configured else Path("/tmp/s-core-001/fresh-catalogue.json")
    )
    if not catalogue_source.is_file():
        pytest.skip("set SCORE_FULL_CATALOGUE to the sealed 001 catalogue")
    root = tmp_path / "source-backed"
    root.mkdir()
    (root / "out").mkdir()
    (root / "reference").mkdir()
    catalogue = root / "catalogue.json"
    shutil.copyfile(catalogue_source, catalogue)
    profile = root / "profile.yaml"
    mapping = root / "mapping.yaml"
    repository = Path(__file__).resolve().parents[2]
    shutil.copyfile(repository / "profiles" / "cpp17-review-draft-v1.yaml", profile)
    shutil.copyfile(repository / "policies" / "s_core_applicability_v1.yaml", mapping)
    inventory = root / "inventory.yaml"
    decisions = root / "decisions.yaml"
    write_yaml(inventory, {"schema_version": 1, "completeness": "complete", "artifacts": []})
    write_yaml(decisions, {"schema_version": 1, "references": []})
    catalogue_data = json.loads(catalogue.read_text(encoding="utf-8"))
    scopes = [default_scopes()[3]]
    scopes[0]["parent"] = None
    scopes[0]["facts"]["security_relevance"] = "relevant"
    intake_data = {
        "schema_version": 1,
        "target_namespace": "source-backed-target",
        "change": {"id": "security-change", "intent": "Exercise all native work products."},
        "scopes": scopes,
        "affected_scopes": [{"kind": "feature", "id": "feature"}],
        "catalogue": {
            "path": catalogue.name,
            "sha256": sha256(catalogue),
            "digest": catalogue_data["digest"],
        },
        "profile": {"path": profile.name, "sha256": sha256(profile)},
        "mapping": {"path": mapping.name, "sha256": sha256(mapping)},
        "inventory": {"path": inventory.name, "sha256": sha256(inventory)},
        "decisions": {"path": decisions.name, "sha256": sha256(decisions)},
        "local_paths": {"output_root": "out", "reference_roots": ["reference"]},
    }
    intake = root / "intake.yaml"
    write_yaml(intake, intake_data)
    result = build_plan(load_planning_inputs(intake))
    assert len(result["coverage"]) == 74
    assert {row["native_ref"]["native_id"] for row in result["coverage"]} == {
        item["native_id"] for item in catalogue_data["entities"] if item["type"] == "workproduct"
    }
    assert "NATIVE_SOURCE_CONFLICT" in {item["code"] for item in result["findings"]}
    audit = next(
        item
        for item in result["instances"]
        if item["identity"]["native_work_product_id"] == "wp__audit_report_security"
    )
    assert "tailoring needs discussion" in audit["rationale"]
    assert result["planning_status"] == "blocked"
