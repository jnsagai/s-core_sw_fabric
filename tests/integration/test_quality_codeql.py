"""Real selected CodeQL installation inspection; genuine analysis/report acceptance is unmet.

Select SCORE_CODEQL_PREREQUISITE_REQUEST to inspect installed original bytes. These checks
cannot stand in for T012's eligible database/query/native-report execution.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import verify_digest
from score_sw_fabric.cli import main
from score_sw_fabric.quality import codeql, dispositions, packet
from score_sw_fabric.quality.models import load_inputs
from tests.quality_support import ref, request


@pytest.mark.parametrize(
    "case,expected_count,expected_exit", [("seeded", 3, 1), ("corrected", 0, 0)]
)
def test_actual_public_fixed_demonstration(
    tmp_path: Path,
    case: str,
    expected_count: int,
    expected_exit: int,
) -> None:
    directory = os.environ.get("SCORE_CODEQL_DEMONSTRATION_REQUEST_DIRECTORY")
    if not directory:
        pytest.skip("select genuine fixed CodeQL demonstration requests explicitly")
    selected = Path(directory) / f"codeql-demonstration-{case}.yaml"
    output_dir = Path(os.environ.get("SCORE_CODEQL_DEMONSTRATION_OUTPUT_DIRECTORY", str(tmp_path)))
    out = output_dir / f"codeql-public-demonstration-{case}.json"
    assert not out.exists(), "retain earlier measurements; select a fresh output directory"
    assert (
        main(
            ["quality", "run", "--adapter", "codeql", "--request", str(selected), "--out", str(out)]
        )
        == expected_exit
    )
    record = json.loads(out.read_bytes())
    verify_digest(record, "/record")
    verify_digest(record["prerequisite_inventory"], "/prerequisite_inventory")
    assert record["result_count"] == expected_count
    assert record["outcome"] == ("findings" if expected_count else "completed")
    assert record["execution_gaps"] == []
    assert record["analysis_executed"] and record["native_reporting_executed"]
    assert record["source_integrity"] == "unchanged"
    assert record["extraction"]["adequacy"] == "adequate"
    assert record["extraction"]["extracted_units"] == ["check.cpp"]
    assert record["extraction"]["errors"] == []
    assert record["accepted_claims"] == 0
    assert record["assurance_eligibility"] == "not_eligible"
    assert record["engineering_readiness"] == "not_evaluated"
    artifacts = {row["id"]: row for row in record["artifacts"]}
    reports = {name for name in artifacts if name.startswith("native-reports/")}
    assert len(reports) == 4 and all(artifacts[name]["bytes"] > 100 for name in reports)
    assert not any(row["truncated"] for row in artifacts.values())
    original = json.loads(base64.b64decode(artifacts["results.sarif"]["base64"]))
    results = original["runs"][0]["results"]
    assert [row["native_record"] for row in record["diagnostics"]] == results
    assert record["report_patch"]["native_patch_qualification"] == "unknown"
    assert (
        next(p for p in record["phases"] if p["name"] == "report-patch:original-check")["exit_code"]
        == 128
    )
    assert all(
        p["exit_code"] == 0 for p in record["phases"] if p["name"] != "report-patch:original-check"
    )


def native_request() -> Path:
    value = os.environ.get("SCORE_CODEQL_PREREQUISITE_REQUEST")
    if not value:
        pytest.skip(
            "select SCORE_CODEQL_PREREQUISITE_REQUEST; eligible CodeQL analysis stays unmet"
        )
    return Path(value)


def test_actual_installed_sources_and_libraries_remain_blocked() -> None:
    code, record, _, _ = codeql.capabilities(native_request())
    assert code == 1 and record["accepted_claims"] == 0
    assert record["source_inspection"]["origin"] == "locked_source_selection"
    assert record["source_inspection"]["source_build"]["state"] == "source_trees_equal"
    pack = record["pack_inspection"]
    assert pack["included_source_state"] == "matched" and pack["included_source_count"] == 233
    assert pack["library_state"] == "matched" and len(pack["libraries"]) == 13
    assert pack["compiled_artifact_provenance"] == "unverified"
    assert record["capability"]["installation_state"] == "bytes_verified"
    assert record["analysis_executed"] is False
    assert "CODEQL_ELIGIBILITY_UNKNOWN" in record["gaps"]
    assert "NATIVE_REPORTING_UNEXECUTED" in record["gaps"]
    assert record["engineering_readiness"] == "not_evaluated"
    assert all(phase["argv"][0] == "/usr/bin/git" for phase in record["phases"])


def test_actual_selected_blocked_run_preserves_component_and_unmet_extraction(
    tmp_path: Path,
) -> None:
    selected = load_inputs(native_request(), "capabilities", "codeql").request
    path = request(tmp_path)
    run_request = json.loads(path.read_bytes())
    for key in (
        "profile",
        "toolchain",
        "config",
        "timeout_seconds",
        "output_limit_bytes",
        "protected_roots",
    ):
        run_request[key] = selected[key]
    run_request["kind"] = "quality_codeql_run_request"
    path.write_text(json.dumps(run_request))
    source = tmp_path / "component/check.cpp"
    before = source.read_bytes()
    code, record, _, _ = codeql.run(path)
    assert code == 1 and source.read_bytes() == before
    assert record["analysis_executed"] is False
    assert record["extraction"]["adequacy"] == "unknown"
    assert record["processed_units"] == record["diagnostics"] == []
    assert record["accepted_claims"] == 0


def test_synthetic_import_preserves_actual_installed_context_without_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Synthetic finding + real inspection is unresolved; no genuine CodeQL evidence exists."""
    from tests.quality_codeql_disposition_support import controls, packet_request
    from tests.quality_disposition_support import change_request, write

    actual = load_inputs(native_request(), "capabilities", "codeql").request
    disposition, original, current = controls(tmp_path)
    selected = json.loads(current.read_bytes())
    for key in (
        "profile",
        "toolchain",
        "config",
        "timeout_seconds",
        "output_limit_bytes",
        "protected_roots",
    ):
        selected[key] = actual[key]
    write(current, selected)
    change_request(disposition, current={"adapter": "codeql", "request": ref(current)})
    code, review, _, _ = dispositions.review(disposition)
    assert code == 1 and review["state"] == "stale"
    assert review["subject"]["origin_class"] == "fixture"
    assert review["inspection"]["pack_inspection"]["included_source_count"] == 233
    assert review["inspection"]["analysis_executed"] is False
    assert "QUERY_PACK_CHANGED" in review["reasons"]
    assert "CODEQL_ELIGIBILITY_UNKNOWN" in review["reasons"]
    _, portable, _, _ = packet.packet(packet_request(tmp_path, disposition, original, review))
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("offline host read"))
    monkeypatch.setattr(Path, "stat", lambda *a, **k: pytest.fail("offline host probe"))
    assert packet.verify_packet(portable)["reproduced"]
