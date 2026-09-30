"""Failure history, deterministic baseline and human review boundaries."""

from __future__ import annotations

from pathlib import Path

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.verification.design import design
from score_sw_fabric.verification.profile import load_profile
from score_sw_fabric.verification.report import build_report
from score_sw_fabric.verification.runner import run
from tests.verification_support import PROFILE, fixture, request


def test_correction_history_and_pending_review(tmp_path: Path) -> None:
    fixture(tmp_path, defect=True)
    profile = load_profile(PROFILE.read_bytes())
    _, failing_design, _, _ = design(request(tmp_path, "design"))
    _, failing, _, _ = run(request(tmp_path, "run"))
    source = tmp_path / "component/src/telemetry_guard.cpp"
    source.write_bytes(
        (tmp_path / "component/src-defect/telemetry_guard.cpp")
        .read_bytes()
        .replace(b">= timeout_", b"> timeout_")
    )
    _, passing_design, _, _ = design(request(tmp_path, "design"))
    _, passing, _, _ = run(request(tmp_path, "run"))
    assert failing_design["outcome"] == passing_design["outcome"] == "complete"
    safety = [
        seal(
            {
                "component": "telemetry_guard",
                "analysis": "fmea",
                "profile": {"id": "fixture"},
                "outcome": "complete",
                "items": [
                    {
                        "mitigated_by": [
                            "comp_req__telemetry_guard__stale_detection",
                            "aou_req__telemetry_guard__consumer_check",
                        ]
                    }
                ],
            }
        )
    ]
    report = build_report(profile, passing_design, [failing, passing], safety)
    assert report["outcome"] == "verified_on_baseline"
    assert report["failures"][0]["resolved"]
    assert report["failures"][0]["routes"]
    assert report["inspection_packet"]["checklist"][0]["answer"] == "pending_human"
    assert "protected_evidence" in {item["id"] for item in report["pending_obligations"]}
    assert {item["closure_evidence"] for item in report["mitigation_candidates"]} == {
        "missing_005_verified_evidence"
    }

    conflicting = seal({**passing, "outcome": "failed"})
    report = build_report(profile, passing_design, [conflicting, passing], [])
    assert report["outcome"] == "blocked"
    assert "NONDETERMINISTIC_RESULT" in {item["code"] for item in report["findings"]}


def test_budget_escalates(tmp_path: Path) -> None:
    fixture(tmp_path, defect=True)
    profile = load_profile(PROFILE.read_bytes())
    _, design_record, _, _ = design(request(tmp_path, "design"))
    _, failing, _, _ = run(request(tmp_path, "run"))
    report = build_report(profile, design_record, [failing] * 3, [])
    assert report["outcome"] == "blocked"
    assert "ESCALATE_TO_HUMAN" in {item["code"] for item in report["findings"]}
