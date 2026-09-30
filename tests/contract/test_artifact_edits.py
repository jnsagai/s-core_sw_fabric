from __future__ import annotations

from pathlib import Path

import pytest

from score_sw_fabric.artifacts.edit import apply_edits
from score_sw_fabric.artifacts.models import ArtifactSemanticError
from score_sw_fabric.artifacts.reader import load_artifact_inputs, read_snapshot_files
from tests.artifact_support import content_edit, prepare_artifact_case


def test_scoped_content_edit_preserves_unrelated_bytes(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path)
    inputs = load_artifact_inputs(request)
    files = read_snapshot_files(inputs)
    operation = content_edit(tmp_path)
    updated, results, source_map = apply_edits(files, [operation], inputs.artifact_profile)
    assert "Updated explicit content." in updated["index.rst"]
    assert "Manual wrapper prose that must remain byte exact." in updated["index.rst"]
    assert results[0]["unchanged_complement"] == "byte_exact"
    assert source_map[0]["plan_instance"] == "obligation-a"


def test_stale_preimage_blocks_whole_edit(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path)
    inputs = load_artifact_inputs(request)
    operation = content_edit(tmp_path)
    operation["expected_preimage"] = "0" * 64
    with pytest.raises(ArtifactSemanticError, match="Stale preimage"):
        apply_edits(read_snapshot_files(inputs), [operation], inputs.artifact_profile)
