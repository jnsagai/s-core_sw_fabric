"""Opt-in native 006 probe against an explicitly disposable pinned server."""

from __future__ import annotations

import hashlib
import json
import os
import time
from copy import deepcopy
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.compiler.reader import semantic_digest
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml
from score_sw_fabric.runtime.client import FabroClient, verify_candidate_files
from score_sw_fabric.runtime.export import build_export, verify_export
from score_sw_fabric.runtime.inspect import bind_pending_questions, inspect_run
from score_sw_fabric.runtime.ledger import IntentLedger
from score_sw_fabric.runtime.models import publish
from score_sw_fabric.runtime.projection import project_version
from score_sw_fabric.runtime.resume import admit_resume

ROOT = Path(__file__).resolve().parents[2]
COMMIT = "1b4fb15281ebb724426f9e480dce48d0100ff79b"
DECLARED = [
    "blob_read",
    "event_read",
    "output_read",
    "question_read",
    "run_cancel",
    "run_create",
    "run_inspect",
    "run_resume",
    "run_start",
    "stage_list",
    "timeline_read",
    "workflow_register",
]


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
            "declared_capabilities": DECLARED,
            # Explicit same-run resume was accepted but inert on the candidate; it stays unproven.
            "demonstrated_capabilities": sorted(set(DECLARED) - {"run_resume"}),
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


def _native_run_ids(client: FabroClient) -> set[str]:
    """Test-side raw count of native runs; run listing is not a fabric capability."""
    import urllib.request

    found: set[str] = set()
    token = client.credential_provider()
    for offset in range(0, 10_000, 100):
        request = urllib.request.Request(
            client.profile["base_url"] + f"/api/v1/runs?limit=100&offset={offset}",
            headers={"Authorization": "Bearer " + token},
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=10) as response:
            page = json.loads(response.read())
        found.update(item["id"] for item in page["data"])
        if len(page["data"]) < 100:
            return found
    raise AssertionError("native run list exceeded test bound")


def _wait(client: FabroClient, run_id: str, kinds: set[str]) -> dict[str, object]:
    for _ in range(200):
        status, body = client.request("run_inspect", "GET", f"/api/v1/runs/{run_id}")
        assert status == 200
        lifecycle = json.loads(body)["lifecycle"]["status"]
        if lifecycle["kind"] in kinds:
            return dict(lifecycle)
        time.sleep(0.1)
    raise AssertionError(f"native run {run_id} did not reach {sorted(kinds)}")


def _intent_for(
    package: dict[str, object], package_path: Path, client: FabroClient, identifier: str
) -> dict[str, object]:
    return seal(
        {
            "schema_version": 1,
            "kind": "runtime_intent",
            "intent_id": identifier,
            "package_ref": {
                "path": package_path.name,
                "sha256": hashlib.sha256(package_path.read_bytes()).hexdigest(),
                "semantic_digest": package["digest"],
            },
            "runtime_profile_ref": {
                "path": "runtime-profile.json",
                "sha256": client.profile["digest"],
                "semantic_digest": client.profile["digest"],
            },
            "baseline": {
                "source_digest": str(package["digest"]),
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
                "output_bytes": 65536,
                "attempts": 2,
            },
        }
    )


def _started(
    client: FabroClient,
    tmp_path: Path,
    package_path: Path,
    compiler_profile: dict[str, object],
    identifier: str,
) -> tuple[IntentLedger, dict[str, object], dict[str, object]]:
    package = read_json(package_path)
    projection = project_version(package, compiler_profile)
    version_id = client.register_package(package, compiler_profile)
    selected = _intent_for(package, package_path, client, identifier)
    ledger = IntentLedger(tmp_path / f"ledger-{identifier}")
    ledger.prepare(
        selected,
        version_id=version_id,
        runtime_commit=COMMIT,
        source_package_digest=str(package["digest"]),
        wire_digest=projection["wire_digest"],
    )
    target = tmp_path / f"target-{identifier}"
    target.mkdir()
    client.create_run(
        ledger,
        identifier,
        target=target,
        disposable_root=tmp_path,
        environment_id="local",
        labels={},
    )
    return ledger, selected, client.start_known_run(ledger, identifier)


