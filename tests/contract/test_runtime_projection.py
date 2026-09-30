"""003 package projection preserves source identity and Fabro's wire limits."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.package import validate_package
from score_sw_fabric.compiler.reader import semantic_digest
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml
from score_sw_fabric.runtime import projection

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "tests/fixtures/compiler/linear/out/package.json"
PROFILE = ROOT / "tests/fixtures/compiler/linear/compiler_profile.yaml"


def _sources() -> tuple[dict[str, Any], dict[str, Any]]:
    return read_json(PACKAGE), read_yaml(PROFILE)


def test_projection_retains_original_package_and_uses_graph_entrypoint() -> None:
    package, profile = _sources()
    original_bytes = PACKAGE.read_bytes()
    projected = projection.project_version(package, profile)
    assert projected["source_package_digest"] == package["digest"]
    assert projected["source_entrypoint"] == "workflow.toml"
    assert projected["wire_entrypoint"] == "workflow.fabro"
    assert projected["wire"]["entrypoint"] == "workflow.fabro"
    assert projected["wire"]["files"] == package["files"]
    assert projected["wire"]["workflow_dependencies"] == {}
    assert projected["wire_bytes"] == len(canonical(projected["wire"]).removesuffix(b"\n"))
    assert (
        projected["wire_digest"]
        == hashlib.sha256(canonical(projected["wire"]).removesuffix(b"\n")).hexdigest()
    )
    assert PACKAGE.read_bytes() == original_bytes


def test_changed_003_file_cannot_register_even_if_outer_digest_is_resealed() -> None:
    package, profile = _sources()
    changed = deepcopy(package)
    changed["files"]["workflow.fabro"] += "\n"
    changed["digest"] = semantic_digest(changed)
    with pytest.raises(InputError) as error:
        projection.project_version(changed, profile)
    assert error.value.code == "PACKAGE_FILE_DIGEST"


def test_old_native_receipt_cannot_cover_resealed_changed_files() -> None:
    package, profile = _sources()
    changed = deepcopy(package)
    graph = "workflow.fabro"
    changed["files"][graph] += "\n// changed after validation\n"
    encoded = changed["files"][graph].encode()
    for record in changed["manifest"]["file_records"]:
        if record["path"] == graph:
            record["bytes"] = len(encoded)
            record["sha256"] = hashlib.sha256(encoded).hexdigest()
    for item in changed["source_map"]:
        if item["kind"] == "file" and item["id"] == graph:
            item["content_binding"] = hashlib.sha256(encoded).hexdigest()
    changed["manifest"]["source_map_digest"] = hashlib.sha256(
        canonical(changed["source_map"])
    ).hexdigest()
    changed["digest"] = semantic_digest(changed)
    validate_package(changed, profile)
    with pytest.raises(InputError) as error:
        projection.project_version(changed, profile)
    assert error.value.code == "NATIVE_RECEIPT_STALE"


def test_missing_declared_graph_is_rejected() -> None:
    package, profile = _sources()
    package["files"].pop("workflow.fabro")
    package["digest"] = semantic_digest(package)
    with pytest.raises(InputError):
        projection.project_version(package, profile)


def test_native_file_count_exact_max_and_one_over(monkeypatch: pytest.MonkeyPatch) -> None:
    package, profile = _sources()
    count = len(package["files"])
    monkeypatch.setattr(projection, "MAX_VERSION_FILES", count)
    projection.project_version(package, profile)
    monkeypatch.setattr(projection, "MAX_VERSION_FILES", count - 1)
    with pytest.raises(InputError) as error:
        projection.project_version(package, profile)
    assert error.value.code == "WIRE_LIMIT_EXCEEDED"


def test_native_file_bytes_exact_max_and_one_over(monkeypatch: pytest.MonkeyPatch) -> None:
    package, profile = _sources()
    maximum = max(len(item.encode()) for item in package["files"].values())
    monkeypatch.setattr(projection, "MAX_VERSION_FILE_BYTES", maximum)
    projection.project_version(package, profile)
    monkeypatch.setattr(projection, "MAX_VERSION_FILE_BYTES", maximum - 1)
    with pytest.raises(InputError) as error:
        projection.project_version(package, profile)
    assert error.value.code == "WIRE_LIMIT_EXCEEDED"


def test_native_canonical_wire_exact_max_and_one_over(monkeypatch: pytest.MonkeyPatch) -> None:
    package, profile = _sources()
    size = projection.project_version(package, profile)["wire_bytes"]
    monkeypatch.setattr(projection, "MAX_VERSION_BYTES", size)
    projection.project_version(package, profile)
    monkeypatch.setattr(projection, "MAX_VERSION_BYTES", size - 1)
    with pytest.raises(InputError) as error:
        projection.project_version(package, profile)
    assert error.value.code == "WIRE_LIMIT_EXCEEDED"


@pytest.mark.parametrize(
    "path",
    [
        "../escape",
        "/absolute",
        "a//b",
        "a/./b",
        "a/../b",
        "a\\b",
        "~home",
        "C:drive",
        "a\x00b",
        "a" * 241,
        "/".join(["a"] * 17),
    ],
)
def test_native_logical_path_rejects_traversal_and_alias(path: str) -> None:
    with pytest.raises(InputError) as error:
        projection._logical_path(path, "/files")
    assert error.value.code == "PACKAGE_PATH"


def _resealed(package: dict[str, Any], files: dict[str, str]) -> dict[str, Any]:
    """Reseal file records, source map and native receipt so projection checks run."""
    changed = deepcopy(package)
    changed["files"] = dict(sorted(files.items()))
    records = []
    for path, content in changed["files"].items():
        encoded = content.encode()
        records.append(
            {"path": path, "bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}
        )
    changed["manifest"]["file_records"] = records
    for item in changed["source_map"]:
        if item["kind"] == "file" and item["id"] in changed["files"]:
            item["content_binding"] = hashlib.sha256(
                changed["files"][item["id"]].encode()
            ).hexdigest()
    changed["manifest"]["source_map_digest"] = hashlib.sha256(
        canonical(changed["source_map"])
    ).hexdigest()
    changed["native_validation"]["source_set_digest"] = hashlib.sha256(
        canonical(changed["files"])
    ).hexdigest()
    changed["digest"] = semantic_digest(changed)
    return changed


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("extra_undeclared_file", "PACKAGE_CLOSURE"),
        ("missing_config", "PACKAGE_ENTRYPOINT"),
        ("graph_elsewhere", "PACKAGE_CLOSURE"),
        ("case_collision", "PACKAGE_CASE_COLLISION"),
        ("directory_shadow", "PACKAGE_CLOSURE"),
        ("child_workflow", "IR_DIGEST"),
    ],
)
def test_undeclared_missing_or_ambiguous_closure_is_refused(change: str, code: str) -> None:
    package, profile = _sources()
    original = PACKAGE.read_bytes()
    files = dict(package["files"])
    if change == "extra_undeclared_file":
        files["prompts/extra.md"] = "undeclared"
    elif change == "missing_config":
        files.pop("workflow.toml")
    elif change == "graph_elsewhere":
        files["workflow.toml"] = files["workflow.toml"].replace("workflow.fabro", "other.fabro")
        files["other.fabro"] = files["workflow.fabro"]
    elif change == "case_collision":
        files["Workflow.fabro"] = files["workflow.fabro"]
    elif change == "directory_shadow":
        files["workflow.fabro/child"] = "shadow"
    if change == "child_workflow":
        # 003 IR has no child-workflow field; an injected reference fails IR integrity.
        changed = deepcopy(package)
        changed["manifest"]["ir"]["child_workflows"] = ["child"]
        changed["digest"] = semantic_digest(changed)
    else:
        changed = _resealed(package, files)
    with pytest.raises(InputError) as error:
        projection.project_version(changed, profile)
    assert error.value.code == code
    assert PACKAGE.read_bytes() == original


def test_non_text_native_file_is_refused() -> None:
    package, profile = _sources()
    changed = deepcopy(package)
    changed["files"]["workflow.fabro"] = 7
    with pytest.raises(InputError):
        projection.project_version(changed, profile)


def test_relocated_package_bytes_project_to_the_same_wire_identity(tmp_path: Path) -> None:
    moved = tmp_path / "relocated/package.json"
    moved.parent.mkdir()
    moved.write_bytes(PACKAGE.read_bytes())
    _, profile = _sources()
    assert (
        projection.project_version(read_json(moved), profile)["wire_digest"]
        == projection.project_version(read_json(PACKAGE), profile)["wire_digest"]
    )
