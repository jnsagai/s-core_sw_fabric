"""007 context-package lock, safe globs, snapshots and repository lock provenance."""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest
import yaml

from score_sw_fabric.agents.lock import load_lock, upstream_findings, validate_lock, verify_copy
from score_sw_fabric.agents.models import (
    diff_snapshots,
    glob_list,
    glob_match,
    relative_path,
    snapshot,
)
from score_sw_fabric.process_source.reader import InputError
from tests.agent_support import REPO_LOCK, ROOT, lock_record, make_copy


def test_repository_lock_matches_reviewed_upstream_digests() -> None:
    lock = load_lock(REPO_LOCK.read_bytes())
    upstream = yaml.safe_load((ROOT / "upstream.lock.yaml").read_text())
    source = next(item for item in upstream["sources"] if item["id"] == "mcp-servers")
    assert lock["source"]["commit"] == source["commit"]
    files = {item["path"]: item["sha256"] for item in lock["files"]}
    for path, value in source["source_file_sha256"].items():
        assert files[path] == value
    statuses = {item["id"]: item["status"] for item in lock["servers"]}
    assert statuses == {
        "apm-setup": "supported",
        "context-discipline": "supported",
        "graphify-codegraph": "unsupported",
    }
    assert {item["code"] for item in upstream_findings(lock)} == {"UPSTREAM_LAUNCH_UNPINNED"}
    assert lock["runtime_client"]["compatibility"] == "not_verified"


def test_fixture_lock_verifies_and_names_each_drift(tmp_path: Path) -> None:
    root = make_copy(tmp_path)
    lock = validate_lock(lock_record(root))
    assert verify_copy(lock, root) == []
    assert upstream_findings(lock) == [
        {"code": "UPSTREAM_LAUNCH_UNPINNED", "detail": "fake"},
    ]
    (root / "pkg/src/fake_mcp.py").write_text("changed")
    assert verify_copy(lock, root) == [{"code": "LOCK_FILE_DRIFT", "detail": "pkg/src/fake_mcp.py"}]
    (root / "pkg/src/fake_mcp.py").unlink()
    assert verify_copy(lock, root)[0]["code"] == "LOCK_FILE_DRIFT"


def test_manifest_launch_must_match_lock(tmp_path: Path) -> None:
    root = make_copy(tmp_path)
    lock = lock_record(root)
    lock["servers"][0]["upstream_launch"]["args"] = ["other"]
    assert verify_copy(validate_lock(lock), root) == [
        {"code": "MANIFEST_LAUNCH_DRIFT", "detail": "fake"}
    ]


def test_locked_path_through_symlink_is_drift(tmp_path: Path) -> None:
    root = make_copy(tmp_path)
    lock = validate_lock(lock_record(root))
    (tmp_path / "elsewhere").mkdir()
    os.replace(root / "pkg/src", tmp_path / "elsewhere/src")
    (root / "pkg/src").symlink_to(tmp_path / "elsewhere/src")
    assert {item["code"] for item in verify_copy(lock, root)} == {"LOCK_FILE_DRIFT"}


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda lock: lock.update(extra=1), "FIELD_UNKNOWN"),
        (lambda lock: lock["source"].update(commit="abc"), "HASH_FORMAT"),
        (lambda lock: lock["servers"][0]["launch"].update(kind="uvx"), "LAUNCH_UNSUPPORTED"),
        (lambda lock: lock["servers"][0]["launch"].update(module="a;b"), "FIELD_TYPE"),
        (
            lambda lock: lock["servers"][0]["tools"][0].update(classification="approve"),
            "FIELD_ENUM",
        ),
        (
            lambda lock: lock["servers"][0]["tools"].append(lock["servers"][0]["tools"][0]),
            "DUPLICATE_ID",
        ),
        (lambda lock: lock["servers"][2].update(tools=[{}]), "LOCK_UNSUPPORTED"),
        (lambda lock: lock["setup_operations"][0].update(tool="read_info"), "LOCK_INCOMPLETE"),
        (lambda lock: lock["source"].update(notice_path="MISSING"), "LOCK_INCOMPLETE"),
        (lambda lock: lock["files"].pop(3), "LOCK_INCOMPLETE"),
        (lambda lock: lock["servers"][0].update(startup_writes=["../x"]), "INPUT_PATH"),
        (lambda lock: lock["limits"].update(line_bytes=0), "LIMIT_EXCEEDED"),
        (lambda lock: lock["servers"].append(lock["servers"][0]), "DUPLICATE_ID"),
    ],
)
def test_lock_refusals(tmp_path: Path, mutate: object, code: str) -> None:
    lock = copy.deepcopy(lock_record(make_copy(tmp_path)))
    mutate(lock)  # type: ignore[operator]
    with pytest.raises(InputError) as error:
        validate_lock(lock)
    assert error.value.code == code


def test_globs_match_whole_segments_only() -> None:
    assert glob_match("src/**", "src")
    assert glob_match("src/**", "src/a/b.cpp")
    assert glob_match("**/*.cpp", "a/b.cpp")
    assert glob_match("*.md", "README.md")
    assert not glob_match("*.md", "docs/README.md")
    assert not glob_match("src/**", "srcx/a")
    assert not glob_match("src/*", "src/a/b")
    for bad in (["/abs"], ["a/../b"], ["a**/b"], ["a", "a"], [""]):
        with pytest.raises(InputError):
            glob_list(bad, "/globs")
    for bad_path in ("/x", "a//b", "./a", "a\\b", "a/.."):
        with pytest.raises(InputError):
            relative_path(bad_path, "/p")


def test_snapshot_records_files_links_and_git_execution_surface(tmp_path: Path) -> None:
    (tmp_path / ".git/hooks").mkdir(parents=True)
    (tmp_path / ".git/objects").mkdir()
    (tmp_path / ".git/HEAD").write_text("ref")
    (tmp_path / ".git/config").write_text("[core]")
    (tmp_path / "a").mkdir()
    (tmp_path / "a/file").write_text("1")
    (tmp_path / "link").symlink_to("a")
    before = snapshot(tmp_path)
    kinds = {item["path"]: item["kind"] for item in before["files"]}
    assert kinds == {
        ".git": "directory",
        ".git/config": "file",
        ".git/hooks": "directory",
        "a": "directory",
        "a/file": "file",
        "link": "symlink",
    }
    (tmp_path / "a/file").write_text("2")
    (tmp_path / "b").write_text("new")
    (tmp_path / "link").unlink()
    (tmp_path / ".git/HEAD").write_text("changed")
    (tmp_path / ".git/objects/x").write_text("object")
    (tmp_path / ".git/hooks/pre-commit").write_text("#!/bin/sh")
    assert diff_snapshots(before, snapshot(tmp_path)) == [
        {"path": ".git/hooks/pre-commit", "change": "added"},
        {"path": "a/file", "change": "modified"},
        {"path": "b", "change": "added"},
        {"path": "link", "change": "removed"},
    ]
