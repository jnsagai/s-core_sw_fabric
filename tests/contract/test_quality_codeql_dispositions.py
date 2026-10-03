"""Imported CodeQL context and portable proposals never substitute for analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import decisions, dispositions, packet
from tests.quality_codeql_disposition_support import controls, packet_request
from tests.quality_disposition_support import change_draft, change_request, write
from tests.quality_support import ref


@pytest.mark.parametrize("kind", ["correction", "false_positive", "deviation", "suppression"])
def test_matching_context_stays_open_or_pending_without_analysis(tmp_path: Path, kind: str) -> None:
    path, _, _ = controls(tmp_path)
    change_draft(path, requested_kind=kind)
    code, review, _, _ = dispositions.review(path)
    assert code == 1 and review["state"] == ("open" if kind == "correction" else "pending_review")
    assert review["kind"] == "quality_codeql_disposition_review"
    assert review["inspection"]["analysis_executed"] is False
    assert review["inspection"]["baseline"] == review["current_baseline"]
    assert review["fresh_run"] is None and review["origin"] == "local_unprotected_inspection"
    assert set(review["inspection"]["gaps"]).issubset(review["reasons"])
    assert not (tmp_path / "never-run-cli-marker").exists()


@pytest.mark.parametrize(
    "mismatch,reason",
    [
        ("tool", "TOOL_CHANGED"),
        ("config", "CONFIGURATION_CHANGED"),
        ("pack", "QUERY_PACK_CHANGED"),
        ("suite", "QUERY_SUITE_CHANGED"),
        ("library", "QUERY_LIBRARIES_CHANGED"),
    ],
)
def test_imported_native_identity_mismatch_is_stale(
    tmp_path: Path, mismatch: str, reason: str
) -> None:
    path, _, _ = controls(tmp_path, mismatch=mismatch)
    _, review, _, _ = dispositions.review(path)
    assert review["state"] == "stale" and reason in review["reasons"]


def test_changed_source_cannot_unlock_codeql_correction(tmp_path: Path) -> None:
    path, _, current = controls(tmp_path)
    source = tmp_path / "component/check.cpp"
    source.write_text("// Changed fixture source; no CodeQL analysis\nint main() { return 0; }\n")
    selected = json.loads(current.read_bytes())
    selected["files"] = [dict(ref(source), path="check.cpp")]
    write(current, selected)
    change_request(
        path, current={"adapter": "codeql", "request": ref(current)}, action="check_correction"
    )
    _, review, _, _ = dispositions.review(path)
    assert review["state"] == "blocked"
    assert "FRESH_CODEQL_ANALYSIS_REQUIRED" in review["reasons"]
    assert review["fresh_run"] is None


def test_prior_scope_stales_when_compiled_pack_changes(tmp_path: Path) -> None:
    path, _, _ = controls(tmp_path)
    _, initial, _, _ = dispositions.review(path)
    previous = tmp_path / "initial-review.json"
    write(previous, initial)
    (tmp_path / "fixture-pack/changed-compiled-artifact.bqrs").write_bytes(b"synthetic bytes")
    change_request(path, previous=ref(previous))
    _, revised, _, _ = dispositions.review(path)
    assert revised["revision"] == 2 and revised["previous"]["digest"] == initial["digest"]
    assert revised["state"] == "stale" and "QUERY_PACK_CHANGED" in revised["reasons"]
    assert json.loads(previous.read_bytes()) == initial


def test_packet_retains_context_history_and_replays_without_host_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, original, _ = controls(tmp_path)
    change_draft(path, requested_kind="false_positive")
    _, review, _, _ = dispositions.review(path)
    request = packet_request(tmp_path, path, original, review)
    _, portable, _, _ = packet.packet(request)
    assert "CODEQL_EXECUTION_UNIMPLEMENTED" in portable["gaps"]
    assert portable["accepted_claims"] == 0
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("offline host read"))
    monkeypatch.setattr(Path, "stat", lambda *a, **k: pytest.fail("offline host probe"))
    assert packet.verify_packet(portable)["reproduced"]


def test_005_subject_retains_missing_primary_context(tmp_path: Path) -> None:
    path, _, _ = controls(tmp_path)
    change_draft(path, requested_kind="false_positive")
    _, review, _, _ = dispositions.review(path)
    request = tmp_path / "subject-request.json"
    write(
        request,
        {
            "schema_version": 1,
            "kind": "quality_disposition_subject_request",
            "review": write(tmp_path / "review.json", review),
            "disposition_request": ref(path),
            "policy": None,
            "protected_roots": [],
        },
    )
    code, binding, _, _ = decisions.subject(request)
    assert code == 1 and binding["outcome"] == "blocked"
    assert "CODEQL_EXECUTION_UNIMPLEMENTED" in binding["reasons"]
    assert binding["review"]["inspection"] == review["inspection"]


def test_output_native_root_is_guarded_before_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _, _ = controls(tmp_path)
    from score_sw_fabric.quality import codeql

    monkeypatch.setattr(codeql, "run", lambda *a, **k: pytest.fail("unsafe inspection"))
    output = tmp_path / "fixture-pack/qlpack.yml"
    before = output.read_bytes()
    assert main(["quality", "disposition", "--request", str(path), "--out", str(output)]) == 2
    assert output.read_bytes() == before


def test_resealed_corrected_context_is_refused(tmp_path: Path) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.quality import disposition_models as dm

    path, _, _ = controls(tmp_path)
    _, review, _, _ = dispositions.review(path)
    review["state"] = "corrected"
    with pytest.raises(InputError):
        dm.previous(seal(review), review["draft"], review["subject"])


@pytest.mark.parametrize("field", ["extraction", "source_inspection", "toolchain", "configuration"])
def test_malformed_inspection_refuses_as_input_error(tmp_path: Path, field: str) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.quality.codeql_dispositions import validate_inspection

    path, _, _ = controls(tmp_path)
    _, review, _, _ = dispositions.review(path)
    value = review["inspection"]
    value[field] = None
    with pytest.raises(InputError):
        validate_inspection(seal(value))


@pytest.mark.parametrize("target", ["configuration", "native_patch", "tool_dependency", "source"])
def test_late_selected_context_drift_preserves_output(
    tmp_path: Path, target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.quality import codeql

    path, _, current = controls(tmp_path)
    selected = json.loads(current.read_bytes())
    changed = {
        "configuration": Path(selected["config"]["path"]),
        "native_patch": tmp_path / "report.patch",
        "tool_dependency": tmp_path / "fixture-cli-license.txt",
        "source": tmp_path / "component/check.cpp",
    }[target]
    native = codeql.run

    def drift(*args: Any, **kwargs: Any) -> Any:
        result = native(*args, **kwargs)
        changed.write_bytes(changed.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(codeql, "run", drift)
    output = tmp_path / "prior.json"
    output.write_text("prior output")
    assert main(["quality", "disposition", "--request", str(path), "--out", str(output)]) == 2
    assert output.read_text() == "prior output"


@pytest.mark.parametrize(
    "target",
    [
        "state",
        "pack_metadata",
        "library_metadata",
        "suite_definition",
        "scan_configuration",
        "source_commit",
    ],
)
def test_resealed_context_cannot_hide_native_identity_observations(
    tmp_path: Path, target: str
) -> None:
    from score_sw_fabric.assurance.models import seal

    path, original, _ = controls(tmp_path, mismatch="pack")
    _, review, _, _ = dispositions.review(path)
    if target == "state":
        review["state"] = "open"
        review["reasons"] = []
    elif target == "pack_metadata":
        review["inspection"]["pack_inspection"]["identity"]["name"] = "invented-name"
    elif target == "library_metadata":
        review["inspection"]["pack_inspection"]["libraries"][0]["metadata"]["invented"] = True
    elif target == "suite_definition":
        review["inspection"]["pack_inspection"]["suite"]["definition"] = []
    elif target == "scan_configuration":
        review["inspection"]["capability"]["effective_config"]["invented"] = True
    elif target == "source_commit":
        review["inspection"]["source_inspection"]["commit"] = "0" * 40
    review["inspection"] = seal(review["inspection"])
    review = seal(review)
    with pytest.raises(InputError):
        packet.packet(packet_request(tmp_path, path, original, review))


def test_resealed_inspection_cannot_erase_unavailable_prerequisites(tmp_path: Path) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.quality.codeql_dispositions import validate_inspection

    path, _, _ = controls(tmp_path)
    _, review, _, _ = dispositions.review(path)
    inspected = review["inspection"]
    inspected["gaps"] = []
    with pytest.raises(InputError):
        validate_inspection(seal(inspected))


def test_portable_linked_codeql_history_retains_original_states(tmp_path: Path) -> None:
    path, original, _ = controls(tmp_path)
    _, initial, _, _ = dispositions.review(path)
    previous = tmp_path / "initial-review.json"
    write(previous, initial)
    (tmp_path / "fixture-pack/changed-compiled-artifact.bqrs").write_bytes(b"synthetic bytes")
    change_request(path, previous=ref(previous))
    _, review, _, _ = dispositions.review(path)
    _, portable, _, _ = packet.packet(packet_request(tmp_path, path, original, review))
    assert portable["dispositions"][0]["history"][0]["record"] == initial
    assert packet.verify_packet(portable)["reproduced"]


@pytest.mark.parametrize("target", ["pack", "library", "configuration"])
def test_portable_history_retains_replaced_native_pack_metadata(
    tmp_path: Path, target: str
) -> None:
    import yaml

    path, original, current = controls(tmp_path)
    _, initial, _, _ = dispositions.review(path)
    previous = tmp_path / "initial-review.json"
    write(previous, initial)
    selected = json.loads(current.read_bytes())
    metadata = {
        "pack": tmp_path / "fixture-pack/qlpack.yml",
        "library": tmp_path / "fixture-pack/.codeql/libraries/codeql/cpp-all/5.0.0/qlpack.yml",
        "configuration": Path(selected["config"]["path"]),
    }[target]
    value = yaml.safe_load(metadata.read_bytes())
    if target == "configuration":
        value["id"] = "fixture-revised-codeql-config"
    else:
        value["fixture_vendor_note"] = "New metadata; old bytes must remain in history"
    metadata.write_text(yaml.safe_dump(value))
    if target == "configuration":
        selected["config"] = ref(metadata)
        write(current, selected)
        change_request(path, current={"adapter": "codeql", "request": ref(current)})
    change_request(path, previous=ref(previous))
    _, review, _, _ = dispositions.review(path)
    request = packet_request(tmp_path, path, original, review)
    if target == "configuration":
        selected_packet = json.loads(request.read_bytes())
        selected_packet["source_snapshots"].append(
            {
                "baseline_digest": initial["current_baseline"]["full_digest"],
                "root": str(tmp_path / "component"),
            }
        )
        write(request, selected_packet)
    _, portable, _, _ = packet.packet(request)
    assert portable["packet_state"] == "complete"
    assert portable["dispositions"][0]["history"][0]["record"] == initial
    assert packet.verify_packet(portable)["reproduced"]


def test_late_proposal_drift_during_final_native_guard_preserves_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.quality import codeql

    path, _, _ = controls(tmp_path)
    selected = json.loads(path.read_bytes())
    draft = Path(selected["draft"]["path"])
    native = codeql._refreeze
    count = 0

    def drift(*args: Any, **kwargs: Any) -> None:
        nonlocal count
        native(*args, **kwargs)
        count += 1
        if count == 2:
            draft.write_bytes(draft.read_bytes() + b"\n")

    monkeypatch.setattr(codeql, "_refreeze", drift)
    output = tmp_path / "prior.json"
    output.write_text("prior output")
    assert main(["quality", "disposition", "--request", str(path), "--out", str(output)]) == 2
    assert count == 2 and output.read_text() == "prior output"


def test_codeql_context_schema_composition_includes_distinct_records() -> None:
    from tests.quality_support import ROOT

    binding = json.loads((ROOT / "schemas/quality-disposition-binding.schema.json").read_bytes())
    packet_schema = json.loads((ROOT / "schemas/quality-review-packet.schema.json").read_bytes())
    variants = binding["properties"]["current_context"]["properties"]["toolchain"]["anyOf"]
    assert {"$ref": "quality-codeql-toolchain-profile.schema.json"} in variants
    props = packet_schema["properties"]["dispositions"]["items"]["properties"]
    assert {"$ref": "quality-codeql-disposition-request.schema.json"} in props["request"]["oneOf"]
    assert {"$ref": "quality-codeql-disposition-review.schema.json"} in props["review"]["oneOf"]


@pytest.mark.parametrize("value", [True, 1, None, "invalid", [], {}])
def test_malformed_phase_arguments_refuse_without_internal_errors(
    tmp_path: Path, value: Any
) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.quality.codeql_dispositions import validate_inspection

    path, _, _ = controls(tmp_path)
    _, review, _, _ = dispositions.review(path)
    inspected = review["inspection"]
    inspected["phases"][0]["argv"] = value
    with pytest.raises(InputError):
        validate_inspection(seal(inspected))


@pytest.mark.parametrize("value", [None, True, 1, "invalid", {}])
def test_malformed_suite_imports_refuse_before_portable_replay(tmp_path: Path, value: Any) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.quality.codeql_dispositions import validate_inspection

    path, _, _ = controls(tmp_path)
    _, review, _, _ = dispositions.review(path)
    inspected = review["inspection"]
    inspected["pack_inspection"]["suite"]["imports"] = value
    with pytest.raises(InputError):
        validate_inspection(seal(inspected))


def test_legacy_packet_bytes_still_replay_without_host_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.quality_support import ROOT

    portable = json.loads(
        (ROOT / "tests/fixtures/quality/codeql/legacy-disposition-packet.json").read_bytes()
    )
    assert portable["digest"] == "0525467a1d3b620b0c7957be39c191d61d5294ef63f007187484c2de4f523040"
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("offline host read"))
    monkeypatch.setattr(Path, "stat", lambda *a, **k: pytest.fail("offline host probe"))
    assert packet.verify_packet(portable)["reproduced"]


def test_unavailable_native_git_identity_stays_unknown_without_fake_drift(tmp_path: Path) -> None:
    import shutil

    path, _, _ = controls(tmp_path)
    # Remove only this test-created synthetic repository's metadata, never an external reference.
    shutil.rmtree(tmp_path / "fixture-source/.git")
    code, review, _, _ = dispositions.review(path)
    assert code == 1 and review["state"] == "open"
    assert review["inspection"]["source_inspection"]["status"] == "unknown"
    assert "NATIVE_SOURCE_IDENTITY_UNKNOWN" in review["reasons"]
    assert review["inspection"]["analysis_executed"] is False


@pytest.mark.parametrize("target", ["source:tracked", "build:tree"])
def test_partial_native_observation_failure_preserves_unknown_relation(
    tmp_path: Path, target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.quality import codeql
    from score_sw_fabric.quality.models import Budget

    path, original, _ = controls(tmp_path)
    native_execute = codeql.execute

    def unavailable(name: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        failed = {target}
        if target == "build:tree":
            failed.add("refreeze:build-tree")
        if name not in failed:
            return native_execute(name, *args, **kwargs)
        budget = Budget(1024, 2048)
        return {
            "name": name,
            "argv": args[0],
            "exit_code": 1,
            "timed_out": False,
            "elapsed_seconds": 0,
            "error": "synthetic observation failure",
            "stdout": budget.capture(b""),
            "stderr": budget.capture(b"fixture failure"),
        }

    monkeypatch.setattr(codeql, "execute", unavailable)
    code, review, _, _ = dispositions.review(path)
    inspected = review["inspection"]
    source = inspected["source_inspection"]
    assert code == 1 and inspected["analysis_executed"] is False
    assert source["status"] == "clean" and source["tree"] is not None
    assert source["source_build"]["state"] == "unknown"
    assert "SOURCE_BUILD_RECONCILIATION_UNKNOWN" in inspected["gaps"]
    _, portable, _, _ = packet.packet(packet_request(tmp_path, path, original, review))
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *a, **k: pytest.fail("offline host read"))
        guard.setattr(Path, "stat", lambda *a, **k: pytest.fail("offline host probe"))
        assert packet.verify_packet(portable)["reproduced"]
