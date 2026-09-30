from __future__ import annotations

from pathlib import Path

import pytest

from score_sw_fabric.artifacts.reader import load_artifact_inputs
from score_sw_fabric.process_source.reader import InputError
from tests.artifact_support import prepare_artifact_case


def test_loads_strict_fixture_index_request(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path)
    inputs = load_artifact_inputs(request)
    assert inputs.operation == "index"
    assert inputs.snapshot["target_namespace"] == "fixture-component"
    assert inputs.artifact_profile["review"]["state"] == "pending"


def test_rejects_duplicate_yaml_key(tmp_path: Path) -> None:
    request = tmp_path / "request.yaml"
    request.write_text("schema_version: 1\nschema_version: 1\n")
    with pytest.raises(InputError, match="Duplicate YAML key"):
        load_artifact_inputs(request)


def test_rejects_snapshot_hash_mutation(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path)
    (tmp_path / "target/index.rst").write_text("changed")
    with pytest.raises(InputError, match="Snapshot (byte count|hash) mismatch"):
        load_artifact_inputs(request)
