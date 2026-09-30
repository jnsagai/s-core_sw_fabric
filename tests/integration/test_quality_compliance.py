"""Genuine local findings and replayed fixture decisions cannot grant compliance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.cli import main
from score_sw_fabric.quality import assessment, imports, packet, runner
from tests.integration.test_quality_packet import selected_decision
from tests.quality_decision_support import (
    AS_OF,
    CONTEXT,
    fixture_assessment,
)
from tests.quality_import_support import from_local_run, write_json
from tests.quality_support import ref


def selected(tmp: Path) -> tuple[Path, dict[str, Any]]:
    packet_selection, _, decision = selected_decision(tmp)
    r = json.loads(packet_selection.read_text())
    local = tmp / "local"
    origin = json.loads((local / "origin.json").read_text())
    imported = from_local_run(local, "clang-tidy", origin, local / "component")
    _, imported_report, _, _ = imports.import_outputs(imported)
    im = json.loads(imported.read_text())
    r["coverage"] = None
    r["analyses"] = [
        {
            "request": ref(imported),
            "report": write_json(local / "import.json", imported_report),
        }
    ]
    r["source_snapshots"] = [
        {"baseline_digest": origin["baseline"]["full_digest"], "root": str(local / "component")},
        {
            "baseline_digest": imported_report["baseline"]["full_digest"],
            "root": str(local / "component"),
        },
    ]
    write_json(packet_selection, r)
    _, original, _, _ = packet.packet(packet_selection)
    p = tmp / "assessment-request.json"
    write_json(
        p,
        {
            "schema_version": 1,
            "kind": "quality_assessment_request",
            "profile": r["profile"],
            "packet": write_json(tmp / "packet.json", original),
            "current_baseline": im["baseline"],
            "decisions": [],
            "assurance_domain": "fixture_contract",
            "as_of": AS_OF,
            "protected_roots": [],
        },
    )
    return p, decision


def test_fixture_disposition_remains_visible_and_compliance_blocked_without_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = selected(tmp_path)
    monkeypatch.setattr(runner, "run", lambda *a: pytest.fail("assessment analyzer execution"))
    _, record, _, _ = assessment.assess(path)
    assert record["dispositions"][0]["observation"] == "accepted_fixture"
    assert record["outcome"] == "blocked"
    assert record["accepted_claims"] == 0
    assert any(r["kind"] == "analysis" and r["outcome"] == "fail" for r in record["obligations"])
    assert assessment.verify_assessment(record)["reproduced"]


def test_assessment_as_of_rechecks_current_fixture_expiry(tmp_path: Path) -> None:
    path, _ = selected(tmp_path)
    r = json.loads(path.read_text())
    r["as_of"] = "2026-12-03T10:00:00Z"
    write_json(path, r)
    _, record, _, _ = assessment.assess(path)
    assert record["dispositions"][0]["observation"] == "stale"
    assert "DECISION_EXPIRED" in record["dispositions"][0]["reasons"]
    assert record["outcome"] == "blocked"
    assert assessment.verify_assessment(record)["reproduced"]


def test_production_domain_cannot_reuse_fixture_acceptance(tmp_path: Path) -> None:
    path, _ = selected(tmp_path)
    r = json.loads(path.read_text())
    r["assurance_domain"] = "production"
    write_json(path, r)
    _, record, _, _ = assessment.assess(path)
    assert record["dispositions"][0]["observation"] != "accepted_fixture"
    assert record["dispositions"][0]["current_decision"]["state"] == "blocked"
    assert record["outcome"] == "blocked"


@pytest.mark.parametrize("exact", [False, True])
def test_supporting_005_packet_binding_is_exact_and_never_adopts_mapping(
    tmp_path: Path, exact: bool
) -> None:
    path, decision = selected(tmp_path)
    r = json.loads(path.read_text())
    original = json.loads(Path(r["packet"]["path"]).read_text())
    supporting = fixture_assessment(
        tmp_path / "local",
        decision["binding"],
        extra_bytes={"quality/complete-review-packet.json": canonical(original)} if exact else {},
    )
    r["decisions"] = [
        {
            "assessment": write_json(tmp_path / "supporting.json", supporting),
            "trust_context": ref(CONTEXT),
        }
    ]
    write_json(path, r)
    _, record, _, _ = assessment.assess(path)
    assert record["decisions"][0]["replay"]["reproduced"]
    assert record["decisions"][0]["binding"] == ("exact_packet" if exact else "other_subject")
    assert record["outcome"] == "blocked"
    assert "RULE_MAPPING_UNKNOWN" in record["gaps"]
    assert "MANUAL_REVIEW_PENDING" in record["gaps"]
    assert assessment.verify_assessment(record)["reproduced"]


def test_changed_current_tool_config_stales_fixture_disposition(tmp_path: Path) -> None:
    path, _ = selected(tmp_path)
    r = json.loads(path.read_text())
    bp = Path(r["current_baseline"]["path"])
    b = json.loads(bp.read_text())
    b["identities"][0]["config_sha256"] = "0" * 64
    from score_sw_fabric.assurance.models import seal

    r["current_baseline"] = write_json(bp, seal(b))
    write_json(path, r)
    _, record, _, _ = assessment.assess(path)
    assert record["dispositions"][0]["observation"] == "stale"
    assert "CONFIGURATION_CHANGED" in record["dispositions"][0]["reasons"]
    assert "BASELINE_DRIFT:identities" in record["gaps"]


def test_cli_assessment_determinism_offline_replay_and_output_protection(tmp_path: Path) -> None:
    path, _ = selected(tmp_path)
    out = tmp_path / "assessment.json"
    command = ["quality", "assess", "--request", str(path), "--out", str(out), "--json"]
    assert main(command) == 1
    prior = out.read_bytes()
    assert main(command) == 1 and out.read_bytes() == prior
    record = json.loads(prior)
    for p in tmp_path.rglob("*"):
        if p.is_file():
            p.unlink()
    assert assessment.verify_assessment(record)["reproduced"]


def test_clean_complementary_analysis_never_becomes_compliance(tmp_path: Path) -> None:
    from score_sw_fabric.quality import coverage
    from tests.integration.test_quality_coverage import selected_local

    selected_coverage = selected_local(tmp_path)
    coverage_request = json.loads(selected_coverage.read_text())
    _, matrix, _, _ = coverage.measure(selected_coverage)
    local = json.loads((tmp_path / "original-analysis-run.json").read_text())
    notice = tmp_path / "fixture-notice.txt"
    notice.write_text("Synthetic guideline association; no license eligibility or owner adoption.")
    packet_path = tmp_path / "packet-request.json"
    write_json(
        packet_path,
        {
            "schema_version": 1,
            "kind": "quality_packet_request",
            "profile": coverage_request["profile"],
            "coverage": {
                "request": ref(selected_coverage),
                "report": write_json(tmp_path / "matrix.json", matrix),
            },
            "analyses": [],
            "dispositions": [],
            "source_snapshots": [
                {"baseline_digest": b["full_digest"], "root": str(tmp_path / "component")}
                for b in [matrix["baseline"], local["baseline"]]
            ],
            "notices": [
                {
                    "id": "fixture-notice",
                    "license": "synthetic test",
                    "notice": "Unverified association",
                    "ref": ref(notice),
                    "applies_to": [
                        "tool:clang-tidy",
                        *("native:" + s["id"] for s in matrix["profile"]["native_sources"]),
                    ],
                }
            ],
            "protected_roots": [],
        },
    )
    _, original, _, _ = packet.packet(packet_path)
    path = tmp_path / "assessment-request.json"
    write_json(
        path,
        {
            "schema_version": 1,
            "kind": "quality_assessment_request",
            "profile": coverage_request["profile"],
            "packet": write_json(tmp_path / "packet.json", original),
            "current_baseline": coverage_request["baseline"],
            "decisions": [],
            "assurance_domain": "production",
            "as_of": AS_OF,
            "protected_roots": [],
        },
    )
    _, record, _, _ = assessment.assess(path)
    assert any(o["kind"] == "analysis" and o["outcome"] == "pass" for o in record["obligations"])
    assert record["packet"]["coverage"]["report"]["counts"]["covered"] == 1
    assert record["outcome"] == "blocked" and record["accepted_claims"] == 0
    assert "PRIMARY_EXECUTION_UNAVAILABLE" in record["gaps"]
    assert "MANUAL_REVIEW_PENDING" in record["gaps"]
    assert assessment.verify_assessment(record)["reproduced"]


def test_correction_header_without_fresh_analysis_stays_unresolved(tmp_path: Path) -> None:
    from score_sw_fabric.assurance.models import seal

    path, _ = selected(tmp_path)
    current = json.loads(path.read_text())
    packet_selection = tmp_path / "fixture/packet-request.json"
    request = json.loads(packet_selection.read_text())
    disposition = request["dispositions"][0]
    draft_request_path = Path(disposition["request"]["path"])
    draft_request = json.loads(draft_request_path.read_text())
    draft_path = Path(draft_request["draft"]["path"])
    draft = json.loads(draft_path.read_text())
    draft["requested_kind"] = "correction"
    draft = seal(draft)
    draft_request["draft"] = write_json(draft_path, draft)
    disposition["request"] = write_json(draft_request_path, draft_request)
    review_path = Path(disposition["review"]["path"])
    review = json.loads(review_path.read_text())
    review.update(
        draft=draft,
        state="corrected",
        outcome="completed",
        reasons=["FRESH_LOCAL_CORRECTION_OBSERVED"],
        fresh_run=None,
    )
    disposition["review"] = write_json(review_path, seal(review))
    disposition["decision"] = None
    write_json(packet_selection, request)
    _, original, _, _ = packet.packet(packet_selection)
    current["packet"] = write_json(tmp_path / "packet.json", original)
    write_json(path, current)
    _, record, _, _ = assessment.assess(path)
    assert record["dispositions"][0]["observation"] == "blocked"
    assert "FRESH_ANALYSIS_REQUIRED" in record["dispositions"][0]["reasons"]
    assert record["outcome"] == "blocked"
    assert assessment.verify_assessment(record)["reproduced"]
