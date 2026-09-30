from __future__ import annotations

from pathlib import Path

from score_sw_fabric.artifacts.obligations import derive_obligations
from score_sw_fabric.artifacts.reader import load_artifact_inputs
from tests.artifact_support import prepare_artifact_case


def test_expected_set_is_derived_before_target_inspection(tmp_path: Path) -> None:
    request, _ = prepare_artifact_case(tmp_path, operation="trace")
    inputs = load_artifact_inputs(request)
    assert inputs.plan and inputs.workflow_package and inputs.trace_profile
    obligations = derive_obligations(inputs.plan, inputs.workflow_package, inputs.trace_profile)
    assert obligations
    assert {item["classification"] for item in obligations} >= {
        "native_artifact",
        "non_native_record",
        "external_boundary",
    }
    assert all(item["authority"] for item in obligations)
