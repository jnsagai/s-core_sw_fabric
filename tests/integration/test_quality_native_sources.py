"""Measure selected pinned sources and installed pack bytes without executing native tools.

Checkouts are selected explicitly through the environment. Git's optional locks and
filesystem monitor are disabled so even status inspection cannot refresh native indexes.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from score_sw_fabric.assurance.models import verify_digest
from score_sw_fabric.quality.profile import load_profile
from tests.quality_support import PROFILE, ROOT

EVIDENCE = (
    ROOT / "specs/010-misra-quality-and-deviations/evidence/native-source-reconciliation.json"
)
ENV = {
    "score": "SCORE_SOURCE",
    "score_cpp_policies": "SCORE_CPP_POLICIES_SOURCE",
    "time": "SCORE_TIME_SOURCE",
    "codeql-coding-standards": "CODEQL_CODING_STANDARDS_SOURCE",
}


def selected(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"read-only native input is selected by {name}")
    root = Path(value)
    assert root.exists(), name
    return root


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()


def state(root: Path) -> dict[str, str]:
    return {
        "head": git(root, "rev-parse", "HEAD"),
        "status": git(root, "status", "--porcelain", "--untracked-files=all"),
    }


def proof() -> dict[str, Any]:
    return verify_digest(json.loads(EVIDENCE.read_bytes()), "/native_source_reconciliation")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_profile_sources_native_statuses_and_original_policy_copies() -> None:
    roots = {
        "https://github.com/eclipse-score/score": selected(ENV["score"]),
        "https://github.com/eclipse-score/score_cpp_policies": selected(ENV["score_cpp_policies"]),
    }
    before = {key: state(root) for key, root in roots.items()}
    profile = load_profile(PROFILE.read_bytes())
    copies = {
        "clang_tidy": "clang-tidy.yaml",
        "sanitizer_features": "sanitizer-features.bazel",
        "asan_runtime": "asan.env.template",
        "asan_suppressions": "asan.supp",
        "ubsan_runtime": "ubsan.env.template",
        "ubsan_suppressions": "ubsan.supp",
    }
    documents = {
        "cpp_guidelines": ("doc__cpp_coding_guidelines", "valid"),
        "cpp_analysis": ("doc__cpp_code_analysis", "valid"),
        "misra_mapping": ("doc__cpp_misra2023_rule_mapping", "draft"),
    }
    for source in profile["native_sources"]:
        root = roots[source["repository"]]
        assert before[source["repository"]] == {"head": source["commit"], "status": ""}
        data = (root / source["path"]).read_bytes()
        assert sha(data) == source["sha256"], source["id"]
        if source["id"] in copies:
            assert data == (ROOT / "profiles/native-quality" / copies[source["id"]]).read_bytes()
        if source["id"] in documents:
            identifier, status = documents[source["id"]]
            text = data.decode()
            assert f":id: {identifier}" in text
            assert f":status: {status}" in text and ":version: 1" in text
    mapping = proof()["native_mapping_csv"]
    assert not (roots["https://github.com/eclipse-score/score"] / mapping["path"]).exists()
    assert profile["mapping_state"] == mapping["mapping_state"] == "unknown"
    policies = roots["https://github.com/eclipse-score/score_cpp_policies"]
    for name in ("LICENSE", "NOTICE"):
        assert (policies / name).read_bytes() == (
            ROOT / "profiles/native-quality" / name
        ).read_bytes()
    assert {key: state(root) for key, root in roots.items()} == before


def test_locked_sources_report_config_and_repository_statuses() -> None:
    record = proof()
    lock = yaml.safe_load((ROOT / "upstream.lock.yaml").read_bytes())
    for row in record["sources"]:
        root = selected(ENV[row["id"]])
        before = state(root)
        locked = next(item for item in lock["sources"] if item["id"] == row["id"])
        assert before == row["before"] == row["after"]
        assert before == {"head": locked["commit"], "status": ""}
        assert git(root, "rev-parse", "HEAD^{tree}") == row["tree"]
        observed = {}
        for source in row["files"]:
            data = (root / source["path"]).read_bytes()
            assert len(data) == source["bytes"] and sha(data) == source["sha256"]
            observed[source["path"]] = source["sha256"]
        assert all(
            observed[path] == digest for path, digest in locked["source_file_sha256"].items()
        )
        assert state(root) == before
    codeql = selected(ENV["codeql-coding-standards"])
    manual = (codeql / "docs/user_manual.md").read_text()
    assert "A Python interpreter version 3.9" in manual
    time = selected(ENV["time"])
    assert 'PYTHON_VERSION = "3.12"' in (time / "MODULE.bazel").read_text()
    assert not (codeql / "cpp/misra/src/codeql-suites/misra-cpp-audit.qls").exists()
    assert record["reporting"]["compatible_environment_selected"] is False
    assert record["analysis_executed"] is False


def test_declared_build_commit_has_exact_locked_git_tree() -> None:
    root = selected("CODEQL_RECONCILIATION_SOURCE")
    source = selected(ENV["codeql-coding-standards"])
    record = proof()["compiled_source_relationship"]
    before = state(root), state(source)
    trees = {commit: git(root, "rev-parse", commit + "^{tree}") for commit in record["git_trees"]}
    assert trees == record["git_trees"] and len(set(trees.values())) == 1
    assert git(source, "rev-parse", "HEAD^{tree}") == trees[record["locked_source_commit"]]
    assert git(root, "diff", "--name-status", *trees) == ""
    assert record["state"] == "source_trees_equal"
    assert record["compiled_artifact_provenance"] == "unverified"
    assert record["rebuild_executed"] is False
    assert (state(root), state(source)) == before


def test_original_report_patch_is_measured_only_in_disposable_copy(tmp_path: Path) -> None:
    source = selected(ENV["codeql-coding-standards"])
    time = selected(ENV["time"])
    before = state(source), state(time)
    row = proof()["reporting"]["disposable_patch_probe"]
    original = source / row["source_path"]
    patch = time / row["patch_path"]
    assert sha(original.read_bytes()) == row["pristine_sha256"]
    assert sha(patch.read_bytes()) == row["patch_sha256"]
    target = tmp_path / row["source_path"]
    target.parent.mkdir(parents=True)
    target.write_bytes(original.read_bytes())
    strict = subprocess.run(
        ["git", "apply", "--check", str(patch)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert strict.returncode == row["strict_git_apply_check_exit"]
    assert strict.stderr.strip() == row["strict_git_apply_check_stderr"]
    recounted = subprocess.run(
        ["git", "apply", "--recount", str(patch)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert recounted.returncode == row["recount_git_apply_exit"] == 0
    assert sha(target.read_bytes()) == row["patched_sha256"]
    assert row["state"] == "disposable_only_not_adopted"
    assert row["native_bazel_patch_engine_tested"] is False
    assert (state(source), state(time)) == before


def test_installed_pack_sources_dependencies_and_archive_originals() -> None:
    source = selected(ENV["codeql-coding-standards"])
    pack = selected("CODEQL_MISRA_COMPILED_PACK")
    archive = selected("CODEQL_CODING_STANDARDS_ARCHIVE")
    before = state(source)
    record = proof()
    relation = record["compiled_source_relationship"]
    originals = source / "cpp/misra/src"
    observed = sorted(
        path.relative_to(originals).as_posix()
        for path in originals.rglob("*")
        if path.is_file() and path.suffix in {".ql", ".qll", ".qls"}
    )
    assert observed == sorted(row["path"] for row in relation["matched_source_files"])
    assert len(observed) == relation["matched_source_file_count"] == 233
    for row in relation["matched_source_files"]:
        data = (originals / row["path"]).read_bytes()
        assert sha(data) == row["sha256"] and len(data) == row["bytes"]
        assert data == (pack / row["path"]).read_bytes()
    assert sha(archive.read_bytes()) == record["compiled_pack"]["archive_sha256"]
    with zipfile.ZipFile(archive) as release:
        for member in record["compiled_pack"]["members"]:
            data = release.read(member["member"])
            assert len(data) == member["bytes"] and sha(data) == member["sha256"]
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
                files = []
                for entry in tar.getmembers():
                    if entry.isfile():
                        handle = tar.extractfile(entry)
                        assert handle is not None
                        raw = handle.read()
                        files.append({"path": entry.name, "sha256": sha(raw), "bytes": len(raw)})
                        if member["member"].startswith("misra-cpp"):
                            assert raw == (pack / entry.name).read_bytes()
                assert len(files) == member["file_count"]
                manifest = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
                assert sha(manifest) == member["file_manifest_sha256"]
                handle = tar.extractfile("qlpack.yml")
                assert handle is not None
                assert yaml.safe_load(handle.read()) == member["identity"]
    suite = yaml.safe_load((pack / "codeql-suites/misra-cpp-default.qls").read_bytes())
    assert suite[-1]["exclude"]["tags contain"] == [
        "external/misra/audit",
        "external/misra/default-disabled",
    ]
    assert record["project_use_eligibility"] == "unresolved"
    assert record["accepted_claims"] == 0 and record["engineering_readiness"] == "not_evaluated"
    assert state(source) == before
