"""Opt-in native 006 probe against an explicitly disposable pinned server."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import read_json, read_yaml
from score_sw_fabric.runtime.client import FabroClient, verify_candidate_files
from score_sw_fabric.runtime.inspect import bind_pending_questions, inspect_run
from score_sw_fabric.runtime.ledger import IntentLedger
from score_sw_fabric.runtime.projection import project_version

ROOT = Path(__file__).resolve().parents[2]
COMMIT = "1b4fb15281ebb724426f9e480dce48d0100ff79b"


def _selected(tmp_path: Path) -> FabroClient:
    selected = {
        key: os.environ.get(key)
        for key in (
            "SCORE_FABRO_RUNTIME_DISPOSABLE_ROOT",
            "SCORE_FABRO_RUNTIME_URL",
            "SCORE_FABRO_RUNTIME_TOKEN_FILE",
            "SCORE_FABRO_SOURCE_API",
            "SCORE_FABRO_BIN",
        )
    }
    if any(value is None for value in selected.values()):
        pytest.skip("Selected disposable Fabro runtime is not configured for 006")
    runtime_root = Path(selected["SCORE_FABRO_RUNTIME_DISPOSABLE_ROOT"] or "")
    executable = Path(selected["SCORE_FABRO_BIN"] or "")
    source_api = Path(selected["SCORE_FABRO_SOURCE_API"] or "")
    token_path = Path(selected["SCORE_FABRO_RUNTIME_TOKEN_FILE"] or "")
    server = json.loads((runtime_root / "storage/server.json").read_text())
    pid = server["pid"]
    assert Path(f"/proc/{pid}/cwd").resolve() == runtime_root.resolve()
    assert Path(f"/proc/{pid}/exe").resolve() == executable.resolve()
    assert (token_path.stat().st_mode & 0o077) == 0
    profile = seal(
        {
            "schema_version": 1,
            "kind": "runtime_profile",
            "id": "disposable-006-integration",
            "source_commit": COMMIT,
            "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            "source_api_sha256": hashlib.sha256(source_api.read_bytes()).hexdigest(),
            "base_url": selected["SCORE_FABRO_RUNTIME_URL"],
            "auth_mode": "dev_token_disposable",
            "declared_capabilities": [
                "event_read",
                "question_read",
                "run_cancel",
                "run_create",
                "run_inspect",
                "run_start",
                "timeline_read",
                "workflow_register",
            ],
            "demonstrated_capabilities": [
                "event_read",
                "question_read",
                "run_cancel",
                "run_create",
                "run_inspect",
                "run_start",
                "timeline_read",
                "workflow_register",
            ],
            "limits": {"timeout_seconds": 20, "response_bytes": 1_000_000},
            "status": "candidate_only",
        }
    )
    verify_candidate_files(profile, executable=executable, source_api=source_api)
    assert tmp_path.resolve().is_relative_to(Path("/tmp"))
    return FabroClient(
        profile,
        expected_commit=COMMIT,
        credential_provider=lambda: token_path.read_text().strip(),
    )


def test_closed_003_version_registers_and_command_run_completes_without_model_calls(
    tmp_path: Path,
) -> None:
    client = _selected(tmp_path)
    fixture = ROOT / "tests/fixtures/compiler/linear"
    package = read_json(fixture / "out/package.json")
    compiler_profile = read_yaml(fixture / "compiler_profile.yaml")
    projection = project_version(package, compiler_profile)
    version_id = client.register_package(package, compiler_profile)
    assert version_id == projection["wire_digest"]
    target = tmp_path / "target"
    target.mkdir()
    intent_id = "native-006-contract-probe"
    intent = seal(
        {
            "schema_version": 1,
            "kind": "runtime_intent",
            "intent_id": intent_id,
            "package_ref": {
                "path": "package.json",
                "sha256": hashlib.sha256((fixture / "out/package.json").read_bytes()).hexdigest(),
                "semantic_digest": package["digest"],
            },
            "runtime_profile_ref": {
                "path": "runtime-profile.json",
                "sha256": client.profile["digest"],
                "semantic_digest": client.profile["digest"],
            },
            "baseline": {
                "source_digest": package["digest"],
                "process_digest": "a" * 64,
                "policy_digest": "b" * 64,
                "tool_digest": "c" * 64,
                "subject_digest": "d" * 64,
                "evidence_digests": [],
            },
            "start_args": {"target_id": "local", "labels": {}},
            "limits": {
                "timeout_seconds": 30,
                "event_pages": 10,
                "output_bytes": 1024,
                "attempts": 2,
            },
        }
    )
    ledger = IntentLedger(tmp_path / "ledger")
    ledger.prepare(
        intent,
        version_id=version_id,
        runtime_commit=COMMIT,
        source_package_digest=package["digest"],
        wire_digest=projection["wire_digest"],
    )
    binding = client.create_run(
        ledger,
        intent_id,
        target=target,
        disposable_root=tmp_path,
        environment_id="local",
        labels={},
    )
    assert binding["creation_state"] == "run_known"
    run_id = binding["run_id"]
    path = f"/api/v1/runs/{run_id}"
    started = client.start_known_run(ledger, intent_id)
    assert started["start_state"] == "started"
    assert client.start_known_run(ledger, intent_id) == started
    for _ in range(100):
        status, body = client.request("run_inspect", "GET", path)
        assert status == 200
        run = json.loads(body)
        if run["lifecycle"]["status"]["kind"] in {"succeeded", "failed", "blocked"}:
            break
        time.sleep(0.1)
    assert run["lifecycle"]["status"] == {"kind": "succeeded", "reason": "completed"}
    assert run["usage"]["tokens"] == {
        "input": 0,
        "output": 0,
        "reasoning": 0,
        "cache_read": 0,
        "cache_write": 0,
    }
    status, body = client.request("event_read", "GET", path + "/events?after=0&limit=1000")
    assert status == 200
    events = json.loads(body)
    assert events["meta"]["has_more"] is False
    assert [event["stream_seq"] for event in events["data"]] == list(
        range(1, len(events["data"]) + 1)
    )
    created = events["data"][0]["item"]["record"]
    assert created["kind"] == "run.created"
    assert created["spec"]["workflow_version_id"] == version_id
    status, body = client.request("timeline_read", "GET", path + "/timeline")
    assert status == 200 and json.loads(body)["entries"]
    status, body = client.request("question_read", "GET", path + "/questions")
    assert status == 200 and json.loads(body)["data"] == []
    inspection = inspect_run(client, run_id)
    assert inspection["complete"] is True
    assert inspection["native_status"] == "succeeded"
    assert inspection["event_position"] == len(events["data"])
    assert inspection["engineering_readiness"] == "not_evaluated"


def test_human_gate_waits_without_answer_and_cancel_converges(tmp_path: Path) -> None:
    client = _selected(tmp_path)
    fixture = ROOT / "tests/fixtures/runtime/shared-human/package.json"
    compiler_profile = read_yaml(
        ROOT / "tests/fixtures/compiler/shared-parallel-review/compiler_profile.yaml"
    )
    package = read_json(fixture)
    version_id = client.register_package(package, compiler_profile)
    target = tmp_path / "human-target"
    target.mkdir()
    status, body = client.request(
        "run_create",
        "POST",
        "/api/v1/runs",
        {
            "workflow_version_id": version_id,
            "target": {"kind": "folder", "path": str(target)},
            "environment_id": "local",
            "args": {
                "labels": {"score_intent": "native-human-006-contract-probe"},
                "auto_approve": False,
                "dry_run": False,
            },
        },
    )
    assert status == 201
    run_id = json.loads(body)["id"]
    path = f"/api/v1/runs/{run_id}"
    status, _ = client.request("run_start", "POST", path + "/start", {})
    assert status == 200
    for _ in range(100):
        status, body = client.request("run_inspect", "GET", path)
        assert status == 200
        run = json.loads(body)
        if run["lifecycle"]["status"]["kind"] in {"blocked", "failed", "succeeded"}:
            break
        time.sleep(0.1)
    assert run["lifecycle"]["status"] == {
        "kind": "blocked",
        "blocked_reason": "human_input_required",
    }
    assert all(value == 0 for value in run["usage"]["tokens"].values())
    inspection = inspect_run(client, run_id)
    assert inspection["complete"] is True
    assert len(inspection["questions"]) == 1
    assert "interview.answered" not in json.dumps(inspection["events"])
    subject = seal(
        {
            "schema_version": 1,
            "kind": "assurance_subject",
            "assurance_domain": "fixture_contract",
            "artifact_candidate": {"bindings": {"workflow_package": package["digest"]}},
            "expected_obligation_ids": ["obligation-a", "obligation-b"],
        }
    )
    handoff = bind_pending_questions(
        inspection,
        package,
        compiler_profile,
        subject,
        expected_subject_digest=subject["digest"],
    )
    assert handoff[0]["next_action"] == "external_authorized_human_decision_required"
    assert handoff[0]["engineering_readiness"] == "not_evaluated"
    status, _ = client.request("run_cancel", "POST", path + "/cancel", {})
    assert status in {200, 202}
    for _ in range(100):
        status, body = client.request("run_inspect", "GET", path)
        assert status == 200
        run = json.loads(body)
        if run["lifecycle"]["status"]["kind"] == "failed":
            break
        time.sleep(0.1)
    assert run["lifecycle"]["status"] == {"kind": "failed", "reason": "cancelled"}