def test_relocation_drift_lost_response_and_duplicate_intent(tmp_path: Path) -> None:
    client = _selected(tmp_path)
    fixture = ROOT / "tests/fixtures/compiler/linear"
    original = (fixture / "out/package.json").read_bytes()
    compiler_profile = read_yaml(fixture / "compiler_profile.yaml")
    relocated = tmp_path / "relocated/package.json"
    relocated.parent.mkdir()
    relocated.write_bytes(original)
    package = read_json(relocated)
    first = client.register_package(package, compiler_profile)
    assert (
        client.register_package(read_json(fixture / "out/package.json"), compiler_profile) == first
    )
    before = _native_run_ids(client)
    drifted = json.loads(original)
    drifted["files"]["workflow.fabro"] += "\n"
    with pytest.raises(InputError) as drift:
        client.register_package(drifted, compiler_profile)
    assert drift.value.code == "PACKAGE_DIGEST"
    drifted["digest"] = semantic_digest(drifted)
    with pytest.raises(InputError) as resealed:
        client.register_package(drifted, compiler_profile)
    assert resealed.value.code == "PACKAGE_FILE_DIGEST"
    ledger, selected, started = _started(client, tmp_path, relocated, compiler_profile, "dup-006")
    assert started["start_state"] == "started"
    assert client.start_known_run(ledger, "dup-006") == started
    lost_ledger = IntentLedger(tmp_path / "ledger-lost")
    lost = _intent_for(package, relocated, client, "lost-006")
    lost_ledger.prepare(
        lost,
        version_id=first,
        runtime_commit=COMMIT,
        source_package_digest=package["digest"],
        wire_digest=first,
    )
    real_transport = client.transport
    creates = 0

    def lose_create(
        method: str, url: str, body: bytes | None, timeout: float, maximum: int, token: str
    ) -> tuple[int, bytes]:
        nonlocal creates
        result = real_transport(method, url, body, timeout, maximum, token)
        if method == "POST" and url.endswith("/api/v1/runs"):
            creates += 1
            raise TimeoutError("response lost after native acceptance")
        return result

    client.transport = lose_create
    (tmp_path / "target-lost").mkdir()
    with pytest.raises(InputError):
        client.create_run(
            lost_ledger,
            "lost-006",
            target=tmp_path / "target-lost",
            disposable_root=tmp_path,
            environment_id="local",
            labels={},
        )
    assert lost_ledger.read("lost-006")["creation_state"] == "reconciliation_required"
    with pytest.raises(InputError) as repeated:
        client.create_run(
            lost_ledger,
            "lost-006",
            target=tmp_path / "target-lost",
            disposable_root=tmp_path,
            environment_id="local",
            labels={},
        )
    assert repeated.value.code == "RUN_CREATE_UNCERTAIN"
    client.transport = real_transport
    assert creates == 1
    created = _native_run_ids(client) - before
    assert len(created) == 2
    assert started["run_id"] in created
    assert (fixture / "out/package.json").read_bytes() == original
    RESULTS["lost_response_runs"] = sorted(created - {str(started["run_id"])})
    RESULTS["duplicate_intent_run"] = started["run_id"]


