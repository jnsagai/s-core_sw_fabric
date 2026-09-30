"""Actual local original outputs and synthetic 005 decisions stay visibly separate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import decisions, dispositions, packet, runner
from tests.quality_decision_support import (
    controls,
    fixture_assessment,
    subject_request,
    with_assessment,
)
from tests.quality_disposition_support import change_request
from tests.quality_import_support import write_json
from tests.quality_packet_support import packet_request
from tests.quality_support import ref


def selected_decision(tmp: Path) -> tuple[Path, Path, dict[str, Any]]:
    fixture = tmp / "fixture"
    fixture.mkdir()
    path = packet_request(fixture)
    local = tmp / "local"
    local.mkdir()
    decision_request = controls(local)
    _, binding, _, _ = decisions.subject(subject_request(decision_request))
    with_assessment(decision_request, fixture_assessment(local, binding))
    _, result, _, _ = decisions.assess(decision_request)
    assert result["state"] == "accepted_fixture"
    d = json.loads(decision_request.read_text())
    request = json.loads(path.read_text())
    request["dispositions"] = [
        {
            "request": d["disposition_request"],
            "review": d["review"],
            "decision": {
                "request": ref(decision_request),
                "result": write_json(local / "decision-result.json", result),
            },
        }
    ]
    request["source_snapshots"].append(
        {
            "baseline_digest": result["binding"]["current_baseline"]["full_digest"],
            "root": str(local / "component"),
        }
    )
    request["notices"][0]["applies_to"].append("tool:clang-tidy")
    write_json(path, request)
    return path, decision_request, result


def test_packet_closes_fixture_decision_and_genuine_local_original_without_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _, _ = selected_decision(tmp_path)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("packet must not execute an analyzer")

    monkeypatch.setattr(dispositions, "execute_current", forbidden)
    monkeypatch.setattr(runner, "run", forbidden)
    status, record, _, _ = packet.packet(path)
    assert status == 0
    assert record["dispositions"][0]["decision"]["result"]["state"] == "accepted_fixture"
    assert record["accepted_claims"] == 0
    assert {"fixture", "local_unprotected_execution", "fixture_contract_evaluation"} <= set(
        record["origins"]
    )
    # 005 may materialize its own embedded fixture in a fresh temporary directory.
    # Original provenance labels must never be opened by portable replay.
    labels = {f["path"] for f in record["files"]}
    original_open, original_stat = Path.open, Path.stat

    def safe_open(p: Path, *args: Any, **kwargs: Any) -> Any:
        if str(p) in labels:
            pytest.fail("portable verifier opened an original host path")
        return original_open(p, *args, **kwargs)

    def safe_stat(p: Path, *args: Any, **kwargs: Any) -> Any:
        if str(p) in labels:
            pytest.fail("portable verifier probed an original host path")
        return original_stat(p, *args, **kwargs)

    with monkeypatch.context() as guarded:
        guarded.setattr(Path, "open", safe_open)
        guarded.setattr(Path, "stat", safe_stat)
        verified = packet.verify_packet(record)
    assert verified["reproduced"], verified


def test_full_review_history_is_retained(tmp_path: Path) -> None:
    path, decision_request, _ = selected_decision(tmp_path)
    decision = json.loads(decision_request.read_text())
    disposition = Path(decision["disposition_request"]["path"])
    prior = json.loads(Path(decision["review"]["path"]).read_text())
    prior_ref = write_json(tmp_path / "prior-review.json", prior)
    change_request(disposition, previous=prior_ref)
    _, review, _, _ = dispositions.review(disposition)
    request = json.loads(path.read_text())
    request["dispositions"] = [
        {
            "request": ref(disposition),
            "review": write_json(tmp_path / "review2.json", review),
            "decision": None,
        }
    ]
    write_json(path, request)
    _, record, _, _ = packet.packet(path)
    assert record["dispositions"][0]["history"][0]["record"] == prior
    assert packet.verify_packet(record)["reproduced"]
    out = tmp_path / "prior-review.json"
    with pytest.raises(InputError):
        packet.packet(path, out)
    assert json.loads(out.read_text()) == prior


def test_cli_packet_deterministic_and_refusal_preserves_output(tmp_path: Path) -> None:
    path = packet_request(tmp_path)
    out = tmp_path / "packet.json"
    command = ["quality", "packet", "--request", str(path), "--out", str(out), "--json"]
    assert main(command) == 0
    original = out.read_bytes()
    assert main(command) == 0 and out.read_bytes() == original
    request = json.loads(path.read_text())
    request["extra"] = True
    write_json(path, request)
    assert main(command) == 2 and out.read_bytes() == original


def test_clean_local_coverage_packet_stays_ineligible(tmp_path: Path) -> None:
    from score_sw_fabric.quality import coverage
    from tests.integration.test_quality_coverage import selected_local

    selection = selected_local(tmp_path)
    _, matrix, _, _ = coverage.measure(selection)
    notice = tmp_path / "fixture-NOTICE.txt"
    notice.write_text("Local test observations and synthetic guideline associations only.")
    request = {
        "schema_version": 1,
        "kind": "quality_packet_request",
        "profile": json.loads(selection.read_text())["profile"],
        "coverage": {
            "request": ref(selection),
            "report": write_json(tmp_path / "matrix.json", matrix),
        },
        "analyses": [],
        "dispositions": [],
        "source_snapshots": [
            {
                "baseline_digest": matrix["baseline"]["full_digest"],
                "root": str(tmp_path / "component"),
            },
            {
                "baseline_digest": json.loads(
                    (tmp_path / "original-analysis-run.json").read_text()
                )["baseline"]["full_digest"],
                "root": str(tmp_path / "component"),
            },
        ],
        "notices": [
            {
                "id": "fixture-notice",
                "license": "synthetic test association",
                "notice": "No license eligibility",
                "ref": ref(notice),
                "applies_to": [
                    "tool:clang-tidy",
                    *("native:" + s["id"] for s in matrix["profile"]["native_sources"]),
                ],
            }
        ],
        "protected_roots": [],
    }
    selected = tmp_path / "packet-request.json"
    write_json(selected, request)
    _, result, _, _ = packet.packet(selected)
    assert result["coverage"]["report"]["rows"][0]["state"] == "covered"
    assert {"imported_unverified", "local_unprotected_execution"} <= set(result["origins"])
    assert result["accepted_claims"] == 0
    assert packet.verify_packet(result)["reproduced"]


def test_correction_packet_retains_both_source_versions_without_rerunning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    from tests.quality_disposition_support import selection as disposition_selection
    from tests.quality_support import ROOT
    from tests.quality_support import request as run_request

    fixture = tmp_path / "fixture"
    fixture.mkdir()
    path = packet_request(fixture)
    local = tmp_path / "local"
    local.mkdir()
    current = run_request(local)
    _, original, _, _ = runner.run(current)
    selected = disposition_selection(local, original, current)
    _, draft, _, _ = dispositions.review(selected)
    prior_ref = write_json(local / "prior.json", draft)
    historical = tmp_path / "historical"
    historical.mkdir()
    shutil.copy2(local / "component/check.cpp", historical / "check.cpp")
    shutil.copy2(ROOT / "tests/fixtures/quality/corrected/check.cpp", local / "component/check.cpp")
    current = run_request(local)
    change_request(
        selected,
        action="check_correction",
        current={"adapter": "clang-tidy", "request": ref(current)},
        previous=prior_ref,
    )
    _, correction, _, _ = dispositions.review(selected)
    assert correction["state"] == "corrected"
    request = json.loads(path.read_text())
    request["dispositions"] = [
        {
            "request": ref(selected),
            "review": write_json(local / "correction.json", correction),
            "decision": None,
        }
    ]
    request["source_snapshots"].extend(
        [
            {"baseline_digest": original["baseline"]["full_digest"], "root": str(historical)},
            {
                "baseline_digest": correction["current_baseline"]["full_digest"],
                "root": str(local / "component"),
            },
        ]
    )
    request["notices"][0]["applies_to"].append("tool:clang-tidy")
    write_json(path, request)
    monkeypatch.setattr(
        dispositions, "execute_current", lambda *a, **k: pytest.fail("packet rerun")
    )
    _, record, _, _ = packet.packet(path)
    assert len(record["sources"]) == 3
    assert record["dispositions"][0]["review"]["state"] == "corrected"
    assert record["dispositions"][0]["history"][0]["record"] == draft
    assert record["accepted_claims"] == 0
    assert packet.verify_packet(record)["reproduced"]
