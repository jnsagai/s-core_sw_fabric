"""Missing or false supervision must never admit an unattended run."""

import importlib
import os
import socket
import time
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.runtime import account_repair as repair
from score_sw_fabric.runtime import supervision as s
from score_sw_fabric.runtime.supervision import classify, require_ready


def test_missing_supervisor_refuses_start(tmp_path: Path) -> None:
    with pytest.raises((OSError, ValueError)):
        require_ready(tmp_path / "policy.json")


def test_human_gate_and_source_findings_never_dispatch_repair() -> None:
    record = {"lifecycle": {"status": {"kind": "running"}}, "timestamps": {}}
    assert (
        classify(
            record,
            {"pending_interviews": {"review": {}}},
            False,
            99,
            {"status": "unavailable"},
            1000,
        )
        is None
    )
    assert classify(record, {}, True, 0, {"status": "findings"}, 1000) is None


def test_native_failed_with_cancelled_reason_never_dispatches_repair() -> None:
    record = {"lifecycle": {"status": {"kind": "failed", "reason": "cancelled"}}}
    assert classify(record, {}, False, 99, {"status": "unavailable"}, 1000) is None


@pytest.fixture
def receipt(tmp_path: Path) -> Path:
    control = tmp_path / "control.py"
    control.write_text("immutable control")
    policy = tmp_path / "policy.json"
    s.atomic(policy, {"run_id": "RUN_A", "controls": {str(control): s.digest(control)}})
    s.atomic(
        tmp_path / "heartbeat.json",
        {
            "run_id": "RUN_A",
            "policy_sha256": s.digest(policy),
            "phase": "observing",
            "dependencies_verified": True,
            "pid": os.getpid(),
            "process_identity": s.process_identity(os.getpid()),
            "observed_at": time.time(),
        },
    )
    return policy


@pytest.mark.parametrize(
    "fault",
    ["wrong_run", "wrong_policy", "stale", "dead", "pid_reuse", "unhealthy", "changed_control"],
)
def test_false_supervision_cannot_admit(fault: str, receipt: Path) -> None:
    path = receipt.parent / "heartbeat.json"
    value = s.read(path)
    if fault == "wrong_run":
        value["run_id"] = "OTHER"
    elif fault == "wrong_policy":
        value["policy_sha256"] = "0" * 64
    elif fault == "stale":
        value["observed_at"] -= 31
    elif fault == "dead":
        value["pid"] = 999999999
    elif fault == "pid_reuse":
        value["process_identity"] = "wrong-start-time"
    elif fault == "unhealthy":
        value["phase"] = "repairing"
    else:
        (receipt.parent / "control.py").write_text("changed control")
    s.atomic(path, value)
    with pytest.raises((OSError, ValueError)):
        s.require_ready(receipt)


def test_ready_receipt_must_match_callers_native_run(receipt: Path) -> None:
    assert s.require_ready(receipt, expected_run_id="RUN_A")["pid"] == os.getpid()
    with pytest.raises(ValueError, match="another run"):
        s.require_ready(receipt, expected_run_id="RUN_B")


@pytest.mark.parametrize(
    "status,worker,misses,measurement,age,expected",
    [
        ("running", False, 3, {}, 61, "worker_missing"),
        ("running", False, 2, {}, 61, None),
        ("running", False, 3, {}, 59, None),
        ("running", True, 0, {"status": "unavailable"}, 61, "host_collector_failure"),
        ("failed", False, 0, {}, 1, "native_failure"),
        ("canceled", False, 99, {"status": "unavailable"}, 999, None),
        ("succeeded", False, 99, {"status": "unavailable"}, 999, None),
    ],
)
def test_classification_respects_native_state_and_start_grace(
    status: str,
    worker: bool,
    misses: int,
    measurement: dict[str, Any],
    age: float,
    expected: str | None,
) -> None:
    record = {"lifecycle": {"status": {"kind": status}}}
    assert s.classify(record, {}, worker, misses, measurement, age) == expected


