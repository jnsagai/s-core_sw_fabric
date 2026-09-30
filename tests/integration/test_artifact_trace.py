from __future__ import annotations

from pathlib import Path

from score_sw_fabric.artifacts.package import trace_request
from tests.artifact_support import prepare_artifact_case


def test_trace_report_has_fixed_expected_denominators_and_boundaries(tmp_path: Path) -> None:
    request, output = prepare_artifact_case(tmp_path, operation="trace")
    report, valid = trace_request(request, output)
    assert report["status"] == ("passed" if valid else "blocked")
    assert all(
        item["counts"]["denominator"] == len(item["denominator"]) for item in report["coverage"]
    )
    assert set(report["capabilities"].values()) == {"not_evaluated"}
    assert output.is_file()
