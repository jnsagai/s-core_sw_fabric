"""Independent expected sets and inner failures cannot become clean import evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import digest, seal, verify_digest
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.imports import import_outputs
from tests.quality_import_support import change_manifest, sarif, selection
from tests.quality_support import ref


@pytest.mark.parametrize("expected,gap", [(None, "EXTRACTION_UNKNOWN"), ([], "EXTRACTION_EMPTY")])
def test_clean_sarif_unknown_or_empty_expectation(
    tmp_path: Path, expected: object, gap: str
) -> None:
    code, r, _, _ = import_outputs(selection(tmp_path, expected=expected, native=sarif([])))
    assert code == 1 and r["outcome"] == "incomplete"
    assert gap in r["gaps"] and r["extraction"]["adequacy"] != "adequate"


@pytest.mark.parametrize(
    "changes,gap",
    [
        ({"processed_units": [], "extracted_units": []}, "EXTRACTION_EMPTY"),
        ({"failed_queries": ["fixture/query"]}, "QUERY_FAILED"),
        ({"warnings": ["fixture extraction warning"]}, "EXTRACTION_WARNING"),
        ({"errors": ["fixture extraction error"]}, "EXTRACTION_ERROR"),
        ({"filtered_checks": ["fixture/check"]}, "CHECK_CONFIGURATION_INCOMPLETE"),
        (
            {
                "exclusions": [
                    {"unit": "check.cpp", "reason": "fixture exclusion", "justification": None}
                ]
            },
            "EXCLUSION_PENDING_REVIEW",
        ),
    ],
)
def test_inner_failures_block_zero_outer_exit(tmp_path: Path, changes: dict, gap: str) -> None:
    path = selection(tmp_path, native=sarif([]))
    change_manifest(path, **changes)
    code, r, _, _ = import_outputs(path)
    assert code == 1 and gap in r["gaps"] and r["outcome"] == "incomplete"


def test_failed_and_missing_report_phases_block_compliant_text(tmp_path: Path) -> None:
    path = selection(tmp_path, native=sarif([]))
    request = json.loads(path.read_text())
    manifest = json.loads(Path(request["extraction"]["path"]).read_text())
    phases = manifest["observations"][0]["phases"]
    phases[-1].update(exit_code=1, status="failed")
    change_manifest(path, phases=phases)
    code, r, _, _ = import_outputs(path)
    assert code == 1 and "PHASE_FAILED" in r["gaps"]
    assert r["extraction"]["adequacy"] == "incomplete"


def test_native_extracted_listing_cannot_be_replaced_by_declaration(tmp_path: Path) -> None:
    path = selection(tmp_path, native=sarif([]))
    report = tmp_path / "database_integrity_report.md"
    report.write_text(
        "# Database integrity report\n - 0 errors reported\n"
        " - 0 successfully analyzed files\n## Successfully extracted files\n"
    )
    req = json.loads(path.read_text())
    req["artifacts"][1]["ref"] = ref(report)
    path.write_text(json.dumps(req))
    code, r, _, _ = import_outputs(path)
    assert code == 1 and "NATIVE_EXTRACTION_MISMATCH" in r["gaps"]


def test_structurally_complete_clean_import_is_still_unverified(tmp_path: Path) -> None:
    code, r, _, _ = import_outputs(
        selection(tmp_path, native=sarif([]), origin="imported_unverified")
    )
    assert code == 0 and r["extraction"]["adequacy"] == "adequate"
    assert r["origin"] == "imported_unverified" and r["engineering_readiness"] == "not_evaluated"
    assert "RULE_MAPPING_UNKNOWN" in r["gaps"]
    verify_digest(r["baseline"], "/snapshot")


def test_partial_scope_names_missing_unit(tmp_path: Path) -> None:
    path = selection(tmp_path, native=sarif([]))
    request = json.loads(path.read_text())
    baseline_path = Path(request["baseline"]["path"])
    baseline = json.loads(baseline_path.read_text())
    extra = tmp_path / "source/other.cpp"
    extra.write_text("// Synthetic second translation unit\n")
    baseline["files"].append({"path": "other.cpp", "sha256": ref(extra)["sha256"]})
    baseline["expected_units"].append("other.cpp")
    baseline_path.write_text(json.dumps(seal(baseline)))
    request["baseline"] = ref(baseline_path)
    source_digest = digest({k: baseline[k] for k in ("component", "files", "expected_units")})
    manifest_path = Path(request["extraction"]["path"])
    manifest = json.loads(manifest_path.read_text())
    manifest["source_digest"] = source_digest
    manifest_path.write_text(json.dumps(seal(manifest)))
    request["extraction"] = ref(manifest_path)
    for artifact in request["artifacts"]:
        artifact["bindings"]["source_digest"] = source_digest
    path.write_text(json.dumps(request))
    code, record, _, _ = import_outputs(path)
    assert code == 1 and "EXTRACTION_PARTIAL" in record["gaps"]
    assert record["extraction"]["observations"][0]["missing_units"] == ["other.cpp"]


def test_missing_report_cannot_be_cleared_by_required_list(tmp_path: Path) -> None:
    path = selection(tmp_path, native=sarif([]))
    request = json.loads(path.read_text())
    absent = "guideline_compliance_summary.md"
    request["artifacts"] = [a for a in request["artifacts"] if a["id"] != absent]
    path.write_text(json.dumps(request))
    manifest = json.loads(Path(request["extraction"]["path"]).read_text())
    for phase in manifest["observations"][0]["phases"]:
        phase["artifacts"] = [name for name in phase["artifacts"] if name != absent]
    change_manifest(path, required_reports=[], phases=manifest["observations"][0]["phases"])
    code, record, _, _ = import_outputs(path)
    assert code == 1 and "REPORT_MISSING" in record["gaps"]


@pytest.mark.parametrize("field,value", [("exit_code", True), ("status", []), ("timed_out", 0)])
def test_phase_types_refused(tmp_path: Path, field: str, value: object) -> None:
    path = selection(tmp_path)
    request = json.loads(path.read_text())
    manifest = json.loads(Path(request["extraction"]["path"]).read_text())
    phases = manifest["observations"][0]["phases"]
    phases[0][field] = value
    change_manifest(path, phases=phases)
    with pytest.raises(InputError):
        import_outputs(path)