def test_duplicate_incident_is_claimed_once(tmp_path: Path) -> None:
    incident = {"run_id": "A", "kind": "worker_missing"}
    assert s.claim(tmp_path, incident) is not None
    assert s.claim(tmp_path, incident) is None


@pytest.mark.parametrize("human_gate", [False, True])
def test_observer_uses_compact_reads_and_preserves_human_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, human_gate: bool
) -> None:
    import io
    import json
    from types import SimpleNamespace

    bound = tmp_path / "workspace"
    bound.mkdir()
    auth = tmp_path / "auth.json"
    s.atomic(auth, {"servers": {"http://fixture": {"token": "fixture"}}})
    policy = tmp_path / "policy.json"
    s.atomic(
        policy,
        {
            "run_id": "RUN",
            "server_url": "http://fixture",
            "auth_file": str(auth),
            "controls": {},
            "prepared_root": str(bound),
            "unit": "fixture",
            "attached_at": 0,
            "workspace_device": bound.stat().st_dev,
        },
    )
    s.atomic(
        bound / "latest-measurement.json", {"status": "unavailable" if human_gate else "findings"}
    )
    requests = []

    def observe(request: Any, **kwargs: Any) -> io.BytesIO:
        url = request.full_url
        requests.append(url)
        if url.endswith("/questions"):
            value = {"data": [{"id": "review"}] if human_gate else []}
        else:
            assert url == "http://fixture/api/v1/runs/RUN", "Full growing state must not be fetched"
            value = {"id": "RUN", "lifecycle": {"status": {"kind": "running"}}}
        return io.BytesIO(json.dumps(value).encode())

    monkeypatch.setattr(
        s.urllib.request, "build_opener", lambda *args: SimpleNamespace(open=observe)
    )
    monkeypatch.setattr(s, "worker_alive", lambda p: not human_gate)
    ticks = []

    def tick(seconds: float) -> None:
        ticks.append(seconds)
        if len(ticks) == 4:
            raise RuntimeError("end observation")

    monkeypatch.setattr(s.time, "sleep", tick)
    with pytest.raises(RuntimeError, match="end observation"):
        s.watch(policy)
    assert s.read(tmp_path / "heartbeat.json")["phase"] == "observing"
    assert not (tmp_path / "incidents").exists()
    assert any(url.endswith("/questions") for url in requests)


@pytest.mark.parametrize("status,worker", [("running", False), ("failed", True)])
def test_cancel_refuses_unsettled_state_or_live_worker(
    factory: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str, worker: bool
) -> None:
    import io
    from types import SimpleNamespace

    adapter = importlib.import_module("recover_infrastructure")
    auth = tmp_path / "auth.json"
    s.atomic(auth, {"servers": {"http://fixture": {"token": "fixture"}}})
    policy = {"server_url": "http://fixture", "auth_file": str(auth), "run_id": "RUN"}
    response = io.BytesIO(b"")
    response.status = 202  # type: ignore[attr-defined]
    monkeypatch.setattr(
        adapter.urllib.request,
        "build_opener",
        lambda *args: SimpleNamespace(open=lambda *a, **k: response),
    )
    monkeypatch.setattr(s, "native", lambda p: {"lifecycle": {"status": {"kind": status}}})
    monkeypatch.setattr(s, "worker_alive", lambda p: worker)
    monkeypatch.setattr(adapter.time, "sleep", lambda seconds: None)
    with pytest.raises(RuntimeError, match="not quiescent"):
        adapter.cancel_native(policy, tmp_path)
    assert s.read(tmp_path / "quiescence.json") == {
        "native_status": {"kind": status},
        "worker_alive": worker,
    }


