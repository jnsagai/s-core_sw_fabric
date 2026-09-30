from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from score_sw_fabric.artifacts.index import build_index
from score_sw_fabric.artifacts.models import ArtifactInputs
from score_sw_fabric.artifacts.package import build_candidate, index_request
from score_sw_fabric.artifacts.rst import scan_rst
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.reader import semantic_digest
from tests.artifact_support import prepare_artifact_case


@pytest.mark.parametrize("kind", ["feature", "component", "analysis"])
def test_representative_native_fixture_index_is_non_skipped_and_read_only(
    tmp_path: Path, kind: str
) -> None:
    request, output = prepare_artifact_case(tmp_path, kind=kind)
    source = tmp_path / "target/index.rst"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    index = index_request(request, output)
    assert index["valid"] is True
    assert index["native_receipt"]["accepted"] is True
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def _real_paths() -> tuple[Path, Path]:
    binary_raw = os.environ.get("SCORE_BAZEL_BIN")
    root_raw = os.environ.get("SCORE_NATIVE_MODULE_ROOT")
    if not binary_raw or not root_raw:
        pytest.skip("real-native acceptance requires SCORE_BAZEL_BIN and SCORE_NATIVE_MODULE_ROOT")
    binary = Path(binary_raw)
    root = Path(root_raw)
    if not binary.is_file() or not root.is_dir():
        pytest.skip("real-native acceptance paths are unavailable")
    return binary, root


def _rst_files(root: Path) -> dict[str, str]:
    selected: dict[str, str] = {}
    for base in ("docs", "score/component_example/docs", "examples/docs"):
        for path in sorted((root / base).rglob("*.rst")):
            selected[path.relative_to(root).as_posix()] = path.read_text()
    return selected


def _source_hashes(root: Path) -> dict[str, str]:
    return {
        path: hashlib.sha256(content.encode()).hexdigest()
        for path, content in _rst_files(root).items()
    }


def _run(binary: Path, root: Path, output_user_root: Path, *argv: str) -> str:
    result = subprocess.run(
        [
            str(binary),
            "--batch",
            f"--output_user_root={output_user_root}",
            *argv,
        ],
        cwd=root,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(output_user_root / "home"),
            "XDG_CACHE_HOME": str(output_user_root / "cache"),
            "NO_COLOR": "1",
        },
        text=True,
        capture_output=True,
        timeout=1800,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    assert len(output.encode()) <= 8 * 1024 * 1024
    assert result.returncode == 0, output[-8000:]
    return output


def _snapshot(files: dict[str, str]) -> dict[str, Any]:
    records = [
        {
            "path": path,
            "bytes": len(content.encode()),
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "media_kind": "text/rst",
            "semantic_role": "native_source",
            "executable": False,
        }
        for path, content in sorted(files.items())
    ]
    value = {
        "schema_version": 1,
        "target_namespace": "fixture-native-module-template",
        "snapshot_id": "module-template-c4d4ad0",
        "source": {
            "source_id": "module_template",
            "repository": "https://github.com/eclipse-score/module_template",
            "commit": "c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d",
            "revision_label": "c4d4ad0",
            "source_lock": "upstream.lock.yaml",
        },
        "configuration": {
            "docs_root": ".",
            "build_files": ["BUILD", "MODULE.bazel", "MODULE.bazel.lock"],
            "dependency_lock": "MODULE.bazel.lock",
            "metamodel_sha256": (
                "fe6a3b6af5ea69271e53c57e3a1694dc69d6ff3df16bd1505dc7242db9976290"
            ),
        },
        "files": records,
        "external_exports": [
            {
                "source_id": "score-process-description",
                "native_ids": [],
                "prefixes": ["wp__", "stkh_req__"],
            }
        ],
        "build_closure": {
            "files": [item["path"] for item in records],
            "dependencies": ["score_process_description@2.1.2", "score_docs_as_code@8.2.0"],
        },
    }
    value["digest"] = semantic_digest(value)
    return value


def _update_operation(
    files: dict[str, str],
    profile: dict[str, Any],
    identifier: str,
    path: str,
    suffix: str,
) -> dict[str, Any]:
    directive = next(
        item
        for item in scan_rst(path, files[path], set(profile["directives"]))["directives"]
        if item["native_id"] == identifier
    )
    return {
        "id": f"update-{suffix}",
        "kind": "set_content",
        "depends_on": [],
        "plan_instance": f"native-{suffix}",
        "target_path": path,
        "target_native_id": identifier,
        "anchor": None,
        "expected_preimage": directive["original_digest"],
        "values": {"content": f"Reviewed isolated {suffix} update."},
        "artifact_rule_id": "fixture-artifact",
        "trace_rule_id": None,
        "origins": [],
        "rationale": "Real-native acceptance update.",
    }


def _create_operation(
    profile: dict[str, Any], kind: str, path: str, identifier: str
) -> dict[str, Any]:
    template = next(item for item in profile["templates"] if item["id"] == f"native-{kind}-v1")
    return {
        "id": f"create-{kind}",
        "kind": "create_document",
        "depends_on": [],
        "plan_instance": f"native-{kind}",
        "target_path": path,
        "target_native_id": None,
        "anchor": None,
        "expected_preimage": template["sha256"],
        "values": {
            "template_id": f"native-{kind}-v1",
            "placeholders": {"ID": identifier},
        },
        "artifact_rule_id": "fixture-artifact",
        "trace_rule_id": None,
        "origins": [],
        "rationale": "Real-native acceptance create.",
    }


