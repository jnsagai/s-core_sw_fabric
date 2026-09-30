"""Contract tests for bounded planning documents and protected paths."""

from __future__ import annotations

import os

import pytest
import yaml

from score_sw_fabric.planning.export import write_plan
from score_sw_fabric.planning.reader import load_planning_inputs
from score_sw_fabric.process_source.reader import InputError
from tests.planning_support import default_scopes, prepare_case, write_yaml


def test_loads_selected_documents_and_normalizes_semantic_inputs(tmp_path) -> None:
    intake, _ = prepare_case(tmp_path / "case")
    loaded = load_planning_inputs(intake)
    assert loaded.catalogue_digest == loaded.profile["catalogue_digest"]
    assert set(loaded.semantic_digests) == {
        "profile",
        "mapping",
        "inventory",
        "decisions",
        "intake",
    }


def test_rejects_duplicate_yaml_keys(tmp_path) -> None:
    intake, _ = prepare_case(tmp_path / "case")
    intake.write_text("schema_version: 1\nschema_version: 1\n", encoding="utf-8")
    with pytest.raises(InputError) as raised:
        load_planning_inputs(intake)
    assert raised.value.code == "DUPLICATE_YAML_KEY"


def test_rejects_scope_cycles_and_missing_affected_scopes(tmp_path) -> None:
    scopes = default_scopes()
    scopes[0]["parent"] = {"kind": "component", "id": "component"}
    intake, _ = prepare_case(tmp_path / "cycle", scopes=scopes)
    with pytest.raises(InputError) as raised:
        load_planning_inputs(intake)
    assert raised.value.code == "SCOPE_CYCLE"

    intake, _ = prepare_case(tmp_path / "affected")
    raw = yaml.safe_load(intake.read_text(encoding="utf-8"))
    raw["affected_scopes"].append({"kind": "component", "id": "missing"})
    write_yaml(intake, raw)
    with pytest.raises(InputError) as raised:
        load_planning_inputs(intake)
    assert raised.value.code == "AFFECTED_SCOPES"


def test_rejects_unsafe_paths_and_output_hardlink_aliases(tmp_path) -> None:
    intake, output = prepare_case(tmp_path / "case")
    raw = yaml.safe_load(intake.read_text(encoding="utf-8"))
    raw["profile"]["path"] = "../profile.yaml"
    write_yaml(intake, raw)
    with pytest.raises(InputError) as raised:
        load_planning_inputs(intake)
    assert raised.value.code == "PATH_ESCAPE"

    intake, output = prepare_case(tmp_path / "alias")
    loaded = load_planning_inputs(intake)
    os.link(tmp_path / "alias" / "profile.yaml", output)
    with pytest.raises(InputError) as raised:
        write_plan(output, b"protected", loaded)
    assert raised.value.code == "OUTPUT_ALIAS"


def test_rejects_output_in_reference_tree_and_symlink_parent(tmp_path) -> None:
    intake, _ = prepare_case(tmp_path / "case")
    loaded = load_planning_inputs(intake)
    with pytest.raises(InputError) as raised:
        write_plan(tmp_path / "case" / "reference" / "plan.json", b"x", loaded)
    assert raised.value.code in {"OUTPUT_PATH", "OUTPUT_SOURCE_ROOT"}

    link = tmp_path / "case" / "out" / "linked"
    link.symlink_to(tmp_path / "case" / "reference", target_is_directory=True)
    with pytest.raises(InputError) as raised:
        write_plan(link / "plan.json", b"x", loaded)
    assert raised.value.code in {"OUTPUT_PATH", "OUTPUT_SYMLINK", "OUTPUT_SOURCE_ROOT"}
