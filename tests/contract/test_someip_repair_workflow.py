"""Repair routing uses real results and keeps human closure outside Fabro."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2] / "docs/handoff/someip-84/factory"


@pytest.fixture
def repair(monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    return importlib.import_module("repair_workflow")


def test_collection_success_does_not_hide_tool_failure(repair):
    assert not repair.passed(
        {"status": "findings_or_execution_failure", "commands": [{"exit_code": 3}]}
    )
    assert not repair.passed({"status": "completed", "commands": []})
    assert repair.passed({"status": "completed", "commands": [{"exit_code": 0}]})


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Executed 0 out of 6 tests",
        "Executed 5 out of 6 tests: 5 tests pass.",
        "Executed 6 out of 6 tests: 5 tests pass and 1 fails.",
        "6 tests pass. (cached)",
    ],
)
def test_integration_requires_all_real_native_tests(repair, text):
    assert not repair.integration_passed(text)


def test_six_executed_integration_tests_are_required(repair):
    assert repair.integration_passed("Executed 6 out of 6 tests: 6 tests pass.")


def test_orchestration_requires_failure_and_bound(repair, tmp_path):
    out = tmp_path / "obligation-results" / "format_precommit-1"
    out.mkdir(parents=True)
    (out / "result.json").write_text(
        json.dumps(
            {
                "status": "findings_or_execution_failure",
                "commands": [{"exit_code": 1}],
                "source_hashes": {},
            }
        )
    )
    first = repair.diagnose(tmp_path, "format_precommit")
    assert first["attempt"] == 1
    assert first["repair"] == "candidate_formatting"
    with pytest.raises(ValueError, match="did not resolve"):
        repair.diagnose(tmp_path, "format_precommit")
    for i in (2, 3):
        (tmp_path / "repair-history" / f"format_precommit-{i}.json").write_text("{}")
    with pytest.raises(ValueError, match="exhausted"):
        repair.diagnose(tmp_path, "format_precommit")


def test_graph_has_orchestrators_loops_and_no_human(repair):
    actions, edges, loops = repair.graph_parts({}, {})
    assert all(action["type"] != "human" for action in actions)
    assert any(action["ref"].startswith("orchestrate_") for action in actions)
    assert {loop["id"] for loop in loops} == {
        "format_precommit",
        "native_performance",
        "native_integration",
    }
    for check in ("format_precommit", "native_performance", "native_integration"):
        assert any(
            e["source"] == "check_" + check
            and e["target"] == "orchestrate_" + check
            and e["outcome"] == "failure"
            for e in edges
        )
        assert any(
            e["source"] == "repair_" + check and e["target"] == "check_" + check for e in edges
        )
    assert (
        next(a for a in actions if a["ref"] == "external_review_packet")["model_capability"]
        == "none"
    )


def test_source_changes_cannot_reuse_old_pass(repair):
    prior = {
        "status": "completed",
        "commands": [{"exit_code": 0}],
        "source_hashes": {"unit.cpp": "old"},
    }
    assert not repair.current_pass(prior, {"unit.cpp": "new"})
    assert repair.current_pass(prior, {"unit.cpp": "old"})


def test_capture_failure_selects_different_repair(repair, tmp_path):
    out = tmp_path / "obligation-results/native_integration-1"
    out.mkdir(parents=True)
    (out / "result.json").write_text(
        json.dumps({"status": "findings_or_execution_failure", "commands": [{"exit_code": 3}]})
    )
    (out / "qemu.stdout").write_text(
        "Couldn't change to 'root' uid=0 gid=0: Operation not permitted"
    )
    assert repair.diagnose(tmp_path, "native_integration")["repair"] == "namespace_capture_identity"
    with pytest.raises(ValueError, match="did not resolve"):
        repair.diagnose(tmp_path, "native_integration")


def test_blocked_packet_fails_native_hook(tmp_path, monkeypatch):
    import io
    import sys

    monkeypatch.syspath_prepend(str(HERE))
    hooks = importlib.import_module("repair_hooks")
    from score_sw_fabric.runtime import supervision

    monkeypatch.setitem(sys.modules, "supervision", supervision)
    (tmp_path / "overnight-policy.json").write_text(
        json.dumps({"nodes": {"terminal": {"mode": "unresolved", "ref": "unresolved_packet"}}})
    )
    (tmp_path / "supervision-binding.json").write_text('{"policy": "fixture-only"}')
    (tmp_path / "native-run-id").write_text("fixture-only")
    monkeypatch.setattr(hooks, "validate_run_root", lambda _p: None)
    monkeypatch.setattr(supervision, "require_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(hooks, "packet", lambda *_a: {"technical_completion": "blocked"})
    observed = []
    monkeypatch.setattr(hooks, "feedback", lambda *_a: observed.append(_a[-1]))
    monkeypatch.setattr(sys, "argv", ["hook", str(tmp_path), "measure"])
    monkeypatch.setattr(
        sys, "stdin", io.StringIO('{"node_id": "terminal", "event": "stage_start"}')
    )
    assert hooks.main() == 2
    assert observed == [False]


def test_initial_failure_remains_original_and_diagnostic_tampering_blocks(repair, tmp_path):
    import hashlib

    prior = tmp_path / "prior"
    prior.mkdir()
    result = prior / "result.json"
    result.write_text('{"status":"findings_or_execution_failure","commands":[{"exit_code":3}]}')
    log = prior / "qemu.stdout"
    log.write_text("Original capture failure")
    (tmp_path / "initial-failure-evidence.json").write_text(
        json.dumps(
            {
                "native_integration": {
                    "path": str(result),
                    "sha256": hashlib.sha256(result.read_bytes()).hexdigest(),
                    "logs_sha256": {str(log): hashlib.sha256(log.read_bytes()).hexdigest()},
                }
            }
        )
    )
    path, value = repair.latest(tmp_path, "native_integration")
    assert path == result and not repair.passed(value)
    log.write_text("Changed diagnostic")
    with pytest.raises(ValueError, match="diagnostic identity"):
        repair.latest(tmp_path, "native_integration")


def test_failed_same_run_workflow_never_dispatches_successor(tmp_path, monkeypatch):
    import time

    from score_sw_fabric.runtime import supervision as s

    policy = tmp_path / "policy.json"
    s.atomic(
        policy,
        {
            "run_id": "fixture-only",
            "controls": {},
            "unit": "fixture-observer",
            "attached_at": time.time(),
            "runtime_policy": {"in_run_repair": True},
            "prepared_root": str(tmp_path),
        },
    )
    monkeypatch.setattr(
        s,
        "native",
        lambda _p, suffix="": (
            {"data": []}
            if suffix
            else {"lifecycle": {"status": {"kind": "failed", "reason": "workflow_error"}}}
        ),
    )
    monkeypatch.setattr(s, "worker_alive", lambda _p: False)
    monkeypatch.setattr(s.time, "sleep", lambda _v: pytest.fail("Observer attempted repair/retry"))
    s.watch(policy)
    state = s.read(tmp_path / "observer-state.json")
    assert state["phase"] == "finished"
    assert state["native_status"] == "failed"
    assert not (tmp_path / "incidents").exists()


def test_frozen_hooks_import_without_preparation_builder(tmp_path):
    import shutil
    import subprocess
    import sys

    from score_sw_fabric import storage, workspace_transfer
    from score_sw_fabric.runtime import supervision

    for name in (
        "repair_hooks.py",
        "repair_workflow.py",
        "perf_bridge.py",
        "collect_obligations.py",
        "evidence.py",
        "integration_evidence.py",
        "queue_tools.py",
        "native_git.py",
        "obligations.py",
        "measure.py",
        "isolate_docker.py",
    ):
        shutil.copyfile(HERE / name, tmp_path / name)
    for module in (supervision, storage, workspace_transfer):
        shutil.copyfile(module.__file__, tmp_path / (module.__name__.split(".")[-1] + ".py"))
    result = subprocess.run(
        [sys.executable, "-c", "import repair_hooks, perf_bridge"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "prepare.py").exists()


@pytest.mark.parametrize("invalid", ["changed_bytes", "failed_recording", "wrong_owner", "escape"])
def test_perf_reader_refuses_unbound_recording(tmp_path, monkeypatch, invalid):
    import hashlib

    monkeypatch.syspath_prepend(str(HERE))
    bridge = importlib.import_module("perf_bridge")
    storage = importlib.import_module("storage")
    monkeypatch.setattr(storage, "validate_run_root", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        bridge.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("Unbound recording launched privileged helper"),
    )
    root = tmp_path / "run"
    root.mkdir()
    (root / "perf-invocations").mkdir()
    (root / "perf-bridge.json").write_text(
        json.dumps(
            {
                "scope": str(root),
                "storage_owner_home": str(tmp_path),
                "mounts": [],
                "build_root": str(root),
                "output_owner_uid": 1000,
            }
        )
    )
    dataset = (tmp_path if invalid == "escape" else root) / "native.data"
    dataset.write_bytes(b"original measured dataset")
    receipt = {
        "sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "perf_exit_code": 0,
        "host_uid": 1000,
    }
    if invalid == "changed_bytes":
        dataset.write_bytes(b"substituted dataset")
    elif invalid == "failed_recording":
        receipt["perf_exit_code"] = 255
    elif invalid == "wrong_owner":
        receipt["host_uid"] = 0
    Path(str(dataset) + ".receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="escapes owned run|differs from successful"):
        bridge.execute(root, ["script", "-i", str(dataset)])