def test_cancel_reconciles_previous_terminal_run_without_another_request(
    factory: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = importlib.import_module("recover_infrastructure")
    monkeypatch.setattr(
        s, "native", lambda p: {"lifecycle": {"status": {"kind": "failed", "reason": "cancelled"}}}
    )
    monkeypatch.setattr(s, "worker_alive", lambda p: False)
    # No credentials/server URL: returning without a duplicate request is required.
    adapter.cancel_native({"run_id": "RUN"}, tmp_path)
    assert s.read(tmp_path / "quiescence.json")["worker_alive"] is False


def test_cancel_waits_for_worker_exit_after_native_terminal_settlement(
    factory: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io
    from types import SimpleNamespace

    adapter = importlib.import_module("recover_infrastructure")
    auth = tmp_path / "auth.json"
    s.atomic(auth, {"servers": {"http://fixture": {"token": "fixture"}}})
    policy = {"server_url": "http://fixture", "auth_file": str(auth), "run_id": "RUN"}
    response = io.BytesIO(b"")
    response.status = 202  # type: ignore[attr-defined]
    monkeypatch.setattr(
        adapter.urllib.request,
        "build_opener",
        lambda *args: SimpleNamespace(open=lambda *a, **k: response),
    )
    ticks = []
    monkeypatch.setattr(
        s, "native", lambda p: {"lifecycle": {"status": {"kind": "failed" if ticks else "running"}}}
    )
    monkeypatch.setattr(s, "worker_alive", lambda p: len(ticks) < 35)
    monkeypatch.setattr(adapter.time, "sleep", lambda seconds: ticks.append(seconds))
    adapter.cancel_native(policy, tmp_path)
    assert len(ticks) == 35
    assert s.read(tmp_path / "quiescence.json")["worker_alive"] is False


def test_scope_and_user_drift_protect_original_files(tmp_path: Path) -> None:
    original = tmp_path / "original"
    candidate = tmp_path / "candidate"
    original.mkdir()
    candidate.mkdir()
    for directory in (original, candidate):
        (directory / "collector.py").write_text("old")
        (directory / "gate.py").write_text("immutable")
    before = repair.inventory(candidate)
    (candidate / "collector.py").write_text("repaired")
    changes = repair.changed_files(before, candidate, ["collector.py"])
    (original / "collector.py").write_text("new user work")
    with pytest.raises(ValueError, match="User work"):
        repair.apply_verified(original, candidate, before, changes)
    assert (original / "collector.py").read_text() == "new user work"
    (candidate / "gate.py").write_text("weakened gate")
    with pytest.raises(ValueError, match="scope"):
        repair.changed_files(before, candidate, ["collector.py"])


def test_verified_change_is_applied_after_comparison(tmp_path: Path) -> None:
    original = tmp_path / "original"
    candidate = tmp_path / "candidate"
    original.mkdir()
    candidate.mkdir()
    (original / "collector.py").write_text("old")
    (candidate / "collector.py").write_text("old")
    before = repair.inventory(candidate)
    (candidate / "collector.py").write_text("fixed")
    changes = repair.changed_files(before, candidate, ["collector.py"])
    repair.apply_verified(original, candidate, before, changes)
    assert (original / "collector.py").read_text() == "fixed"


def test_account_environment_cannot_select_api_billing(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "OPENAI_API_KEY",
        "CODEX_API_KEY",
        "OPENAI_BASE_URL",
        "CODEX_HOME",
        "OPENAI_IDENTITY_TOKEN_FILE",
        "OPENAI_FEDERATION_RULE_ID",
    ):
        monkeypatch.setenv(key, "must-not-inherit")
    assert not set(repair.account_environment()) & {
        "OPENAI_API_KEY",
        "CODEX_API_KEY",
        "OPENAI_BASE_URL",
        "CODEX_HOME",
        "OPENAI_IDENTITY_TOKEN_FILE",
        "OPENAI_FEDERATION_RULE_ID",
    }


def test_uncertain_codex_invocation_is_not_repeated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    s.atomic(tmp_path / "intent.json", {"status": "running"})
    monkeypatch.setattr(repair, "account_status", lambda: pytest.fail("must not invoke"))
    with pytest.raises(ValueError, match="uncertain"):
        repair.propose(tmp_path, tmp_path, "irrelevant")


@pytest.fixture
def factory(monkeypatch: pytest.MonkeyPatch) -> Any:
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "docs/handoff/someip-84/factory"))
    return importlib.import_module("start_overnight_queue")


