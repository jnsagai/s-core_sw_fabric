"""Genuine complementary check observations remain ineligible guideline declarations."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from score_sw_fabric.assurance.models import digest
from score_sw_fabric.cli import main
from score_sw_fabric.quality import coverage, imports, runner
from tests.quality_coverage_support import change_mapping, controls
from tests.quality_import_support import from_local_run, write_json
from tests.quality_support import ROOT, ref, request


def selected_local(tmp: Path) -> Path:
    source = tmp / "component"
    source.mkdir()
    shutil.copy2(ROOT / "tests/fixtures/quality/corrected/check.cpp", source / "check.cpp")
    run_request = request(tmp, component="fixture_component")
    _, local, _, _ = runner.run(run_request)
    assert local["extraction"]["adequacy"] == "adequate" and not local["diagnostics"]
    imported = from_local_run(tmp, "clang-tidy", local, source)
    _, report, _, _ = imports.import_outputs(imported)
    # Seed only the synthetic mapping/control records, then select genuine local originals.
    fixture = tmp / "fixture"
    fixture.mkdir()
    path = controls(fixture, clean=True)
    selected = json.loads(imported.read_text())
    r = json.loads(path.read_text())
    r.update(
        profile=selected["profile"],
        baseline=selected["baseline"],
        analyses=[
            {
                "request": ref(imported),
                "report": write_json(tmp / "local-import.json", report),
            }
        ],
    )
    write_json(path, r)
    m = json.loads((fixture / "mapping.json").read_text())
    mechanism = m["rows"][0]["mechanisms"][0]
    mechanism.update(
        tool="clang-tidy",
        native_id="clang-analyzer-core.NullDereference",
        identity_digest=digest(report["identities"][0]),
    )
    m["rows"][0]["expected_evidence"] = ["original-analysis-run"]
    change_mapping(path, rows=m["rows"])
    return path


def test_genuine_clean_selection_covers_only_declared_automatic_mechanism(tmp_path: Path) -> None:
    path = selected_local(tmp_path)
    code, result, _, _ = coverage.measure(path)
    assert code == 1 and result["rows"][0]["state"] == "covered"
    assert result["rows"][1]["state"] == "pending_manual"
    assert result["counts"]["covered"] == 1 and result["accepted_claims"] == 0
    assert "RULE_MAPPING_UNKNOWN" in result["gaps"]
    assert "PRODUCTION_AUTHORITY_UNAVAILABLE" in result["gaps"]
    assert result["analyses"][0]["report"]["origin"] == "imported_unverified"


def test_cli_stable_portable_source_closure_and_disabled_check(tmp_path: Path) -> None:
    path = selected_local(tmp_path)
    out = tmp_path / "matrix.json"
    command = ["quality", "coverage", "--request", str(path), "--out", str(out), "--json"]
    assert main(command) == 1
    original = out.read_bytes()
    assert main(command) == 1 and out.read_bytes() == original
    saved = json.loads(original)
    mapping = json.loads(Path(json.loads(path.read_text())["manifest"]["path"]).read_text())
    mapping["rows"][0]["mechanisms"][0]["enabled"] = False
    change_mapping(path, rows=mapping["rows"])
    assert main(command) == 1
    assert json.loads(out.read_text())["rows"][0]["state"] == "unsupported"
    for p in (tmp_path / "component").iterdir():
        p.unlink()
    assert saved["sources"][0]["record"]["guideline_ids"]
    assert saved["analyses"][0]["report"]["artifacts"]
    assert saved["rows"][0]["state"] == "covered"
    assert saved["engineering_readiness"] == "not_evaluated"


def test_missing_required_artifact_blocks_automatic_coverage(tmp_path: Path) -> None:
    path = selected_local(tmp_path)
    m = json.loads(Path(json.loads(path.read_text())["manifest"]["path"]).read_text())
    m["rows"][0]["expected_evidence"].append("missing-required-report")
    change_mapping(path, rows=m["rows"])
    _, result, _, _ = coverage.measure(path)
    assert result["rows"][0]["state"] == "unknown"
    assert "EXPECTED_EVIDENCE_MISSING" in result["rows"][0]["reasons"]
