"""CLI fixture journeys retain independent 005 closure after local inputs disappear."""

from __future__ import annotations

import json
from pathlib import Path

from score_sw_fabric.assurance.package import verify_assessment
from score_sw_fabric.cli import main
from tests.quality_decision_support import (
    CONTEXT,
    controls,
    fixture_assessment,
    subject_request,
    with_assessment,
)
from tests.quality_disposition_support import change_request
from tests.quality_support import ROOT


def test_cli_fixture_expiry_production_and_portable_closure(tmp_path: Path) -> None:
    path = controls(tmp_path)
    subject_path = subject_request(path)
    binding_out = tmp_path / "binding-out.json"
    result_out = tmp_path / "result-out.json"
    assert (
        main(
            [
                "quality",
                "decision-subject",
                "--request",
                str(subject_path),
                "--out",
                str(binding_out),
                "--json",
            ]
        )
        == 0
    )
    binding = json.loads(binding_out.read_text())
    with_assessment(path, fixture_assessment(tmp_path, binding))
    command = ["quality", "decision", "--request", str(path), "--out", str(result_out), "--json"]
    assert main(command) == 0
    accepted = json.loads(result_out.read_text())
    assert accepted["state"] == "accepted_fixture"
    frozen = result_out.read_bytes()
    change_request(path, as_of="2026-12-03T10:00:00Z")
    assert main(command) == 1
    assert json.loads(result_out.read_text())["state"] == "stale"
    change_request(path, assurance_domain="production")
    assert main(command) == 1
    assert json.loads(result_out.read_text())["state"] == "blocked"
    assert accepted["binding"]["review"]["state"] == "pending_review"
    # Original saved record remains portable; replay uses retained originals, not local paths.
    for source in (tmp_path / "component").iterdir():
        source.unlink()
    retained = json.loads(frozen)
    entry = retained["decisions"][0]
    assert verify_assessment(entry["assessment"], entry["trust_context"])["reproduced"] is True


def test_checked_in_fixture_is_independently_portable() -> None:
    base = ROOT / "tests/fixtures/quality/dispositions/decision-replay"
    assessment = json.loads((base / "assessment.json").read_text())
    context = json.loads(CONTEXT.read_text())
    replay = verify_assessment(assessment, context)
    assert replay["reproduced"] is True and replay["outcome"] == "pass"
    result = json.loads((base / "result.json").read_text())
    assert result["state"] == "accepted_fixture"
    assert result["decisions"][0]["assessment"] == assessment
    assert result["decisions"][0]["current_gate"]["outcome"] == "pass"
    assert result["engineering_readiness"] == "not_evaluated"