def test_locked_real_native_index_and_candidate_round_trips(tmp_path: Path) -> None:
    binary, root = _real_paths()
    protected_before = _source_hashes(root)
    output_user_root = Path(
        os.environ.get("SCORE_BAZEL_OUTPUT_ROOT", str(tmp_path / "bazel-output"))
    )
    output_user_root.mkdir(parents=True, exist_ok=True)
    (output_user_root / "home").mkdir(exist_ok=True)
    (output_user_root / "cache").mkdir(exist_ok=True)
    needs_log = _run(binary, root, output_user_root, "build", "//:needs_json")
    docs_log = _run(binary, root, output_user_root, "run", "//:docs_check")
    export_path = root / "bazel-bin/needs_json/_build/needs/needs.json"
    export = json.loads(export_path.read_text())
    files = _rst_files(root)
    profile = yaml.safe_load(Path("profiles/s_core_native_artifacts_v1.yaml").read_text())
    snapshot = _snapshot(files)
    receipt = {
        "accepted": True,
        "validator": {
            "id": "s-core-native-build-v1",
            "fixture_only": False,
            "executable_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        },
        "log_digest": hashlib.sha256((needs_log + docs_log).encode()).hexdigest(),
        "export_digest": hashlib.sha256(canonical(export)).hexdigest(),
        "cleanup": "complete",
    }
    index = build_index(files, snapshot, profile, export, receipt)
    assert index["valid"] is True
    assert index["counts"] == {
        "files": 47,
        "wrappers": 33,
        "needs": 29,
        "relations": 82,
        "findings": 0,
    }
    assert all(item["state"] == "matched" for item in index["reconciliation"])
    by_path = {
        "feature": [
            x
            for x in [*index["wrappers"], *index["needs"]]
            if x["source"]["path"].startswith("docs/features/")
        ],
        "component": [
            x
            for x in [*index["wrappers"], *index["needs"]]
            if x["source"]["path"].startswith("score/component_example/docs/")
        ],
        "analysis": [
            x for x in [*index["wrappers"], *index["needs"]] if "analysis" in x["source"]["path"]
        ],
    }
    assert {name: len(items) for name, items in by_path.items()} == {
        "feature": 8,
        "component": 14,
        "analysis": 9,
    }
    assert any(item["status"] == "invalid" for item in by_path["component"])
    assert sum(content.count(".. ") for content in files.values()) > 62

    profile = json.loads(json.dumps(profile))
    shared_output_base = os.environ.get("SCORE_BAZEL_OUTPUT_BASE")
    startup = ["--batch", f"--output_user_root={output_user_root}"]
    if shared_output_base:
        startup.append(f"--output_base={shared_output_base}")
    profile["native_validator"]["argv"] = [
        [*startup, "build", "//:needs_json"],
        [*startup, "run", "//:docs_check"],
    ]
    profile["digest"] = semantic_digest(profile)
    operations = [
        _update_operation(
            files,
            profile,
            "doc__feature_name_fmea",
            "docs/features/safety_analysis/fmea.rst",
            "feature",
        ),
        _update_operation(
            files,
            profile,
            "doc__mod_temp_component_name",
            "score/component_example/docs/index.rst",
            "component",
        ),
        _update_operation(
            files,
            profile,
            "doc__mod_temp_component_name_fmea",
            "score/component_example/docs/safety_analysis/fmea.rst",
            "analysis",
        ),
        _create_operation(profile, "feature", "docs/features/generated_feature_004.rst", "004"),
        _create_operation(
            profile,
            "component",
            "score/component_example/docs/generated_component_004.rst",
            "004",
        ),
        _create_operation(
            profile,
            "analysis",
            "docs/features/safety_analysis/generated_analysis_004.rst",
            "004",
        ),
    ]
    request = {
        "schema_version": 1,
        "operation": "candidate",
        "operations": operations,
    }
    plan = {"digest": "1" * 64}
    package = {"digest": "2" * 64}
    candidate_inputs = ArtifactInputs(
        request_path=tmp_path / "real-request.yaml",
        request=request,
        operation="candidate",
        snapshot=snapshot,
        artifact_profile=profile,
        trace_profile=None,
        plan=plan,
        workflow_package=package,
        semantic_digests={},
        input_paths=(),
        snapshot_root=root,
        output_root=tmp_path,
        protected_roots=(root,),
        local_paths={
            "bazel": str(binary),
            "build_profile": str(Path("profiles/s_core_native_build_v1.yaml").resolve()),
            "native_consumer": str(root),
            "native_export_result": "bazel-bin/needs_json/_build/needs/needs.json",
        },
    )
    candidate = build_candidate(candidate_inputs)
    assert candidate["native_receipt"] == candidate["index"]["native_receipt"]
    assert candidate["native_receipt"]["validator"]["fixture_only"] is False
    assert candidate["index"]["counts"]["wrappers"] == 36
    assert candidate["index"]["counts"]["findings"] == 0
    assert {item["id"] for item in candidate["edit_results"]} == {
        "update-feature",
        "update-component",
        "update-analysis",
        "create-feature",
        "create-component",
        "create-analysis",
    }
    assert len(candidate["overlay_files"]) == 6
    for record in candidate["overlay_files"]:
        if record["base_sha256"] is not None:
            assert (
                hashlib.sha256(files[record["path"]].encode()).hexdigest() == record["base_sha256"]
            )
    assert _source_hashes(root) == protected_before