def test_launch_never_starts_without_supervision(
    factory: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def missing(root: Path) -> dict:
        raise RuntimeError("no ready supervisor")

    monkeypatch.setattr(factory, "ensure_supervised", missing)
    with pytest.raises(RuntimeError, match="ready"):
        factory.start_supervised(lambda *args: calls.append(args), tmp_path, "RUN")
    assert calls == []


def test_supervisor_uses_persistent_enabled_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    unit = "score-fabric-supervisor-run123"
    policy = tmp_path / "private/policy.json"
    observer = tmp_path / "private/observer.py"
    s.atomic(policy, {"unit": unit, "observer": str(observer), "run_id": "RUN"})
    monkeypatch.setattr(s.pwd, "getpwuid", lambda uid: SimpleNamespace(pw_dir=str(tmp_path)))
    calls: list[list[str]] = []
    monkeypatch.setattr(s.subprocess, "run", lambda argv, **kw: calls.append(argv))
    monkeypatch.setattr(s, "require_ready", lambda path: {"run_id": "RUN"})
    assert s.start_service(policy) == {"run_id": "RUN"}
    path = tmp_path / ".config/systemd/user" / (unit + ".service")
    assert path.stat().st_mode & 0o777 == 0o600
    assert "WantedBy=default.target" in path.read_text()
    assert "WorkingDirectory=" + str(policy.parent) + "\n" in path.read_text()
    assert str(observer) in path.read_text() and str(policy) in path.read_text()
    assert calls == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", unit + ".service"],
    ]
    path.write_text("substituted observer")
    calls.clear()
    with pytest.raises(ValueError, match="differs"):
        s.start_service(policy)
    assert calls == []


