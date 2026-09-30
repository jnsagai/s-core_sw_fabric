"""Portable run exports close over exact bytes and fail closed without Fabro."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError, read_json
from score_sw_fabric.runtime.export import build_export, verify_export
from score_sw_fabric.runtime.ledger import IntentLedger
from score_sw_fabric.runtime.models import publish
from tests.runtime_support import LINEAR, FakeFabro, intent, linear_sources, project

PACKAGE_BYTES = (LINEAR / "out/package.json").read_bytes()
PROFILE_BYTES = (LINEAR / "compiler_profile.yaml").read_bytes()


def _run(tmp_path: Path, fabro: FakeFabro) -> tuple[Any, dict[str, Any]]:
    client = fabro.client()
    package, compiler_profile = linear_sources()
    selected = intent(package, client)
    ledger = IntentLedger(tmp_path / "ledger")
    ledger.prepare(
        selected,
        version_id=client.register_package(package, compiler_profile),
        runtime_commit="a" * 40,
        source_package_digest=package["digest"],
        wire_digest=project(package, compiler_profile)["wire_digest"],
    )
    (tmp_path / "target").mkdir()
    client.create_run(
        ledger,
        selected["intent_id"],
        target=tmp_path / "target",
        disposable_root=tmp_path,
        environment_id="local",
        labels={},
    )
    return client, client.start_known_run(ledger, selected["intent_id"])


def _export(client: Any, binding: dict[str, Any], **changes: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "package_bytes": PACKAGE_BYTES,
        "compiler_profile_bytes": PROFILE_BYTES,
        "assurance_references": [],
        "output_limit": 4096,
    }
    return build_export(client, binding, **{**arguments, **changes})


def test_completed_export_closes_source_wire_events_blobs_and_outputs(tmp_path: Path) -> None:
    fabro = FakeFabro()
    client, binding = _run(tmp_path, fabro)
    record = _export(client, binding)
    assert record["completeness"] == "complete"
    assert record["source_package"]["entrypoint"] == "workflow.toml"
    assert record["wire_projection"]["wire_entrypoint"] == "workflow.fabro"
    assert record["wire_projection"]["wire_digest"] == binding["version_id"]
    assert record["status"]["native_status"] == "succeeded"
    assert record["status"]["engineering_readiness"] == "not_evaluated"
    ids = {item["id"]: item for item in record["blobs"]}
    assert ids["source:package"]["origin"] == "fabric_source"
    assert base64.b64decode(ids["stage-output:node_2e028993944f88df30dfca7b:1"]["base64"]) == (
        b"hello-006"
    )
    assert sum(1 for name in ids if name.startswith("native-blob:")) == 5
    result = verify_export(record)
    assert result["reproduced"] is True
    assert result["completeness"] == "complete"
    assert result["reason_codes"] == []
    assert result["event_count"] == len(record["events"])


def test_waiting_run_export_is_complete_history_without_success(tmp_path: Path) -> None:
    client, binding = _run(tmp_path, FakeFabro(start_outcome="blocked"))
    record = _export(client, binding)
    result = verify_export(record)
    assert (result["reproduced"], result["completeness"]) == (True, "complete")
    assert result["native_status"] == "blocked"
    assert result["native_terminal"] is False
    assert record["questions"] == [{"id": "review#1", "stage": "review@1"}]


def test_relocated_export_verifies_offline_with_zero_native_calls(tmp_path: Path) -> None:
    fabro = FakeFabro()
    client, binding = _run(tmp_path, fabro)
    first = tmp_path / "first/export.json"
    publish(first, _export(client, binding), inputs=[], protected_roots=[])
    moved = tmp_path / "elsewhere/copy.json"
    moved.parent.mkdir()
    shutil.move(first, moved)
    calls = len(fabro.calls)
    fabro.runs.clear()
    assert verify_export(read_json(moved))["reproduced"] is True
    assert len(fabro.calls) == calls


def test_unavailable_native_blob_is_explicitly_incomplete(tmp_path: Path) -> None:
    fabro = FakeFabro()
    client, binding = _run(tmp_path, fabro)
    missing = next(iter(sorted(fabro.blobs)))
    fabro.missing_blobs.add(missing)
    record = _export(client, binding)
    assert record["completeness"] == "incomplete"
    assert "BLOB_MISSING" in record["limitations"]
    result = verify_export(record)
    assert result["reproduced"] is True
    assert result["completeness"] == "incomplete"
    assert {"BLOB_MISSING", "EXPORT_INCOMPLETE"} <= set(result["reason_codes"])


def _resealed(record: dict[str, Any], change: str) -> dict[str, Any]:
    changed = deepcopy(record)
    if change == "drop_event":
        changed["events"].pop(3)
    elif change == "drop_blob":
        dropped = next(item for item in changed["blobs"] if item["id"].startswith("native-blob:"))
        changed["blobs"].remove(dropped)
    elif change == "drop_output":
        changed["blobs"] = [
            item for item in changed["blobs"] if not item["id"].startswith("stage-output:")
        ]
    elif change == "package_bytes":
        package = json.loads(PACKAGE_BYTES)
        package["files"]["workflow.fabro"] += "\n"
        data = json.dumps(package).encode()
        for item in changed["blobs"]:
            if item["id"] == "source:package":
                item["base64"] = base64.b64encode(data).decode()
                item["bytes"] = len(data)
                item["sha256"] = hashlib.sha256(data).hexdigest()
                changed["source_package"]["sha256"] = item["sha256"]
    elif change == "version":
        created = changed["events"][0]["item"]["record"]
        created["spec"]["workflow_version_id"] = "0" * 64
    elif change == "extra_blob":
        extra = {**changed["blobs"][0], "id": "native-blob:" + "0" * 64}
        changed["blobs"].append(extra)
    elif change == "relabel_output":
        for item in changed["blobs"]:
            if item["id"].startswith("stage-output:"):
                item["origin"] = "authenticated_005_reference"
    elif change == "runtime":
        changed["runtime"]["source_commit"] = "f" * 40
    elif change == "readiness":
        changed["status"]["engineering_readiness"] = "ready"
    return seal({key: value for key, value in changed.items() if key != "digest"})


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("drop_event", "EVENT_GAP"),
        ("drop_blob", "BLOB_MISSING"),
        ("drop_output", "BLOB_MISSING"),
        ("package_bytes", "EXPORT_CLOSURE_MISMATCH"),
        ("version", "EXPORT_CLOSURE_MISMATCH"),
        ("extra_blob", "EXPORT_CLOSURE_MISMATCH"),
        ("relabel_output", "EXPORT_CLOSURE_MISMATCH"),
        ("runtime", "RUNTIME_IDENTITY_MISMATCH"),
        ("readiness", "EXPORT_CLOSURE_MISMATCH"),
    ],
)
def test_resealed_closure_change_never_reproduces_as_complete(
    tmp_path: Path, change: str, code: str
) -> None:
    client, binding = _run(tmp_path, FakeFabro())
    result = verify_export(_resealed(_export(client, binding), change))
    assert code in result["reason_codes"]
    assert result["reproduced"] is False or result["completeness"] != "complete"


def test_single_byte_change_without_reseal_is_corrupt(tmp_path: Path) -> None:
    client, binding = _run(tmp_path, FakeFabro())
    record = _export(client, binding)
    blob = next(item for item in record["blobs"] if item["id"].startswith("stage-output:"))
    raw = bytearray(base64.b64decode(blob["base64"]) or b"x")
    raw[0] ^= 1
    changed = deepcopy(record)
    for item in changed["blobs"]:
        if item["id"] == blob["id"]:
            item["base64"] = base64.b64encode(bytes(raw)).decode()
    with pytest.raises(InputError) as error:
        verify_export(changed)
    assert error.value.code in {"HASH_MISMATCH", "SEMANTIC_DIGEST"}
    envelope = deepcopy(record)
    envelope["events"][0]["recorded_at"] += 1
    with pytest.raises(InputError) as digest_error:
        verify_export(envelope)
    assert digest_error.value.code == "SEMANTIC_DIGEST"


def test_export_refuses_changed_source_or_unknown_run_before_native_reads(tmp_path: Path) -> None:
    fabro = FakeFabro()
    client, binding = _run(tmp_path, fabro)
    calls = len(fabro.calls)
    package = json.loads(PACKAGE_BYTES)
    package["digest"] = "0" * 64
    with pytest.raises(InputError):
        _export(client, binding, package_bytes=json.dumps(package).encode())
    with pytest.raises(InputError) as error:
        _export(client, {**binding, "run_id": None, "creation_state": "prepared"})
    assert error.value.code == "RUN_ID_UNKNOWN"
    reduced = fabro.client(demonstrated=["event_read", "run_inspect", "timeline_read"])
    with pytest.raises(InputError) as capability:
        _export(reduced, binding)
    assert capability.value.code == "RUNTIME_CAPABILITY_UNAVAILABLE"
    assert len(fabro.calls) == calls


def test_output_limit_marks_export_incomplete(tmp_path: Path) -> None:
    client, binding = _run(tmp_path, FakeFabro())
    record = _export(client, binding, output_limit=4)
    assert record["completeness"] == "incomplete"
    assert "STAGE_OUTPUT_LIMIT" in record["limitations"]


def test_verification_never_upgrades_a_recorded_incomplete_export(tmp_path: Path) -> None:
    client, binding = _run(tmp_path, FakeFabro())
    record = _export(client, binding)
    assert verify_export(record)["completeness"] == "complete"
    marked = {key: value for key, value in record.items() if key != "digest"}
    result = verify_export(seal({**marked, "completeness": "incomplete"}))
    assert result["reproduced"] is True
    assert result["completeness"] == "incomplete"
    assert result["reason_codes"] == ["EXPORT_INCOMPLETE"]
