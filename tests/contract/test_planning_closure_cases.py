"""Shared-scope closure, cycles, and native revision selection cases."""

from __future__ import annotations

import copy
import json

import yaml

from score_sw_fabric.catalog.export import seal
from score_sw_fabric.planning.closure import build_plan
from score_sw_fabric.planning.reader import load_planning_inputs
from tests.planning_support import (
    default_scopes,
    native_rule,
    prepare_case,
    sha256,
    write_yaml,
)


def test_two_components_deduplicate_one_shared_module_obligation(tmp_path) -> None:
    scopes = default_scopes()[:3]
    second = copy.deepcopy(scopes[2])
    second["id"] = "component-2"
    scopes.append(second)
    rule = native_rule("wp__plan", selector="owning_module")
    rule["scope_kinds"] = ["component"]
    intake, _ = prepare_case(
        tmp_path / "case",
        native_ids=("wp__plan",),
        scopes=scopes,
        rules=[rule],
    )
    result = build_plan(load_planning_inputs(intake))
    assert len(result["instances"]) == 1
    assert result["instances"][0]["identity"]["scope_kind"] == "module"
    assert result["instances"][0]["requesting_scopes"] == [
        "component:component",
        "component:component-2",
    ]


def test_dependency_cycle_reaches_a_finite_fixed_set(tmp_path) -> None:
    first = native_rule("wp__a")
    second = native_rule("wp__b")
    first["dependencies"] = [
        {"target_rule": second["id"], "purpose": "primary", "scope_selector": "self"}
    ]
    second["dependencies"] = [
        {"target_rule": first["id"], "purpose": "primary", "scope_selector": "self"}
    ]
    scope = default_scopes()[2]
    scope["parent"] = None
    intake, _ = prepare_case(
        tmp_path / "case",
        native_ids=("wp__a", "wp__b"),
        scopes=[scope],
        rules=[first, second],
    )
    result = build_plan(load_planning_inputs(intake))
    assert result["closure_complete"] is True
    assert len(result["instances"]) == 2
    assert all(len(item["dependency_ids"]) == 1 for item in result["instances"])
    assert {item["dependency_ids"][0] for item in result["instances"]} == {
        item["instance_id"] for item in result["instances"]
    }


def test_multiple_native_revisions_require_explicit_profile_selection(tmp_path) -> None:
    root = tmp_path / "case"
    intake, _ = prepare_case(root, native_ids=("wp__plan",))
    catalogue_path = root / "catalogue.json"
    catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
    payload = {key: value for key, value in catalogue.items() if key != "digest"}
    revised = copy.deepcopy(payload["entities"][0])
    revised["native_version"] = 2
    revised["source_ref"]["native_version"] = 2
    revised["raw"]["version"] = 2
    revised["normalized"]["version"] = 2
    payload["entities"].append(revised)
    resealed, data = seal(payload)
    catalogue_path.write_bytes(data)

    profile_path = root / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["catalogue_digest"] = resealed["digest"]
    profile["expected_workproduct_count"] = 2
    profile["active_revisions"] = []
    profile_sha = write_yaml(profile_path, profile)
    intake_data = yaml.safe_load(intake.read_text(encoding="utf-8"))
    intake_data["catalogue"]["sha256"] = sha256(catalogue_path)
    intake_data["catalogue"]["digest"] = resealed["digest"]
    intake_data["profile"]["sha256"] = profile_sha
    write_yaml(intake, intake_data)

    result = build_plan(load_planning_inputs(intake))
    assert "PROFILE_REVISION_AMBIGUOUS" in {item["code"] for item in result["findings"]}
    assert all(row["state"] == "outside_scope" for row in result["coverage"])
    assert result["instances"] == []
