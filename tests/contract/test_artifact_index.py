from __future__ import annotations

from pathlib import Path

import pytest

from score_sw_fabric.artifacts.index import build_index, require_valid_index
from score_sw_fabric.artifacts.models import ArtifactSemanticError
from score_sw_fabric.artifacts.native import validate_native
from score_sw_fabric.artifacts.reader import load_artifact_inputs, read_snapshot_files
from tests.artifact_support import prepare_artifact_case


def test_index_keeps_wrapper_child_status_and_source_identity_separate(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path)
    inputs = load_artifact_inputs(request)
    files = read_snapshot_files(inputs)
    receipt, export = validate_native(files, inputs.artifact_profile, inputs.local_paths)
    index = require_valid_index(
        build_index(files, inputs.snapshot, inputs.artifact_profile, export, receipt)
    )
    assert index["wrappers"][0]["status"] == "draft"
    assert all(item["status"] == "valid" for item in index["needs"])
    assert all(
        item["key"].startswith("fixture-component:score:")
        for item in [*index["wrappers"], *index["needs"]]
    )


def test_index_rejects_valid_wrapper_with_invalid_child(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path)
    inputs = load_artifact_inputs(request)
    files = read_snapshot_files(inputs)
    files["index.rst"] = files["index.rst"].replace(":status: valid", ":status: draft", 1)
    receipt, export = validate_native(files, inputs.artifact_profile, inputs.local_paths)
    index = build_index(files, inputs.snapshot, inputs.artifact_profile, export, receipt)
    with pytest.raises(ArtifactSemanticError):
        require_valid_index(index)
    assert any(item["code"] == "NATIVE_STATUS" for item in index["findings"])