def test_persistent_server_rejects_changed_runtime_or_config(
    factory: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = importlib.import_module("start_persistent_server")
    root = tmp_path / "someip84-server"
    root.mkdir()
    binary = tmp_path / "fabro"
    binary.write_text("pinned runtime")
    config = root / "settings.toml"
    config.write_text("pinned server settings")
    s.atomic(
        root / "bootstrap.json",
        {
            "source_commit": launcher.PIN,
            "binary_sha256": s.digest(binary),
            "config_sha256": s.digest(config),
            "dev_token": "private-test-token",
        },
    )
    s.atomic(root / "server-recovery-auth.json", {"session_secret": "private-test-signing"})
    monkeypatch.setattr(launcher, "STATE", tmp_path)
    monkeypatch.setattr(launcher, "BINARY", binary)
    monkeypatch.setattr(launcher.sys, "argv", ["launcher", str(root)])
    calls: list[Any] = []
    monkeypatch.setattr(launcher.os, "execve", lambda *args: calls.append(args))
    config.write_text("substituted config")
    with pytest.raises(ValueError, match="configuration changed"):
        launcher.main()
    assert not calls and not (root / "queue-server.json").exists()
    config.write_text("pinned server settings")
    binary.write_text("substituted executable")
    with pytest.raises(ValueError, match="runtime identity"):
        launcher.main()
    assert not calls
    binary.write_text("pinned runtime")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
    launcher.main()
    _, args, env = calls[0]
    assert "--storage-dir" in args and str(root / "storage") in args
    assert "OPENAI_API_KEY" not in env
    assert "/usr/sbin" in env["PATH"].split(":") and "/sbin" in env["PATH"].split(":")
    assert s.read(root / "queue-server.json")["pid"] == os.getpid()


@pytest.mark.parametrize("fault", [None, "bytes", "identity", "symlink", "duplicate"])
def test_reboot_source_reuse_requires_exact_preserved_identity_and_bytes(
    factory: Any, tmp_path: Path, fault: str | None
) -> None:
    import hashlib
    import json

    preparation = importlib.import_module("prepare_overnight_queue")
    previous = tmp_path / "workspace"
    context = previous / ".llm_tmp/context/obligations"
    context.mkdir(parents=True)
    source = context / "verification.rst"
    source.write_bytes(b"actual pinned source excerpt")
    record = {
        "id": "verification",
        "repository": "process_description",
        "commit": "a" * 40,
        "path": "guidance.rst",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    if fault == "bytes":
        source.write_bytes(b"altered source excerpt")
    if fault == "identity":
        record["commit"] = "b" * 40
    if fault == "symlink":
        target = tmp_path / "other.rst"
        source.rename(target)
        source.symlink_to(target)
    records = [record, record] if fault == "duplicate" else [record]
    (context / "source-index.json").write_text(json.dumps(records))
    args = (
        "verification",
        "process_description",
        "a" * 40,
        "guidance.rst",
        tmp_path / "missing",
        previous,
    )
    if fault:
        with pytest.raises(ValueError):
            preparation.obligation_source(*args)
    else:
        assert preparation.obligation_source(*args) == (
            b"actual pinned source excerpt",
            "preserved_pinned_export",
        )
        with pytest.raises(ValueError, match="Missing pinned"):
            preparation.obligation_source(*args[:-1], None)


def test_launch_rejects_supervisor_for_another_run(
    factory: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    monkeypatch.setattr(factory, "ensure_supervised", lambda root: {"run_id": "OTHER"})
    with pytest.raises(ValueError):
        factory.start_supervised(lambda *args: calls.append(args), tmp_path, "RUN")
    assert calls == []


def test_stage_hook_refuses_missing_required_supervisor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "docs/handoff/someip-84/factory"))
    monkeypatch.setitem(__import__("sys").modules, "supervision", s)
    hooks = importlib.import_module("overnight_hooks")
    s.atomic(
        tmp_path / "overnight-policy.json",
        {"supervision_required": True, "nodes": {}, "deadline_epoch": None, "single_pass": True},
    )
    monkeypatch.setattr(hooks.sys, "argv", ["hook", str(tmp_path), "guard"])
    monkeypatch.setattr(hooks.sys, "stdin", io.StringIO("{}"))
    assert hooks.main() == 2


def test_repeated_storage_write_failure_dispatches_repair_even_with_healthy_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    root = tmp_path / "bound-workspace"
    root.mkdir()
    state = tmp_path / "private"
    state.mkdir()
    policy = state / "policy.json"
    s.atomic(
        policy,
        {
            "run_id": "RUN",
            "controls": {},
            "prepared_root": str(root),
            "unit": "fixture",
            "attached_at": 0,
            "workspace_device": root.stat().st_dev,
            "repair_command": ["fixture-repair"],
        },
    )
    record = {"id": "RUN", "lifecycle": {"status": {"kind": "running"}}}
    monkeypatch.setattr(s, "native", lambda p, suffix="": {"data": []} if suffix else record)
    monkeypatch.setattr(s, "worker_alive", lambda p: True)
    original = Path.stat

    def broken(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == root:
            raise OSError(30, "Read-only file system")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", broken)
    calls = []

    class Child:
        returncode = None

        def poll(self) -> None:
            return None

    monkeypatch.setattr(subprocess, "Popen", lambda argv, **kwargs: calls.append(argv) or Child())
    ticks = []

    def tick(seconds: float) -> None:
        ticks.append(seconds)
        if len(ticks) == 4:
            raise RuntimeError("stop fixture observer")

    monkeypatch.setattr(s.time, "sleep", tick)
    with pytest.raises(RuntimeError, match="stop fixture"):
        s.watch(policy)
    assert len(calls) == 1 and calls[0][0] == "fixture-repair"
    incident = s.read(Path(calls[0][-1]))
    assert incident["kind"] == "observer_dependency_failure"
    assert incident["measurement"]["error_type"] == "OSError"


@pytest.mark.parametrize("lost_start_response", [False, True])
def test_recovery_preserves_then_verifies_then_starts_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lost_start_response: bool,
) -> None:
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "docs/handoff/someip-84/factory"))
    adapter = importlib.import_module("recover_infrastructure")
    original = tmp_path / "fabric"
    original.mkdir()
    (original / "collector.py").write_text("broken")
    bound = tmp_path / "old-native-root"
    bound.mkdir()
    evidence = tmp_path / "private-incident"
    evidence.mkdir()
    incident = evidence / "incident.json"
    s.atomic(incident, {"run_id": "OLD", "kind": "worker_missing"})
    policy = evidence / "policy.json"
    s.atomic(
        policy,
        {
            "run_id": "OLD",
            "prepared_root": str(bound),
            "runtime_policy": {"image_id": "pinned-image", "deadline_epoch": None},
            "single_pass": True,
            "all_obligations": True,
        },
    )
    scratch = tmp_path / "repair"
    scratch.mkdir()
    successor = tmp_path / "successor"
    calls = []
    monkeypatch.setattr(adapter, "REPO", original)
    monkeypatch.setattr(adapter, "ALLOWED", ["collector.py"])
    monkeypatch.setattr(adapter, "owned_container", lambda p: "owned")
    monkeypatch.setattr(adapter, "restore_server", lambda *args: None)
    monkeypatch.setattr(adapter, "cancel_native", lambda *args: calls.append("cancel"))
    monkeypatch.setattr(adapter, "new_run_root", lambda prefix: scratch)

    def snapshot(container: str, destination: Path) -> None:
        calls.append("preserve")
        (destination / "implementation.cpp").write_text("latest source")

    monkeypatch.setattr(adapter, "snapshot_workspace", snapshot)

    def proposal(work: Path, attempt: Path, prompt: str) -> dict:
        calls.append("codex")
        assert (scratch / "preserved-workspace/implementation.cpp").read_text() == "latest source"
        (work / "collector.py").write_text("fixed")
        return {"status": "ready", "summary": "fixture repair"}

    monkeypatch.setattr(adapter, "propose", proposal)

    def verify(work: Path, attempt: Path) -> None:
        calls.append("verify")
        assert (original / "collector.py").read_text() == "broken"
        assert (work / "collector.py").read_text() == "fixed"

    monkeypatch.setattr(adapter, "verification", verify)

    def command(evidence: Path, label: str, args: list[str], **kwargs: Any) -> str:
        calls.append(label)
        if label == "prepare-successor":
            assert (original / "collector.py").read_text() == "fixed"
            successor.mkdir()
            s.atomic(successor / "overnight-queue.json", {"status": "prepared_not_submitted"})
            source = args[args.index("--preserve-from") + 1]
            assert (Path(source) / "implementation.cpp").read_text() == "latest source"
            return str(successor) + "\n"
        if label == "start-successor":
            (successor / "native-run-id").write_text("NEW\n")
            s.atomic(successor / "supervision-binding.json", {"policy": str(policy)})
            s.atomic(
                successor / "overnight-queue.json",
                {"status": "native_submitted" if lost_start_response else "native_start_requested"},
            )
            if lost_start_response:
                raise RuntimeError("lost CLI response")
        return ""

    monkeypatch.setattr(adapter, "command", command)
    monkeypatch.setattr(s, "require_ready", lambda *args, **kwargs: {"run_id": "NEW"})
    monkeypatch.setattr(s, "native", lambda *args: {"lifecycle": {"status": {"kind": "running"}}})
    adapter.recover(policy, incident)
    assert s.read(evidence / "result.json")["successor_run_id"] == "NEW"
    assert (
        calls.index("preserve")
        < calls.index("codex")
        < calls.index("verify")
        < calls.index("start-successor")
    )
    adapter.recover(policy, incident)
    assert calls.count("codex") == 1 and calls.count("start-successor") == 1
    assert (scratch / "preserved-workspace/implementation.cpp").read_text() == "latest source"


