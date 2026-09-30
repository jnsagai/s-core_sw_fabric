from __future__ import annotations

import copy
from pathlib import Path

from score_sw_fabric.artifacts.diff import compare_artifacts
from score_sw_fabric.artifacts.drift import inspect_drift
from score_sw_fabric.artifacts.package import candidate_request, load_profile
from tests.artifact_support import prepare_artifact_case


def test_semantic_diff_reports_only_changed_categories(tmp_path: Path) -> None:
    request, output = prepare_artifact_case(tmp_path, operation="candidate")
    before = candidate_request(request, output)
    after = copy.deepcopy(before)
    after["index"]["needs"][0]["title"] = "Changed"
    from score_sw_fabric.compiler.reader import semantic_digest

    after["index"]["digest"] = semantic_digest(after["index"])
    after["digest"] = semantic_digest(after)
    result = compare_artifacts(before, after)
    assert result["equivalent"] is False
    assert result["categories"]["content"]["modified"]


def test_direct_candidate_edit_is_drift_and_cannot_be_adopted(tmp_path: Path) -> None:
    request, output = prepare_artifact_case(tmp_path, operation="candidate")
    candidate = candidate_request(request, output)
    candidate["overlay_files"][0]["content"] += "direct edit"
    profile = load_profile(Path("profiles/s_core_native_artifacts_v1.yaml"))
    result = inspect_drift(candidate, profile)
    assert result["clean"] is False
    assert result["findings"][0]["code"] == "GENERATED_DRIFT"
