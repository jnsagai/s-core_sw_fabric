"""Independent evaluation cannot transform structural closure into compliance."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import assessment
from tests.quality_assessment_support import assessment_request
from tests.quality_import_support import write_json


@pytest.mark.parametrize("domain", ["fixture_contract", "production"])
def test_complete_packet_with_missing_engineering_obligations_is_blocked(
    tmp_path: Path, domain: str
) -> None:
    path = assessment_request(tmp_path, assurance_domain=domain)
    code, record, _, _ = assessment.assess(path)
    assert code == 1 and record["outcome"] == "blocked"
    assert record["packet_replay"]["reproduced"]
    assert record["accepted_claims"] == 0
    assert record["engineering_readiness"] == "not_evaluated"
    assert "RULE_MAPPING_UNKNOWN" in record["gaps"]
    assert "PRIMARY_EXECUTION_UNAVAILABLE" in record["gaps"]
    assert "MANUAL_REVIEW_PENDING" in record["gaps"]
    assert "PRODUCTION_AUTHORITY_UNAVAILABLE" in record["gaps"]
    assert record["denominator"] == 2
    assert {r["id"] for r in record["obligations"] if r["kind"] == "guideline"} == {
        "fixture-guideline-a",
        "fixture-guideline-b",
    }
    assert assessment.verify_assessment(record)["reproduced"]


def test_offline_source_freshness_remains_unknown(tmp_path: Path) -> None:
    path = assessment_request(tmp_path, current_baseline=None)
    _, record, _, _ = assessment.assess(path)
    for original in tmp_path.rglob("*"):
        if original.is_file():
            original.unlink()
    assert record["current_baseline"] is None
    assert "BASELINE_FRESHNESS_UNKNOWN" in record["gaps"]
    assert assessment.verify_assessment(record)["reproduced"]


def test_explicit_current_source_change_stales_packet(tmp_path: Path) -> None:
    path = assessment_request(tmp_path)
    current = json.loads(path.read_text())
    bp = Path(current["current_baseline"]["path"])
    b = json.loads(bp.read_text())
    source = tmp_path / "source/check.cpp"
    source.write_text("int main() { return 1; }\n")
    from tests.quality_support import ref

    b["files"] = [{"path": "check.cpp", "sha256": ref(source)["sha256"]}]
    current["current_baseline"] = write_json(bp, seal(b))
    write_json(path, current)
    _, record, _, _ = assessment.assess(path)
    assert "BASELINE_DRIFT:files" in record["gaps"]
    assert record["outcome"] == "blocked"
    assert assessment.verify_assessment(record)["reproduced"]


@pytest.mark.parametrize("mutation", ["gap", "denominator", "origin", "obligations", "claims"])
def test_resealed_assessment_tampering_fails_independent_replay(
    tmp_path: Path, mutation: str
) -> None:
    _, record, _, _ = assessment.assess(assessment_request(tmp_path))
    value = copy.deepcopy(record)
    if mutation == "gap":
        value["gaps"] = []
    elif mutation == "denominator":
        value["denominator"] = 0
    elif mutation == "origin":
        value["origin"] = "protected"
    elif mutation == "obligations":
        value["obligations"] = []
    else:
        value["accepted_claims"] = 1
    assert not assessment.verify_assessment(seal(value))["reproduced"]


def test_unreproduced_packet_refuses_and_preserves_output(tmp_path: Path) -> None:
    path = assessment_request(tmp_path)
    request = json.loads(path.read_text())
    pp = Path(request["packet"]["path"])
    original = json.loads(pp.read_text())
    original["questions"][0]["answer"] = "approved"
    request["packet"] = write_json(pp, seal(original))
    write_json(path, request)
    out = tmp_path / "out.json"
    out.write_text("prior output")
    assert main(["quality", "assess", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_text() == "prior output"


def test_assessment_output_cannot_replace_any_packet_original(tmp_path: Path) -> None:
    path = assessment_request(tmp_path, current_baseline=None)
    with pytest.raises(InputError):
        assessment.assess(path, tmp_path / "NOTICE.txt")


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": True},
        {"as_of": "2026-12-01"},
        {"assurance_domain": "auto"},
        {"extra": "unreviewed"},
        {"decisions": [{}] * 21},
    ],
)
def test_malformed_controls_preserve_existing_output(
    tmp_path: Path, change: dict[str, object]
) -> None:
    path = assessment_request(tmp_path)
    request = json.loads(path.read_text())
    request.update(change)
    write_json(path, request)
    out = tmp_path / "out.json"
    out.write_text("old")
    assert main(["quality", "assess", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_text() == "old"


def test_publication_refreezes_selected_current_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = assessment_request(tmp_path)
    original = assessment.evaluate

    def changed(*args: object, **kwargs: object) -> object:
        result = original(*args, **kwargs)
        (tmp_path / "source/check.cpp").write_text("late drift")
        return result

    monkeypatch.setattr(assessment, "evaluate", changed)
    out = tmp_path / "out.json"
    out.write_text("prior evidence")
    assert main(["quality", "assess", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_text() == "prior evidence"


def test_current_source_tampering_cannot_be_hidden_in_resealed_output(tmp_path: Path) -> None:
    _, original, _, _ = assessment.assess(assessment_request(tmp_path))
    value = copy.deepcopy(original)
    value["current_baseline"]["sources"][0]["raw"]["base64"] = ""
    assert not assessment.verify_assessment(seal(value))["reproduced"]


def test_unknown_denominator_remains_null_in_assessment(tmp_path: Path) -> None:
    from score_sw_fabric.quality import coverage, packet
    from tests.quality_coverage_support import change_mapping
    from tests.quality_support import ref

    path = assessment_request(tmp_path)
    current = json.loads(path.read_text())
    packet_selection = tmp_path / "packet-request.json"
    selected = json.loads(packet_selection.read_text())
    coverage_request = Path(selected["coverage"]["request"]["path"])
    change_mapping(coverage_request, expected_guidelines=None, rows=[])
    _, matrix, _, _ = coverage.measure(coverage_request)
    selected["coverage"] = {
        "request": ref(coverage_request),
        "report": write_json(tmp_path / "matrix.json", matrix),
    }
    write_json(packet_selection, selected)
    _, original, _, _ = packet.packet(packet_selection)
    current["packet"] = write_json(tmp_path / "packet.json", original)
    write_json(path, current)
    _, record, _, _ = assessment.assess(path)
    assert record["denominator"] is None
    assert "GUIDELINE_DENOMINATOR_UNKNOWN" in record["gaps"]
    assert record["outcome"] == "blocked"
