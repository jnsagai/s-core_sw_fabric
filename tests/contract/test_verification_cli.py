"""CLI outcome codes and guarded report publication."""

from __future__ import annotations

import json
from pathlib import Path

from score_sw_fabric.cli import main
from score_sw_fabric.safety.analysis import check
from score_sw_fabric.verification.design import DESIGN_FIELDS
from score_sw_fabric.verification.profile import PROFILE_FIELDS, TOOLCHAIN_FIELDS
from score_sw_fabric.verification.report import REPORT_FIELDS
from score_sw_fabric.verification.runner import RUN_FIELDS
from tests.safety_support import check_request, copy_version
from tests.verification_support import PROFILE, ROOT, fixture, ref, request


def _call(command: str, source: Path, out: Path) -> int:
    return main(["verify", command, "--request", str(source), "--out", str(out), "--json"])


def test_cli_end_to_end_and_mismatch_preserves_output(tmp_path: Path) -> None:
    fixture(tmp_path)
    design_out = tmp_path / "out/design.json"
    run_out = tmp_path / "out/run.json"
    assert _call("design", request(tmp_path, "design"), design_out) == 0
    assert _call("run", request(tmp_path, "run"), run_out) == 0
    v1 = copy_version(tmp_path, "v1", "safety-v1")
    v2 = copy_version(tmp_path, "v2", "safety-v2")
    safety_request = check_request(tmp_path, v2, baseline=v1, iteration=2)
    _, safety, _, _ = check(safety_request)
    safety_out = tmp_path / "out/safety.json"
    safety_out.write_text(json.dumps(safety))
    report_request = tmp_path / "report-request.json"
    report_request.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "verification_report_request",
                "profile": ref(PROFILE),
                "design_report": ref(design_out),
                "runs": [ref(run_out)],
                "safety_reports": [ref(safety_out)],
                "protected_roots": [],
            }
        )
    )
    report_out = tmp_path / "report.json"
    assert _call("report", report_request, report_out) == 0
    result = json.loads(report_out.read_text())
    assert result["outcome"] == "verified_on_baseline"
    assert result["assurance_eligibility"] == "not_eligible"
    assert result["mitigation_candidates"]
    assert all(
        item["closure_evidence"] == "missing_005_verified_evidence"
        for item in result["mitigation_candidates"]
    )
    for name, output in (
        ("verification-design-report", design_out),
        ("verification-run", run_out),
        ("verification-milestone-report", report_out),
    ):
        schema = json.loads((ROOT / f"schemas/{name}.schema.json").read_text())
        assert set(json.loads(output.read_text())) == set(schema["required"])
    before = report_out.read_bytes()
    bad = json.loads(report_request.read_text())
    bad["runs"][0]["sha256"] = "0" * 64
    report_request.write_text(json.dumps(bad))
    assert _call("report", report_request, report_out) == 2
    assert report_out.read_bytes() == before


def test_request_schema_fields_match_readers() -> None:
    cases = {
        "verification-profile": PROFILE_FIELDS,
        "verification-toolchain-profile": TOOLCHAIN_FIELDS,
        "verification-design-request": DESIGN_FIELDS,
        "verification-run-request": RUN_FIELDS,
        "verification-report-request": REPORT_FIELDS,
    }
    for name, fields in cases.items():
        schema = json.loads((ROOT / f"schemas/{name}.schema.json").read_text())
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == {"schema_version", "kind", *fields}
