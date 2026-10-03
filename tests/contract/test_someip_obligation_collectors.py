"""Failure preservation, deadline and ownership checks for the operational collectors."""

from __future__ import annotations

import importlib
import json
import shutil
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2] / "docs/handoff/someip-84/factory"


@pytest.fixture
def collector(monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    return importlib.import_module("collect_obligations")


def test_command_failure_preserves_outputs_and_omits_provider_credentials(
    collector, tmp_path, monkeypatch
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-placeholder-never-forwarded")
    out = tmp_path / "out"
    out.mkdir()
    runner = collector.Commands(tmp_path, out, tmp_path, time.time() + 30)
    code = runner.run(
        "failure",
        [
            sys.executable,
            "-c",
            "import os,sys; print('DEEPSEEK_API_KEY' in os.environ); sys.exit(7)",
        ],
    )
    assert code == 7
    assert (out / "failure.stdout").read_text().strip() == "False"
    assert json.loads((out / "failure.command.json").read_text())["exit_code"] == 7


def test_deadline_stops_owned_command(collector, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    runner = collector.Commands(tmp_path, out, tmp_path, time.time() + 12)
    code = runner.run("timeout", [sys.executable, "-c", "import time; time.sleep(30)"], 1)
    assert code == 124
    assert "process group stopped" in runner.records[0]["reason"]


def test_foreign_container_rejected_before_copy(collector, tmp_path, monkeypatch):
    run = "01M3WSTF1DAJA248NQ5QQGQG52"
    (tmp_path / "native-run-id").write_text(run)
    calls = []

    def docker(*args):
        calls.append(args)
        if args[0] == "ps":
            return "foreign"
        return json.dumps(
            [
                {
                    "Image": "sha256:expected",
                    "NetworkSettings": {"Networks": {}},
                    "Config": {"Labels": {"petri.run": "FOREIGN"}},
                }
            ]
        )

    monkeypatch.setattr(collector, "docker", docker)
    with pytest.raises(ValueError, match="identity"):
        collector.snapshot(tmp_path, {"image_id": "sha256:expected"}, tmp_path)
    assert not any(call[0] == "cp" for call in calls)


def test_checkpoint_metadata_excluded_but_engineering_drift_rejected(
    collector, tmp_path, monkeypatch
):
    run = "01M3WSTF1DAJA248NQ5QQGQG52"
    (tmp_path / "native-run-id").write_text(run)
    target = tmp_path / "target"
    target.mkdir()
    (target / "README.md").write_text("unchanged")
    container_tree = tmp_path / "container"
    shutil.copytree(target, container_tree)
    (container_tree / ".git").mkdir()
    (container_tree / ".git/HEAD").write_text("runtime checkpoint")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    (tmp_path / "measurement-inputs.json").write_text(
        json.dumps(
            {
                "baseline": str(target),
                "source_manifest": str(manifest),
                "googletest": str(target),
                "googletest_manifest": str(manifest),
                "controls": [],
            }
        )
    )

    def docker(*args):
        if args[0] == "ps":
            return "owned"
        if args[0] == "inspect":
            return json.dumps(
                [
                    {
                        "Image": "sha256:expected",
                        "NetworkSettings": {"Networks": {}},
                        "Config": {"Labels": {"petri.run": run}},
                    }
                ]
            )
        shutil.copytree(container_tree, args[2], dirs_exist_ok=True)
        return ""

    monkeypatch.setattr(collector, "docker", docker)
    monkeypatch.setattr(collector, "verify_tree", lambda *_: None)
    monkeypatch.setattr(
        collector,
        "snapshot_workspace",
        lambda _container, dest: shutil.copytree(container_tree, dest, dirs_exist_ok=True),
    )
    policy = {"image_id": "sha256:expected", "source_write_paths": []}
    first = tmp_path / "first"
    first.mkdir()
    collector.snapshot(tmp_path, policy, first)
    (container_tree / "README.md").write_text("unauthorized edit")
    second = tmp_path / "second"
    second.mkdir()
    with pytest.raises(ValueError, match="Out-of-scope source change"):
        collector.snapshot(tmp_path, policy, second)


def test_collection_completion_does_not_hide_tool_failure(collector, tmp_path, monkeypatch):
    source = tmp_path / "fixture"
    (source / "score").mkdir(parents=True)
    (source / "score/example.cpp").write_text("int x;")
    gtest = tmp_path / "gtest"
    gtest.mkdir()
    (tmp_path / "measurement-inputs.json").write_text(json.dumps({"googletest": str(gtest)}))
    monkeypatch.setattr(collector, "snapshot", lambda *_: (source, "owned"))
    monkeypatch.setattr(collector, "docker", lambda *_: "")

    def execute(_check, commands, _root, result):
        commands.records.append({"exit_code": 2, "label": "native-tool", "argv": ["fixed"]})
        result["blockers"].append("unavailable native configuration")

    monkeypatch.setattr(collector, "execute", execute)
    collector.collect(
        tmp_path,
        {"deadline_epoch": time.time() + 900},
        {"mode": "obligation:native_lint", "ref": "collect_native_lint"},
    )
    record = json.loads((tmp_path / "latest-obligation.json").read_text())
    assert record["status"] == "findings_or_execution_failure"
    assert record["commands"][0]["exit_code"] == 2
    assert record["engineering_acceptance"] == "pending"
    assert (Path(record["result_path"]).parent / "feedback/collection-result").read_text() == "0\n"


def test_archive_requires_all_collectors_and_current_source(collector, tmp_path):
    source = tmp_path / "source"
    (source / "score").mkdir(parents=True)
    (source / "score/example.cpp").write_text("int current;")
    out = tmp_path / "out"
    out.mkdir()
    previous = tmp_path / "obligation-results/earlier"
    previous.mkdir(parents=True)
    (previous / "result.json").write_text(
        json.dumps(
            {
                "check": "compiler_diagnostics",
                "status": "completed",
                "result_path": "earlier",
                "source_hashes": {"score/example.cpp": "stale"},
                "blockers": [],
            }
        )
    )
    runner = collector.Commands(tmp_path, out, source, time.time() + 60)
    result = {"blockers": []}
    collector.execute("verification_report", runner, tmp_path, result)
    assert result["missing_checks"]
    assert not result["results"][0]["matches_current_source"]
    assert "Independent PR approval pending" in result["blockers"]


def test_unknown_collector_cannot_execute_commands(collector, tmp_path):
    with pytest.raises(ValueError, match="Unknown obligation collector"):
        collector.collect(tmp_path, {}, {"mode": "obligation:arbitrary_shell"})


def test_rework_repeats_only_after_source_progress(collector, tmp_path):
    source = tmp_path / "source"
    (source / "score").mkdir(parents=True)
    unit = source / "score/example.cpp"
    unit.write_text("int before;")
    state = tmp_path / "rework-source-hashes.json"
    state.write_text(json.dumps(collector.source_identity(source)))
    unit.write_text("int after;")
    runner = collector.Commands(tmp_path, tmp_path, source, time.time() + 30)
    first = {"blockers": []}
    collector.execute("rework_progress", runner, tmp_path, first)
    assert first["rework_requested"]
    second = {"blockers": []}
    collector.execute("rework_progress", runner, tmp_path, second)
    assert not second["rework_requested"]
    assert "pending" in second["stop_reason"]


def test_recollection_reuses_only_identical_source_and_collector(collector, tmp_path, monkeypatch):
    source = tmp_path / "fixture"
    (source / "score").mkdir(parents=True)
    unit = source / "score/example.cpp"
    unit.write_text("int before;")
    gtest = tmp_path / "gtest"
    gtest.mkdir()
    (tmp_path / "measurement-inputs.json").write_text(json.dumps({"googletest": str(gtest)}))
    monkeypatch.setattr(collector, "snapshot", lambda *_: (source, "owned"))
    monkeypatch.setattr(collector, "docker", lambda *_: "")
    identity = {"fixed-tool": "one"}
    monkeypatch.setattr(collector, "collector_identity", lambda: identity)
    executions = []

    def execute(check, commands, _root, result):
        executions.append(check)
        commands.records.append({"exit_code": 2, "label": "native-tool", "argv": ["fixed"]})
        result["blockers"].append("native execution failed")

    monkeypatch.setattr(collector, "execute", execute)
    policy = {"deadline_epoch": time.time() + 900}
    mode = "obligation:native_lint"
    collector.collect(tmp_path, policy, {"mode": mode, "ref": "collect_native_lint"})
    collector.collect(tmp_path, policy, {"mode": mode, "ref": "recollect_native_lint"})
    reused = json.loads((tmp_path / "latest-obligation.json").read_text())
    assert reused["reused_from"]
    assert reused["commands"][0]["exit_code"] == 2
    assert len(executions) == 1
    unit.write_text("int after;")
    collector.collect(tmp_path, policy, {"mode": mode, "ref": "recollect_native_lint"})
    assert len(executions) == 2
    identity["fixed-tool"] = "two"
    collector.collect(tmp_path, policy, {"mode": mode, "ref": "recollect_native_lint"})
    assert len(executions) == 3


def test_single_pass_keeps_blockers_and_does_not_repeat_changed_source(
    collector, tmp_path, monkeypatch
):
    source = tmp_path / "source"
    (source / "score").mkdir(parents=True)
    (source / "score/example.cpp").write_text("int changed;")
    gtest = tmp_path / "gtest"
    gtest.mkdir()
    (tmp_path / "measurement-inputs.json").write_text(json.dumps({"googletest": str(gtest)}))
    monkeypatch.setattr(collector, "snapshot", lambda *_: (source, "owned"))
    monkeypatch.setattr(collector, "docker", lambda *_: "")

    def execute(_check, commands, _root, result):
        result.update(source_changed_this_round=True, rework_requested=True)
        result["blockers"].append("unresolved finding")

    monkeypatch.setattr(collector, "execute", execute)
    collector.collect(
        tmp_path,
        {"deadline_epoch": None, "single_pass": True},
        {"mode": "obligation:rework_progress", "ref": "collect_rework_progress"},
    )
    result = json.loads((tmp_path / "latest-obligation.json").read_text())
    assert result["source_changed_this_round"]
    assert not result["rework_requested"]
    assert result["blockers"] == ["unresolved finding"]
    assert (Path(result["result_path"]).parent / "feedback/collection-result").read_text() == "0\n"


def test_single_pass_hook_admits_only_known_nodes_and_events(monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    hooks = importlib.import_module("overnight_hooks")
    policy = {"single_pass": True, "deadline_epoch": None, "nodes": {"known": {}}}
    assert hooks.admissible(policy, {"node_id": "known", "event": "stage_start"}, time.time())
    assert not hooks.admissible(policy, {"node_id": "unknown", "event": "stage_start"}, time.time())
    assert not hooks.admissible(policy, {"node_id": "known", "event": "unknown"}, time.time())


def test_native_workspace_reuses_outputs_and_rejects_unexpected_source_drift(
    collector, tmp_path, monkeypatch
):
    source = tmp_path / "source"
    (source / "score").mkdir(parents=True)
    unit = source / "score/example.cpp"
    unit.write_text("int before;")
    (tmp_path / "overnight-policy.json").write_text(
        json.dumps({"source_write_paths": ["/workspace/score/example.cpp"]})
    )
    called = []
    monkeypatch.setattr(collector, "bazel", lambda c, *_: called.append(c.source))
    for contents in ("int before;", "int after;"):
        unit.write_text(contents)
        c = collector.Commands(tmp_path, tmp_path, source, time.time() + 60)
        collector.execute("native_build", c, tmp_path, {"blockers": []})
        assert (c.source / "score/example.cpp").read_text() == contents
    assert called == [tmp_path / "native-workspace"] * 2
    invocations = []
    monkeypatch.setattr(
        collector,
        "bazel",
        lambda _c, _root, _label, _op, args, _timeout: invocations.append(args),
    )
    c = collector.Commands(tmp_path, tmp_path, source, time.time() + 60)
    collector.execute("native_traceability", c, tmp_path, {"blockers": []})
    assert str(tmp_path / "native-workspace/_build/metrics.json") in invocations[-1]
    (tmp_path / "native-workspace/score/unexpected.cpp").write_text("drift")
    c = collector.Commands(tmp_path, tmp_path, source, time.time() + 60)
    with pytest.raises(ValueError, match="source drift"):
        collector.execute("native_build", c, tmp_path, {"blockers": []})
