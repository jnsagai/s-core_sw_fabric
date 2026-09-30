"""Real local C++17 compile, GoogleTest result and coverage checks."""

from __future__ import annotations

from pathlib import Path

from score_sw_fabric.verification.profile import load_profile
from score_sw_fabric.verification.runner import metadata_findings, parse_results, run
from tests.verification_support import PROFILE, fixture, request


def test_real_pass_and_seeded_failure(tmp_path: Path) -> None:
    fixture(tmp_path)
    status, passing, _, _ = run(request(tmp_path, "run"))
    assert status == 0 and passing["outcome"] == "passed"
    assert len(passing["tests"]) == 13
    assert all(
        item["baseline_digest"] == passing["baseline"]["full_digest"] for item in passing["tests"]
    )
    assert passing["coverage"]["status"] == "imported"
    assert passing["coverage"]["units"][0]["branches_total"] > 0

    source = tmp_path / "component/src/telemetry_guard.cpp"
    source.write_bytes((tmp_path / "component/src-defect/telemetry_guard.cpp").read_bytes())
    status, failing, _, _ = run(request(tmp_path, "run"))
    assert status == 1 and failing["outcome"] == "failed"
    assert "TEST_FAILED" in {item["code"] for item in failing["findings"]}
    assert failing["baseline"]["source_digest"] != passing["baseline"]["source_digest"]
    assert any(item["state"] == "failing" for item in failing["requirements"])


def test_native_error_and_skip_classes() -> None:
    results = parse_results(
        b'<testsuites><testsuite><testcase classname="T" name="a">'
        b'<error message="boom"/></testcase><testcase classname="T" name="b">'
        b"<skipped/></testcase></testsuite></testsuites>"
    )
    assert [item["result"] for item in results] == ["failed", "skipped"]


def test_metadata_faults_name_native_rules() -> None:
    profile = load_profile(PROFILE.read_bytes())
    tests = parse_results(
        b'<testsuites><testsuite><testcase classname="T" name="bad">'
        b'<properties><property name="TestType" value="unknown"/>'
        b'<property name="FullyVerifies" value="comp_req__unknown"/>'
        b"</properties></testcase></testsuite></testsuites>"
    )
    findings = metadata_findings(profile, tests, {})
    codes = {item["code"] for item in findings}
    assert {
        "METADATA_VALUE",
        "METADATA_MISSING",
        "DESCRIPTION_EMPTY",
        "VERIFIES_UNRESOLVED",
    } <= codes
    assert all(item["rule"].startswith("gd_req__verification_") for item in findings)
