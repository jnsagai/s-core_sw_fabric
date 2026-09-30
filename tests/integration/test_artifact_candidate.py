from __future__ import annotations

from pathlib import Path

from score_sw_fabric.artifacts.edit import apply_edits
from score_sw_fabric.artifacts.package import candidate_request
from score_sw_fabric.artifacts.reader import load_artifact_inputs, read_snapshot_files
from tests.artifact_support import create_edit, prepare_artifact_case


def test_update_candidate_round_trip_and_relocation_are_deterministic(tmp_path: Path) -> None:
    request_a, output_a = prepare_artifact_case(tmp_path / "a", operation="candidate")
    request_b, output_b = prepare_artifact_case(tmp_path / "b", operation="candidate")
    first = candidate_request(request_a, output_a)
    second = candidate_request(request_b, output_b)
    assert first == second
    assert first["overlay_files"][0]["edit_ids"] == ["edit-content-1"]


def test_create_uses_exact_template_and_resolves_all_placeholders(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path, kind="analysis")
    inputs = load_artifact_inputs(request)
    files, results, _ = apply_edits(
        read_snapshot_files(inputs), [create_edit()], inputs.artifact_profile
    )
    assert "created.rst" in files
    assert "{{" not in files["created.rst"]
    assert results[0]["kind"] == "create_document"
