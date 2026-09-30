"""Manifest and source boundary checks."""

import shutil
from pathlib import Path

import pytest
import yaml

from score_sw_fabric.process_source.reader import InputError, load_manifest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/native"


def copied_manifest(tmp_path: Path) -> Path:
    root = tmp_path / "native"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("build"))
    return root / "export-manifest.yaml"


def test_duplicate_yaml_key_rejected(tmp_path: Path) -> None:
    path = copied_manifest(tmp_path)
    path.write_text(path.read_text() + "\nsources: []\n")
    with pytest.raises(InputError) as error:
        load_manifest(path)
    assert error.value.code == "DUPLICATE_YAML_KEY"


def test_false_fresh_build_provenance_rejected(tmp_path: Path) -> None:
    path = copied_manifest(tmp_path)
    manifest = yaml.safe_load(path.read_text())
    manifest["provenance"]["origin"] = "fresh_build"
    path.write_text(yaml.safe_dump(manifest))
    with pytest.raises(InputError) as error:
        load_manifest(path)
    assert error.value.code == "PROVENANCE"


def test_mount_order_does_not_change_semantic_manifest(tmp_path: Path) -> None:
    path = copied_manifest(tmp_path)
    first = load_manifest(path).semantic
    manifest = yaml.safe_load(path.read_text())
    manifest["mounts"].append(
        {"source_id": "docs_as_code", "docname_prefix": "unrelated", "path_prefix": "docs"}
    )
    path.write_text(yaml.safe_dump(manifest))
    second = load_manifest(path).semantic
    manifest["mounts"].reverse()
    path.write_text(yaml.safe_dump(manifest))
    third = load_manifest(path).semantic
    assert second == third
    assert first != second