def test_resume_admission_and_confirmed_cancellation_on_native_states(tmp_path: Path) -> None:
    client = _selected(tmp_path)
    fixture = ROOT / "tests/fixtures/compiler/linear"
    ledger, selected, binding = _started(
        client,
        tmp_path,
        fixture / "out/package.json",
        read_yaml(fixture / "compiler_profile.yaml"),
        "resume-completed-006",
    )
    run_id = str(binding["run_id"])
    assert _wait(client, run_id, {"succeeded", "failed"}) == {
        "kind": "succeeded",
        "reason": "completed",
    }
    inspection = inspect_run(client, run_id)
    assert inspection["complete"] is True
    stage_ids = [item["id"] for item in inspection["stages"]]
    assert all(item.endswith("@1") for item in stage_ids)
    assert len(stage_ids) == len(set(item.rsplit("@", 1)[0] for item in stage_ids))
    decision = admit_resume(
        binding=binding,
        intent=selected,
        baseline_now=selected["baseline"],
        inspection=inspection,
        evidence=[],
        effects=[],
    )
    assert decision["decision"] == "refuse_terminal"
    with pytest.raises(InputError) as refused:
        client.resume_run(decision)
    assert refused.value.code == "RESUME_NOT_ADMITTED"
    assert inspect_run(client, run_id)["events"] == inspection["events"]
    shared = ROOT / "tests/fixtures/runtime/shared-human/package.json"
    human_ledger, human_intent, human = _started(
        client,
        tmp_path,
        shared,
        read_yaml(ROOT / "tests/fixtures/compiler/shared-parallel-review/compiler_profile.yaml"),
        "resume-waiting-006",
    )
    human_run = str(human["run_id"])
    assert _wait(client, human_run, {"blocked", "failed", "succeeded"})["kind"] == "blocked"
    waiting = inspect_run(client, human_run)
    blocked = admit_resume(
        binding=human,
        intent=human_intent,
        baseline_now=human_intent["baseline"],
        inspection=waiting,
        evidence=[],
        effects=[],
    )
    # The waiting gate stage is also in flight, so its effects would need reconciliation.
    assert (blocked["decision"], blocked["reason_codes"]) == (
        "block_unknown",
        ["EFFECT_RECONCILIATION_REQUIRED", "RESUME_SOURCE_ACTIVE"],
    )
    cancelled = client.cancel_run(human_run, polls=100, interval_seconds=0.1)
    assert cancelled["cancellation"] == "confirmed"
    after = inspect_run(client, human_run)
    assert after["events"][: len(waiting["events"])] == waiting["events"]
    refused_cancel = admit_resume(
        binding=human,
        intent=human_intent,
        baseline_now=human_intent["baseline"],
        inspection=after,
        evidence=[],
        effects=[],
    )
    assert refused_cancel["decision"] == "refuse_terminal"
    assert "CANCELLED_TERMINAL" in refused_cancel["reason_codes"]
    with pytest.raises(InputError):
        client.cancel_run(human_run, polls=1, interval_seconds=0)
    RESULTS["resume_refused_completed"] = run_id
    RESULTS["cancel_confirmed"] = [human_run, cancelled["request_http_status"]]


def test_probe_graph_external_effect_runs_once(tmp_path: Path) -> None:
    """Probe-only native graph with an external effect; not a 003 package claim."""
    client = _selected(tmp_path)
    effects = tmp_path / "effects.log"
    graph = (
        'digraph EffectProbe { graph [goal="006 effect count probe"]; start [type="start"]; '
        'exit [type="exit"]; '
        f'effect [type="command", script="echo effect >> {effects}", timeout="30s"]; '
        "start -> effect -> exit; }\n"
    )
    wire = {
        "entrypoint": "workflow.fabro",
        "files": {
            "workflow.fabro": graph,
            "workflow.toml": '_version = 1\n\n[workflow]\ngraph = "workflow.fabro"\n',
        },
        "workflow_dependencies": {},
    }
    status, body = client.request("workflow_register", "POST", "/api/v1/workflow-versions", wire)
    assert status == 201
    version_id = json.loads(body)["workflow_version_id"]
    (tmp_path / "effect-target").mkdir()
    status, body = client.request(
        "run_create",
        "POST",
        "/api/v1/runs",
        {
            "workflow_version_id": version_id,
            "target": {"kind": "folder", "path": str(tmp_path / "effect-target")},
            "environment_id": "local",
            "args": {"labels": {}, "auto_approve": False, "dry_run": False},
        },
    )
    assert status == 201
    run_id = json.loads(body)["id"]
    assert client.request("run_start", "POST", f"/api/v1/runs/{run_id}/start", {})[0] == 200
    assert _wait(client, run_id, {"succeeded", "failed"})["kind"] == "succeeded"
    assert effects.read_text() == "effect\n"
    inspection = inspect_run(client, run_id)
    assert [item["id"] for item in inspection["stages"]] == ["start@1", "effect@1", "exit@1"]
    assert effects.read_text() == "effect\n"
    RESULTS["effect_probe_run"] = run_id


