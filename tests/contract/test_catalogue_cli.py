"""CLI failure semantics preserve the previous successful catalogue."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from score_sw_fabric.cli import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/native"


def test_cli_atomic_failure_and_output_bounds(tmp_path: Path, capsys: object) -> None:
    root = tmp_path / "native"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("build"))
    manifest = root / "export-manifest.yaml"
    output = root / "build/catalogue.json"
    argv = ["catalog", "export", "--manifest", str(manifest), "--out", str(output), "--json"]
    assert main(argv) == 0
    first = output.read_bytes()
    assert json.loads(first)["engineering_readiness"] == "not_evaluated"
    (root / "needs.json").write_bytes((root / "needs.json").read_bytes() + b" ")
    assert main(argv) == 2
    assert output.read_bytes() == first
    assert (
        main(
            [
                "catalog",
                "export",
                "--manifest",
                str(manifest),
                "--out",
                str(tmp_path / "outside.json"),
                "--json",
            ]
        )
        == 2
    )
    assert not (tmp_path / "outside.json").exists()


def test_cli_semantic_failure_exit_one(tmp_path: Path) -> None:
    root = tmp_path / "native"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("build"))
    manifest_path = root / "export-manifest.yaml"
    export_path = root / "needs.json"
    export = json.loads(export_path.read_text())
    record = next(iter(next(iter(export["versions"].values()))["needs"].values()))
    record["links"] = ["tool_req__missing"]
    export_path.write_text(json.dumps(export))
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["exports"][0]["sha256"] = hashlib.sha256(export_path.read_bytes()).hexdigest()
    manifest_path.write_text(yaml.safe_dump(manifest))
    output = root / "build/catalogue.json"
    assert (
        main(
            ["catalog", "export", "--manifest", str(manifest_path), "--out", str(output), "--json"]
        )
        == 1
    )
    assert not output.exists()


@pytest.mark.parametrize(
    "relative_output",
    [
        "source/src/extensions/score_metamodel/metamodel-schema.json",
        "source/src/tests/docs_bzl/scenarios/nested_bundles/parent/index.rst",
        "source/new-directory/catalogue.json",
    ],
)
def test_cli_rejects_output_inside_source_tree(tmp_path: Path, relative_output: str) -> None:
    root = tmp_path / "native"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("build"))
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    output = root / relative_output
    assert (
        main(
            [
                "catalog",
                "export",
                "--manifest",
                str(root / "export-manifest.yaml"),
                "--out",
                str(output),
                "--json",
            ]
        )
        == 2
    )
    after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert after == before
    if relative_output == "source/new-directory/catalogue.json":
        assert not output.parent.exists()
