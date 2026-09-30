"""Portable closure refuses drift and never promotes local or fixture authority."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import packet
from tests.quality_import_support import write_json
from tests.quality_packet_support import packet_request


def test_packet_retains_raw_sources_origins_and_pending_questions(tmp_path: Path) -> None:
    request = packet_request(tmp_path)
    status, record, _, _ = packet.packet(request)
    assert status == 0
    assert record["packet_state"] == "complete"
    assert record["accepted_claims"] == 0
    assert record["engineering_readiness"] == "not_evaluated"
    assert record["assurance_eligibility"] == "not_eligible"
    assert "fixture" in record["origins"]
    assert "CODEQL_ELIGIBILITY_UNKNOWN" in record["gaps"]
    assert all(q["answer"] == "pending_human" for q in record["questions"])
    assert record["sources"][0]["files"][0]["path"] == "check.cpp"
    assert len(record["analyses"][0]["report"]["artifacts"]) == 5
    assert packet.verify_packet(record)["reproduced"]


def test_offline_verification_after_originals_removed(tmp_path: Path) -> None:
    request = packet_request(tmp_path)
    _, record, _, _ = packet.packet(request)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.unlink()
    assert packet.verify_packet(record)["reproduced"]


@pytest.mark.parametrize("field", ["source_snapshots", "notices"])
def test_missing_portable_closure_publishes_incomplete(tmp_path: Path, field: str) -> None:
    request = packet_request(tmp_path, **{field: []})
    status, record, _, _ = packet.packet(request)
    assert status == 1
    assert record["packet_state"] == "incomplete"
    assert packet.verify_packet(record)["reproduced"]


@pytest.mark.parametrize(
    "mutation", ["source", "archive", "question", "origin", "finding", "notice"]
)
def test_resealed_tampering_does_not_reproduce(tmp_path: Path, mutation: str) -> None:
    _, record, _, _ = packet.packet(packet_request(tmp_path))
    value = copy.deepcopy(record)
    if mutation == "source":
        value["sources"][0]["files"][0]["sha256"] = "0" * 64
    elif mutation == "archive":
        value["files"][0]["raw"]["base64"] = ""
    elif mutation == "question":
        value["questions"][0]["answer"] = "approved"
    elif mutation == "origin":
        value["analyses"][0]["report"]["origin"] = "protected"
    elif mutation == "finding":
        value["analyses"][0]["report"]["findings"] = []
    else:
        value["notices"][0]["license"] = "Changed"
    assert not packet.verify_packet(seal(value))["reproduced"]


def test_changed_selected_source_refuses_packet(tmp_path: Path) -> None:
    request = packet_request(tmp_path)
    (tmp_path / "source/check.cpp").write_text("changed")
    with pytest.raises(InputError):
        packet.packet(request)


@pytest.mark.parametrize(
    "field,value", [("schema_version", True), ("extra", None), ("analyses", "bad")]
)
def test_strict_controls(tmp_path: Path, field: str, value: object) -> None:
    request = packet_request(tmp_path)
    record = json.loads(request.read_text())
    record[field] = value
    write_json(request, record)
    with pytest.raises(InputError):
        packet.packet(request)


def test_output_cannot_overwrite_sources_or_notice(tmp_path: Path) -> None:
    request = packet_request(tmp_path)
    for target in (tmp_path / "source/check.cpp", tmp_path / "NOTICE.txt"):
        old = target.read_bytes()
        with pytest.raises(InputError):
            packet.packet(request, target)
        assert target.read_bytes() == old


def test_notice_must_associate_every_selected_native_source_and_tool(tmp_path: Path) -> None:
    path = packet_request(tmp_path)
    request = json.loads(path.read_text())
    request["notices"][0]["applies_to"] = ["tool:codeql"]
    write_json(path, request)
    status, record, _, _ = packet.packet(path)
    assert status == 1
    assert "LICENSE_NOTICE_MISSING:native:clang_tidy" in record["gaps"]
    assert packet.verify_packet(record)["reproduced"]


def test_offline_verifier_never_uses_host_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, record, _, _ = packet.packet(packet_request(tmp_path))
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("offline host file read"))
    monkeypatch.setattr(Path, "stat", lambda *a, **k: pytest.fail("offline host path probe"))
    assert packet.verify_packet(record)["reproduced"]


def test_no_coverage_keeps_unknown_denominator(tmp_path: Path) -> None:
    path = packet_request(tmp_path)
    request = json.loads(path.read_text())
    coverage_request = json.loads(Path(request["coverage"]["request"]["path"]).read_text())
    request["coverage"] = None
    request["analyses"] = coverage_request["analyses"]
    write_json(path, request)
    status, record, _, _ = packet.packet(path)
    assert status == 0 and record["coverage"] is None
    assert "GUIDELINE_DENOMINATOR_UNKNOWN" in record["gaps"]
    assert packet.verify_packet(record)["reproduced"]


def test_missing_original_report_does_not_substitute_normalized_findings(tmp_path: Path) -> None:
    path = packet_request(tmp_path)
    (tmp_path / "analysis.sarif").unlink()
    with pytest.raises(InputError):
        packet.packet(path)


def test_archive_duplicate_extra_and_unsafe_labels_fail(tmp_path: Path) -> None:
    _, original, _, _ = packet.packet(packet_request(tmp_path))
    for change in ("duplicate", "extra", "unsafe"):
        record = copy.deepcopy(original)
        if change == "duplicate":
            record["files"].append(record["files"][0])
        elif change == "extra":
            entry = copy.deepcopy(record["files"][0])
            entry["path"] = "/unselected/not-opened"
            record["files"].append(entry)
        else:
            record["files"][0]["path"] = "/etc/../etc/passwd"
        assert not packet.verify_packet(seal(record))["reproduced"]


def test_prior_declaration_source_bytes_and_changes_are_portable(tmp_path: Path) -> None:
    from score_sw_fabric.quality import coverage
    from tests.quality_coverage_support import change_mapping
    from tests.quality_support import ref

    path = packet_request(tmp_path)
    request = json.loads(path.read_text())
    selected_path = Path(request["coverage"]["request"]["path"])
    selected = json.loads(selected_path.read_text())
    prior = json.loads(Path(selected["manifest"]["path"]).read_text())
    selected["previous_manifest"] = write_json(tmp_path / "prior.json", prior)
    write_json(selected_path, selected)
    changed = copy.deepcopy(prior["expected_guidelines"])
    changed[0]["applicability"] = "not_applicable"
    change_mapping(selected_path, expected_guidelines=changed)
    _, matrix, _, _ = coverage.measure(selected_path)
    request["coverage"] = {
        "request": ref(selected_path),
        "report": write_json(tmp_path / "matrix.json", matrix),
    }
    write_json(path, request)
    _, result, _, _ = packet.packet(path)
    assert result["coverage"]["report"]["changes"]
    assert packet.verify_packet(result)["reproduced"]


def test_source_drift_during_publication_preserves_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.cli import main
    from score_sw_fabric.quality.packet_models import Archive

    request = packet_request(tmp_path)
    out = tmp_path / "out.json"
    out.write_text("prior evidence")
    original = Archive.recheck

    def changed(archive: Archive) -> None:
        (tmp_path / "source/check.cpp").write_text("late source drift")
        original(archive)

    monkeypatch.setattr(Archive, "recheck", changed)
    assert main(["quality", "packet", "--request", str(request), "--out", str(out)]) == 2
    assert out.read_text() == "prior evidence"


def test_missing_snapshot_protects_current_source_directory(tmp_path: Path) -> None:
    request = packet_request(tmp_path, source_snapshots=[])
    with pytest.raises(InputError):
        packet.packet(request, tmp_path / "source/new-file.json")