def test_completed_and_waiting_exports_verify_offline_after_relocation(tmp_path: Path) -> None:
    client = _selected(tmp_path)
    fixture = ROOT / "tests/fixtures/compiler/linear"
    package_path = fixture / "out/package.json"
    profile_path = fixture / "compiler_profile.yaml"
    _, _, completed = _started(
        client, tmp_path, package_path, read_yaml(profile_path), "export-completed-006"
    )
    _wait(client, str(completed["run_id"]), {"succeeded", "failed"})
    shared = ROOT / "tests/fixtures/runtime/shared-human/package.json"
    shared_profile = ROOT / "tests/fixtures/compiler/shared-parallel-review/compiler_profile.yaml"
    _, _, waiting = _started(
        client, tmp_path, shared, read_yaml(shared_profile), "export-waiting-006"
    )
    _wait(client, str(waiting["run_id"]), {"blocked", "failed", "succeeded"})
    exported = {}
    for name, binding, package, profile in (
        ("completed", completed, package_path, profile_path),
        ("waiting", waiting, shared, shared_profile),
    ):
        record = build_export(
            client,
            binding,
            package_bytes=package.read_bytes(),
            compiler_profile_bytes=profile.read_bytes(),
            assurance_references=[],
            output_limit=65536,
        )
        assert record["completeness"] == "complete", record["limitations"]
        out = tmp_path / f"{name}/export.json"
        publish(out, record, inputs=[package, profile], protected_roots=[ROOT / "tests"])
        moved = tmp_path / f"moved/{name}.json"
        moved.parent.mkdir(exist_ok=True)
        out.rename(moved)
        exported[name] = (moved, record)
    if waiting["run_id"]:
        client.cancel_run(str(waiting["run_id"]), polls=100, interval_seconds=0.1)

    def offline(*_: object) -> tuple[int, bytes]:
        raise AssertionError("offline verification contacted Fabro")

    client.transport = offline
    for name, (moved, record) in exported.items():
        result = verify_export(read_json(moved))
        assert (result["reproduced"], result["completeness"]) == (True, "complete"), name
        missing = deepcopy(record)
        missing["blobs"] = [
            item for item in missing["blobs"] if not item["id"].startswith("native-blob:")
        ]
        result = verify_export(seal({k: v for k, v in missing.items() if k != "digest"}))
        assert "BLOB_MISSING" in result["reason_codes"] and result["completeness"] != "complete"
        corrupt = deepcopy(record)
        corrupt["blobs"][0]["base64"] = corrupt["blobs"][0]["base64"][:-4] + "AAAA"
        with pytest.raises(InputError):
            verify_export(corrupt)
        RESULTS[f"export_{name}"] = {
            "run_id": record["binding"]["run_id"],
            "digest": record["digest"],
            "sha256": hashlib.sha256(moved.read_bytes()).hexdigest(),
            "bytes": moved.stat().st_size,
            "events": len(record["events"]),
            "blobs": len(record["blobs"]),
            "status": record["status"]["native_status"],
        }


RESULTS: dict[str, object] = {}


@pytest.fixture(scope="module", autouse=True)
def _record_results() -> object:
    yield
    target = os.environ.get("SCORE_FABRO_RESULTS_FILE")
    if target and RESULTS:
        Path(target).write_text(json.dumps(RESULTS, indent=2, sort_keys=True) + "\n")