@pytest.mark.parametrize("recorded_launch", [False, True])
def test_server_restore_pauses_workers_waits_and_reconciles_intent(
    factory: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded_launch: bool
) -> None:
    adapter = importlib.import_module("recover_infrastructure")
    server_root = tmp_path / "server"
    server_root.mkdir()
    s.atomic(server_root / "queue-server.json", {"pid": 1})
    s.atomic(server_root / "server-recovery-auth.json", {"session_secret": "retained-key"})
    evidence = tmp_path / "incident"
    evidence.mkdir()
    binary = tmp_path / "fabro"
    binary.write_text("pinned")
    config = tmp_path / "frozen.toml"
    config.write_text('[server.auth]\nmode = "development"\n')
    auth = tmp_path / "auth.json"
    s.atomic(auth, {"servers": {"http://local": {"token": "private-token"}}})
    policy = {
        "server_url": "http://local",
        "auth_file": str(auth),
        "server_restore": {
            "pid": 1,
            "process_identity": "old",
            "root": str(server_root),
            "config": str(config),
            "binary_sha256": s.digest(binary),
        },
    }
    monkeypatch.setattr(adapter, "BINARY", binary)
    if recorded_launch:
        s.atomic(
            evidence / "server-restore-intent.json",
            {
                "pid": 22,
                "process_identity": "recorded",
                "capacity": 0,
            },
        )
    monkeypatch.setattr(s, "same_process", lambda pid, identity: pid == 22)
    monkeypatch.setattr(s, "process_identity", lambda pid: "recorded")
    monkeypatch.setattr(adapter.time, "sleep", lambda seconds: None)
    observations = []

    def native(policy: dict) -> dict:
        observations.append(True)
        if len(observations) < 45:
            raise OSError("startup reconciliation is slow")
        return {"id": "OLD"}

    monkeypatch.setattr(s, "native", native)
    launches = []

    class Process:
        pid = 22

        def poll(self) -> None:
            return None

    def launch(args: list, **kwargs: Any) -> Process:
        launches.append(args)
        assert args[args.index("--max-concurrent-runs") + 1] == "0"
        assert "max_concurrent_runs = 0" in Path(args[args.index("--config") + 1]).read_text()
        assert kwargs["env"]["SESSION_SECRET"] == "retained-key"
        return Process()

    class Probe:
        def __enter__(self) -> "Probe":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def bind(self, address: tuple) -> None:
            assert address == ("127.0.0.1", 43916)

        def setsockopt(self, *args: Any) -> None:
            pass

    monkeypatch.setattr(socket, "socket", lambda: Probe())
    monkeypatch.setattr(adapter.subprocess, "Popen", launch)
    adapter.restore_server(policy, evidence)
    assert len(observations) == 45
    assert len(launches) == (0 if recorded_launch else 1)
    assert s.read(evidence / "server-probe.json") == {"error_type": "OSError"}
    assert config.read_text() == '[server.auth]\nmode = "development"\n'


