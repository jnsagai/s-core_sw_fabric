"""Public CLI semantics, determinism, and prior-output preservation."""

from __future__ import annotations

import json

import yaml

from score_sw_fabric.cli import main
from score_sw_fabric.planning.closure import build_plan
from score_sw_fabric.planning.export import seal_plan
from score_sw_fabric.planning.reader import load_planning_inputs
from tests.planning_support import prepare_case, sha256, write_yaml


def test_cli_writes_complete_and_blocked_drafts_with_distinct_exits(tmp_path) -> None:
    intake, output = prepare_case(tmp_path / "complete")
    assert main(["plan", "--input", str(intake), "--out", str(output), "--json"]) == 0
    plan = json.loads(output.read_text(encoding="utf-8"))
    assert (plan["plan_kind"], plan["engineering_readiness"]) == ("draft", "not_evaluated")

    conflict = {
        "id": "conflict",
        "native_refs": [{}, {}],
        "message": "conflict",
        "required_action": "resolve",
    }
    intake, output = prepare_case(tmp_path / "blocked", source_conflicts=[conflict])
    assert main(["plan", "--input", str(intake), "--out", str(output), "--json"]) == 1
    assert json.loads(output.read_text(encoding="utf-8"))["planning_status"] == "blocked"


def test_invalid_input_preserves_prior_output(tmp_path) -> None:
    intake, output = prepare_case(tmp_path / "case")
    output.write_bytes(b"prior valid output\n")
    mapping = tmp_path / "case" / "mapping.yaml"
    mapping.write_text(mapping.read_text(encoding="utf-8") + "\nchanged: true\n", encoding="utf-8")
    assert main(["plan", "--input", str(intake), "--out", str(output), "--json"]) == 2
    assert output.read_bytes() == b"prior valid output\n"


def test_relocation_and_set_order_do_not_change_plan_bytes(tmp_path) -> None:
    first, _ = prepare_case(tmp_path / "first")
    second, _ = prepare_case(tmp_path / "second")
    raw = yaml.safe_load(second.read_text(encoding="utf-8"))
    raw["scopes"].reverse()
    raw["affected_scopes"].reverse()
    write_yaml(second, raw)
    mapping_path = tmp_path / "second" / "mapping.yaml"
    mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    mapping["rules"].reverse()
    raw["mapping"]["sha256"] = write_yaml(mapping_path, mapping)
    write_yaml(second, raw)

    _, first_bytes = seal_plan(build_plan(load_planning_inputs(first)))
    _, second_bytes = seal_plan(build_plan(load_planning_inputs(second)))
    assert first_bytes == second_bytes


def test_semantic_change_changes_plan_digest_but_not_logical_identity(tmp_path) -> None:
    intake, _ = prepare_case(tmp_path / "case")
    first, _ = seal_plan(build_plan(load_planning_inputs(intake)))
    raw = yaml.safe_load(intake.read_text(encoding="utf-8"))
    raw["change"]["intent"] = "Different declared semantic change."
    write_yaml(intake, raw)
    second, _ = seal_plan(build_plan(load_planning_inputs(intake)))
    assert first["digest"] != second["digest"]
    assert [item["instance_id"] for item in first["instances"]] == [
        item["instance_id"] for item in second["instances"]
    ]
    assert sha256(tmp_path / "case" / "catalogue.json") == raw["catalogue"]["sha256"]
