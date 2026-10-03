"""Selective reruns and real disposable Git metadata preserve source and fail closed."""

from __future__ import annotations

import importlib
import json
import subprocess
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2] / "docs/handoff/someip-84/factory"


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    return importlib.import_module("collect_obligations"), importlib.import_module("native_git")


def test_missing_native_lint_does_not_repeat_passing_ruff(modules, tmp_path, monkeypatch):
    collector, _ = modules
    source = tmp_path / "source"
    (source / "score").mkdir(parents=True)
    (source / "score/unit.cpp").write_text("int x;")
    commands = collector.Commands(
        tmp_path, tmp_path, source, time.time() + 30, selected=["clang-tidy"]
    )
    called = []
    monkeypatch.setattr(collector, "bazel", lambda _c, _r, label, *_args: called.append(label))
    collector.execute("native_lint", commands, tmp_path, {"blockers": []})
    assert called == ["clang-tidy"]


def test_format_timeout_rerun_omits_other_completed_checks(modules, tmp_path, monkeypatch):
    collector, _ = modules
    commands = collector.Commands(
        tmp_path, tmp_path, tmp_path, time.time() + 30, selected=["format"]
    )
    called = []
    monkeypatch.setattr(commands, "run", lambda label, *_args: called.append(label) or 0)
    monkeypatch.setattr(collector, "bazel", lambda _c, _r, label, *_args: called.append(label))
    collector.execute("format_precommit", commands, tmp_path, {"blockers": []})
    assert called == ["git-init", "git-add", "format"]


def test_invalid_timeout_refuses_before_process_launch(modules, tmp_path):
    collector, _ = modules
    commands = collector.Commands(
        tmp_path, tmp_path, tmp_path, time.time() + 30, timeouts={"bad": 7201}
    )
    with pytest.raises(ValueError, match="timeout"):
        commands.run("bad", ["/bin/true"])
    assert not (tmp_path / "bad.command.json").exists()


def test_genuine_git_baseline_retains_dirty_candidate_and_disables_hooks(modules, tmp_path):
    collector, git = modules
    baseline = tmp_path / "fixture-baseline"
    baseline.mkdir()
    (baseline / "unit.cpp").write_text("int before;")
    prefix = ["/usr/bin/git", "-c", "core.hooksPath=/dev/null"]

    def invoke(*args):
        return subprocess.check_output(
            [*prefix, *args], cwd=baseline, text=True, stderr=subprocess.DEVNULL
        ).strip()

    invoke("init")
    invoke("add", "unit.cpp")
    invoke(
        "-c",
        "user.name=Explicit fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "Fixture baseline; not engineering evidence",
    )
    commit, tree = invoke("rev-parse", "HEAD"), invoke("rev-parse", "HEAD^{tree}")
    bundle = tmp_path / "native-git-baseline.bundle"
    invoke("bundle", "create", str(bundle), "HEAD")
    (tmp_path / "native-git-baseline.json").write_text(
        json.dumps(
            {
                "repository": "eclipse-score/inc_someip_gateway",
                "commit": commit,
                "tree": tree,
                "bundle_sha256": collector.digest(bundle),
            }
        )
    )
    source = tmp_path / "candidate"
    source.mkdir()
    (source / "unit.cpp").write_text("int changed_candidate;")
    out = tmp_path / "out"
    out.mkdir()
    commands = collector.Commands(tmp_path, out, source, time.time() + 60)
    git.restore_native_git(commands, tmp_path, {})
    assert (source / "unit.cpp").read_text() == "int changed_candidate;"
    status = subprocess.check_output([*prefix, "status", "--porcelain"], cwd=source, text=True)
    assert " M unit.cpp" in status
    assert (
        subprocess.check_output(
            [*prefix, "config", "--local", "core.hooksPath"], cwd=source, text=True
        ).strip()
        == "/dev/null"
    )
    bundle.write_bytes(b"substituted bundle")
    with pytest.raises(ValueError, match="bundle changed"):
        git.restore_native_git(commands, tmp_path, {})


def test_additional_tool_volume_is_validated(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    tools = importlib.import_module("queue_tools")
    manifest = tmp_path / "manifest.json"
    primary, additional = tmp_path / "primary", tmp_path / "additional"
    primary.mkdir()
    additional.mkdir()
    for root in (primary, additional):
        (root / "storage-selection.json").write_text("{}")
    manifest.write_text(
        json.dumps(
            {
                "storage_root": str(primary),
                "additional_storage_roots": [str(additional)],
                "identities": {},
                "tools": {},
            }
        )
    )

    def check(root):
        if root == additional:
            raise OSError("Supplementary tool volume disconnected")

    monkeypatch.setattr(tools, "validate_run_root", check)
    with pytest.raises(OSError, match="disconnected"):
        tools.validate_tools(manifest)