def test_recovery_config_changes_only_scheduler_capacity(factory: Any, tmp_path: Path) -> None:
    adapter = importlib.import_module("recover_infrastructure")
    baseline = tmp_path / "original.toml"
    baseline.write_text(
        '[server.scheduler]\nmax_concurrent_runs = 4\n[server.auth]\nmode = "development"\n'
    )
    result = adapter.recovery_config(baseline, tmp_path / "maintenance.toml", 0)
    config = adapter.tomllib.loads(result.read_text())
    assert config == {
        "server": {"scheduler": {"max_concurrent_runs": 0}, "auth": {"mode": "development"}}
    }
    assert "max_concurrent_runs = 4" in baseline.read_text()


def test_maintenance_capacity_is_not_enabled_before_preservation(
    factory: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = importlib.import_module("recover_infrastructure")
    s.atomic(
        tmp_path / "server-restore-intent.json",
        {
            "pid": 22,
            "process_identity": "owned",
            "capacity": 0,
        },
    )
    signals = []
    identities = iter([True, False])
    monkeypatch.setattr(s, "same_process", lambda *args: next(identities))
    monkeypatch.setattr(adapter.os, "kill", lambda *args: signals.append(args))
    launches = []
    monkeypatch.setattr(adapter, "restore_server", lambda *args, **kw: launches.append(kw))
    adapter.enable_restored_server({}, tmp_path)
    assert signals == [(22, adapter.signal.SIGTERM)]
    assert launches == [{"capacity": 1}]
