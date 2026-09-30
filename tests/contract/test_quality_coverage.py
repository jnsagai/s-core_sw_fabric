"""Declared expectations persist; clean tools cannot erase unknown or human obligations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import coverage
from tests.quality_coverage_support import change_mapping, controls
from tests.quality_import_support import write_json
from tests.quality_support import ref


def cells(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["guideline_id"]: row for row in result["rows"]}


def test_declared_rows_findings_and_manual_reviews_remain(tmp_path: Path) -> None:
    path = controls(tmp_path)
    code, result, _, _ = coverage.measure(path)
    assert code == 1 and result["denominator"] == 2
    assert cells(result)["fixture-guideline-a"]["state"] == "findings_open"
    assert cells(result)["fixture-guideline-b"]["state"] == "pending_manual"
    assert result["accepted_claims"] == 0 and result["assurance_eligibility"] == "not_eligible"


def test_unknown_denominator_retains_supplied_rows(tmp_path: Path) -> None:
    path = controls(tmp_path, clean=True)
    change_mapping(path, expected_guidelines=None)
    _, result, _, _ = coverage.measure(path)
    assert result["scope_state"] == "unknown" and result["denominator"] is None
    assert len(result["rows"]) == 2 and "GUIDELINE_DENOMINATOR_UNKNOWN" in result["gaps"]


def test_missing_declared_row_materializes_unknown_cell(tmp_path: Path) -> None:
    path = controls(tmp_path)
    m = json.loads((tmp_path / "mapping.json").read_text())
    change_mapping(path, rows=m["rows"][:1])
    _, result, _, _ = coverage.measure(path)
    row = cells(result)["fixture-guideline-b"]
    assert row["state"] == "unknown" and "MAPPING_ROW_MISSING" in row["reasons"]
    assert result["denominator"] == 2


@pytest.mark.parametrize("applicability", ["unknown", "not_applicable"])
def test_unknown_and_excluded_expectations_do_not_shrink_denominator(
    tmp_path: Path,
    applicability: str,
) -> None:
    path = controls(tmp_path, clean=True)
    m = json.loads((tmp_path / "mapping.json").read_text())
    m["expected_guidelines"][0]["applicability"] = applicability
    change_mapping(path, expected_guidelines=m["expected_guidelines"])
    _, result, _, _ = coverage.measure(path)
    assert result["denominator"] == 2
    assert cells(result)["fixture-guideline-a"]["state"] == (
        "unknown" if applicability == "unknown" else "excluded_pending_review"
    )


@pytest.mark.parametrize("kind", ["manual", "audit", "unsupported"])
def test_all_required_nonautomatic_mechanisms_remain_visible(tmp_path: Path, kind: str) -> None:
    path = controls(tmp_path, clean=True)
    m = json.loads((tmp_path / "mapping.json").read_text())
    row = m["rows"][1]["mechanisms"][0]
    row.update(kind=kind, automation_class=kind)
    change_mapping(path, rows=m["rows"])
    _, result, _, _ = coverage.measure(path)
    assert cells(result)["fixture-guideline-b"]["state"] == (
        "unsupported" if kind == "unsupported" else "pending_manual"
    )


def test_clean_codeql_fixture_never_supplies_primary_execution(tmp_path: Path) -> None:
    _, result, _, _ = coverage.measure(controls(tmp_path, clean=True))
    row = cells(result)["fixture-guideline-a"]
    assert row["state"] != "covered" and "CODEQL_ELIGIBILITY_UNKNOWN" in result["gaps"]
    assert result["accepted_claims"] == 0


def test_suppressed_finding_cannot_be_cleared_by_mapping(tmp_path: Path) -> None:
    from score_sw_fabric.quality import imports
    from tests.quality_import_support import sarif, selection

    path = controls(tmp_path)
    native = sarif()
    native["runs"][0]["results"][0]["suppressions"] = [{"kind": "inSource", "status": "accepted"}]
    selected = selection(tmp_path, native=native)
    _, report, _, _ = imports.import_outputs(selected)
    request = json.loads(path.read_text())
    request["baseline"] = json.loads(selected.read_text())["baseline"]
    request["analyses"] = [
        {"request": ref(selected), "report": write_json(tmp_path / "report.json", report)}
    ]
    write_json(path, request)
    _, result, _, _ = coverage.measure(path)
    row = cells(result)["fixture-guideline-a"]
    assert row["state"] == "findings_open" and row["findings"]


def test_changed_applicability_retains_prior_declaration(tmp_path: Path) -> None:
    path = controls(tmp_path, clean=True)
    request = json.loads(path.read_text())
    old = json.loads((tmp_path / "mapping.json").read_text())
    request["previous_manifest"] = write_json(tmp_path / "previous.json", old)
    write_json(path, request)
    old["expected_guidelines"][0]["applicability"] = "not_applicable"
    change_mapping(path, expected_guidelines=old["expected_guidelines"])
    _, result, _, _ = coverage.measure(path)
    assert result["previous"]["manifest"]["expected_guidelines"][0]["applicability"] == "applicable"
    assert any(c["guideline_id"] == "fixture-guideline-a" for c in result["changes"])


@pytest.mark.parametrize("mutation", ["category", "source", "scope", "extra_row", "duplicate"])
def test_invalid_or_ungrounded_mapping_is_refused_or_unknown(tmp_path: Path, mutation: str) -> None:
    path = controls(tmp_path, clean=True)
    m = json.loads((tmp_path / "mapping.json").read_text())
    if mutation == "category":
        m["expected_guidelines"][0]["native_category"] = None
        change_mapping(path, expected_guidelines=m["expected_guidelines"])
        _, result, _, _ = coverage.measure(path)
        assert cells(result)["fixture-guideline-a"]["state"] == "unknown"
        return
    if mutation == "source":
        m["rows"][0]["source_ids"] = ["missing-source"]
    elif mutation == "scope":
        m["scope"]["component"] = "another-component"
    elif mutation == "extra_row":
        m["rows"][0]["guideline_id"] = "unlisted-guideline"
    else:
        m["rows"].append(m["rows"][0])
    change_mapping(path, **{key: m[key] for key in ("rows", "scope")})
    with pytest.raises(InputError):
        coverage.measure(path)


def test_tampered_resealed_report_cannot_assert_clean(tmp_path: Path) -> None:
    path = controls(tmp_path)
    request = json.loads(path.read_text())
    p = Path(request["analyses"][0]["report"]["path"])
    report = json.loads(p.read_text())
    report["findings"] = []
    request["analyses"][0]["report"] = write_json(p, seal(report))
    write_json(path, request)
    with pytest.raises(InputError):
        coverage.measure(path)


@pytest.mark.parametrize("output", ["request", "manifest", "source", "report", "frozen_file"])
def test_output_cannot_overwrite_selected_inputs(tmp_path: Path, output: str) -> None:
    path = controls(tmp_path)
    target = {
        "request": path,
        "manifest": tmp_path / "mapping.json",
        "source": tmp_path / "guidelines.json",
        "report": tmp_path / "report.json",
        "frozen_file": tmp_path / "source/check.cpp",
    }[output]
    old = target.read_bytes()
    assert main(["quality", "coverage", "--request", str(path), "--out", str(target)]) == 2
    assert target.read_bytes() == old


@pytest.mark.parametrize("automation", ["partial", "audit"])
def test_partial_and_default_disabled_audit_require_manual_review(
    tmp_path: Path,
    automation: str,
) -> None:
    path = controls(tmp_path, clean=True)
    m = json.loads((tmp_path / "mapping.json").read_text())
    m["rows"][0]["mechanisms"][0].update(automation_class=automation, enabled=False)
    change_mapping(path, rows=m["rows"])
    _, result, _, _ = coverage.measure(path)
    row = cells(result)["fixture-guideline-a"]
    assert row["state"] == "pending_manual"
    assert "CHECK_NOT_SELECTED" in row["reasons"]


def test_unknown_scope_with_no_rows_does_not_invent_expectations(tmp_path: Path) -> None:
    path = controls(tmp_path, clean=True)
    change_mapping(path, expected_guidelines=None, source_refs=[], rows=[])
    request = json.loads(path.read_text())
    request["analyses"] = []
    write_json(path, request)
    _, result, _, _ = coverage.measure(path)
    assert result["denominator"] is None and not result["rows"]
    assert sum(result["counts"].values()) == 0


@pytest.mark.parametrize("which", ["source", "suite", "config"])
def test_current_frozen_baseline_drift_is_visible(tmp_path: Path, which: str) -> None:
    path = controls(tmp_path, clean=True)
    request = json.loads(path.read_text())
    baseline = json.loads(Path(request["baseline"]["path"]).read_text())
    if which == "source":
        source = tmp_path / "source/check.cpp"
        source.write_text("// changed source\nint main() { return 2; }\n")
        baseline["files"][0]["sha256"] = ref(source)["sha256"]
        # The historical analyzer selection keeps a separate, original frozen source copy.
        old_root = tmp_path / "historical"
        old_root.mkdir()
        (old_root / "check.cpp").write_text("// synthetic\nint main() { return 0; }\n")
        analysis_request = Path(request["analyses"][0]["request"]["path"])
        analysis = json.loads(analysis_request.read_text())
        old = json.loads(Path(analysis["baseline"]["path"]).read_text())
        old["root"] = str(old_root)
        analysis["baseline"] = write_json(tmp_path / "historical-baseline.json", seal(old))
        write_json(analysis_request, analysis)
        from score_sw_fabric.quality import imports

        _, report, _, _ = imports.import_outputs(analysis_request)
        request["analyses"][0] = {
            "request": ref(analysis_request),
            "report": write_json(tmp_path / "report.json", report),
        }
    elif which == "suite":
        baseline["identities"][0]["suite"]["sha256"] = "0" * 64
    else:
        baseline["identities"][0]["config_sha256"] = "0" * 64
    request["baseline"] = write_json(tmp_path / "current-baseline.json", seal(baseline))
    write_json(path, request)
    _, result, _, _ = coverage.measure(path)
    assert result["analyses"][0]["current"] is False
    assert any(g.startswith("BASELINE_DRIFT:") for g in result["gaps"])
    assert result["accepted_claims"] == 0


@pytest.mark.parametrize(
    "mutation", ["boolean_version", "bad_ref", "empty_set", "too_many", "bad_source"]
)
def test_malformed_inputs_refuse_before_publication(tmp_path: Path, mutation: str) -> None:
    path = controls(tmp_path)
    r = json.loads(path.read_text())
    if mutation == "boolean_version":
        r["schema_version"] = True
    elif mutation == "bad_ref":
        r["profile"] = {"sha256": "0" * 64}
    elif mutation == "too_many":
        r["analyses"] *= 21
    elif mutation == "empty_set":
        change_mapping(path, expected_guidelines=[])
        r = json.loads(path.read_text())
    else:
        source = tmp_path / "guidelines.json"
        value = json.loads(source.read_text())
        value["guideline_ids"] = ["unrelated-guideline"]
        write_json(source, value)
        m = json.loads((tmp_path / "mapping.json").read_text())
        m["source_refs"][0]["ref"] = ref(source)
        change_mapping(path, source_refs=m["source_refs"])
        r = json.loads(path.read_text())
    write_json(path, r)
    out = tmp_path / "matrix.json"
    out.write_text("previous")
    assert main(["quality", "coverage", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_text() == "previous"


def test_native_input_drift_during_measurement_preserves_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = controls(tmp_path)
    measure_cell = coverage._cell

    def drift(*args: Any, **kwargs: Any) -> Any:
        result = measure_cell(*args, **kwargs)
        (tmp_path / "analysis.sarif").write_text("{}")
        return result

    monkeypatch.setattr(coverage, "_cell", drift)
    out = tmp_path / "matrix.json"
    out.write_text("previous")
    assert main(["quality", "coverage", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_text() == "previous"


def test_failed_native_phases_and_filters_remain_named(tmp_path: Path) -> None:
    from score_sw_fabric.quality import imports
    from tests.quality_import_support import change_manifest

    path = controls(tmp_path, clean=True)
    request = json.loads(path.read_text())
    analysis_request = Path(request["analyses"][0]["request"]["path"])
    change_manifest(analysis_request, filtered_checks=["fixture/check"])
    _, report, _, _ = imports.import_outputs(analysis_request)
    request["analyses"][0] = {
        "request": ref(analysis_request),
        "report": write_json(tmp_path / "report.json", report),
    }
    write_json(path, request)
    _, result, _, _ = coverage.measure(path)
    assert "CHECK_CONFIGURATION_INCOMPLETE" in result["gaps"]
    assert all(row["state"] != "covered" for row in result["rows"])


def test_previous_source_cannot_be_overwritten(tmp_path: Path) -> None:
    path = controls(tmp_path)
    r = json.loads(path.read_text())
    old = json.loads((tmp_path / "mapping.json").read_text())
    source = tmp_path / "historical-guidelines.json"
    source.write_bytes((tmp_path / "guidelines.json").read_bytes())
    old["source_refs"][0]["ref"] = ref(source)
    r["previous_manifest"] = write_json(tmp_path / "previous.json", seal(old))
    write_json(path, r)
    frozen = source.read_bytes()
    assert main(["quality", "coverage", "--request", str(path), "--out", str(source)]) == 2
    assert source.read_bytes() == frozen
