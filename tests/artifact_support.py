"""Deterministic Increment 004 fixture/request/package builders."""

from __future__ import annotations

import copy
import hashlib
import shutil
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric.artifacts.rst import scan_rst
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.package import compile_package
from score_sw_fabric.compiler.reader import load_compiler_inputs, semantic_digest
from tests.compiler_support import RecordingValidator, prepare_case

REPO = Path(__file__).resolve().parents[1]


def seal(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["digest"] = semantic_digest(result)
    return result


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def reference(path: Path, *, logical: str | None = None) -> dict[str, str]:
    value = (
        __import__("json").loads(path.read_text())
        if path.suffix == ".json"
        else yaml.safe_load(path.read_text())
    )
    return {
        "path": logical or path.as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "semantic_digest": value["digest"],
    }


def snapshot(root: Path, kind: str = "component") -> dict[str, Any]:
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        logical = path.relative_to(root).as_posix()
        data = path.read_bytes()
        records.append(
            {
                "path": logical,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "media_kind": "text/rst" if path.suffix == ".rst" else "application/octet-stream",
                "semantic_role": "native_source" if path.suffix == ".rst" else "build_support",
                "executable": False,
            }
        )
    external = {
        "feature": ["COMP_REQ_001", "TEST_CASE_001", "WP_FEATURE_001"],
        "component": ["FEAT_REQ_001", "WP_COMPONENT_001"],
        "analysis": ["COMP_REQ_001", "WP_ANALYSIS_001"],
    }[kind]
    return seal(
        {
            "schema_version": 1,
            "target_namespace": f"fixture-{kind}",
            "snapshot_id": f"fixture-{kind}-snapshot-v1",
            "source": {
                "source_id": "score",
                "repository": "https://github.com/eclipse-score/score",
                "commit": "c4d4ad0000000000000000000000000000000000",
                "revision_label": "fixture-v1",
                "source_lock": "upstream.lock.yaml",
            },
            "configuration": {
                "docs_root": ".",
                "build_files": [],
                "dependency_lock": "tests/native_consumer/MODULE.bazel.lock",
                "metamodel_sha256": (
                    "fe6a3b6af5ea69271e53c57e3a1694dc69d6ff3df16bd1505dc7242db9976290"
                ),
            },
            "files": records,
            "external_exports": [
                {
                    "source_id": "fixture-external",
                    "native_ids": external,
                    "prefixes": ["FEAT_REQ_", "COMP_REQ_", "TEST_CASE_", "WP_"],
                }
            ],
            "build_closure": {"files": [item["path"] for item in records], "dependencies": []},
        }
    )


def prepare_artifact_case(
    root: Path,
    *,
    kind: str = "component",
    operation: str = "index",
    edits: list[dict[str, Any]] | None = None,
) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    target = root / "target"
    shutil.copytree(REPO / "tests/fixtures/artifacts" / kind / "target", target)
    (root / "out").mkdir()
    snap = snapshot(target, kind)
    snapshot_path = root / "snapshot.json"
    write_json(snapshot_path, snap)
    artifact_profile = REPO / "profiles/s_core_native_artifacts_v1.yaml"
    trace_profile = REPO / "policies/s_core_trace_profile_v1.yaml"
    workflow_request, _ = prepare_case(root / "workflow")
    workflow_inputs = load_compiler_inputs(workflow_request)
    package = compile_package(workflow_inputs, native_validator=RecordingValidator())
    package_path = root / "workflow-package.json"
    write_json(package_path, package)
    plan_path = root / "workflow" / "plan.json"
    refs: dict[str, Any] = {
        "target_snapshot": reference(snapshot_path, logical="snapshot.json"),
        "artifact_profile": reference(
            artifact_profile, logical="profiles/s_core_native_artifacts_v1.yaml"
        ),
        "trace_profile": None,
        "plan": None,
        "workflow_package": None,
    }
    if operation in {"candidate", "trace"}:
        refs["plan"] = reference(plan_path, logical="workflow/plan.json")
        refs["workflow_package"] = reference(package_path, logical="workflow-package.json")
    if operation == "trace":
        refs["trace_profile"] = reference(
            trace_profile, logical="policies/s_core_trace_profile_v1.yaml"
        )
    selected_edits = edits
    if operation == "candidate" and selected_edits is None:
        selected_edits = [content_edit(root)]
    request = {
        "schema_version": 1,
        "operation": operation,
        **refs,
        "operations": selected_edits or [],
        "local_paths": {
            "snapshot_root": "target",
            "protected_roots": ["target"],
            "fixture_native": True,
        },
        "output_root": "out",
    }
    request_path = root / "request.yaml"
    request_path.write_text(yaml.safe_dump(request, sort_keys=False))
    return request_path, root / "out" / f"{operation}.json"


def content_edit(
    root: Path, *, native_id: str = "COMP_REQ_001", content: str = "Updated explicit content."
) -> dict[str, Any]:
    source = (root / "target/index.rst").read_text()
    directive = next(
        item
        for item in scan_rst(
            "index.rst", source, {"document", "comp_req", "interface", "test_case"}
        )["directives"]
        if item["native_id"] == native_id
    )
    return {
        "id": "edit-content-1",
        "kind": "set_content",
        "depends_on": [],
        "plan_instance": "obligation-a",
        "target_path": "index.rst",
        "target_native_id": native_id,
        "anchor": None,
        "expected_preimage": directive["original_digest"],
        "values": {"content": content},
        "artifact_rule_id": "fixture-artifact",
        "trace_rule_id": None,
        "origins": [
            {
                "kind": "reviewed_project_configuration",
                "source_ref": {"fixture": "tests/artifact_support.py"},
                "pointer": "/edits/0",
                "decision_ref": "fixture-review-004",
                "rationale": "Explicit fixture edit.",
            }
        ],
        "rationale": "Exercise a bounded content edit.",
    }


def create_edit(kind: str = "analysis", identifier: str = "002") -> dict[str, Any]:
    template = REPO / f"tests/fixtures/artifacts/{kind}/template.rst"
    return {
        "id": "create-document-1",
        "kind": "create_document",
        "depends_on": [],
        "plan_instance": "obligation-a",
        "target_path": "created.rst",
        "target_native_id": None,
        "anchor": None,
        "expected_preimage": hashlib.sha256(template.read_bytes()).hexdigest(),
        "values": {"template_id": f"{kind}-v1", "placeholders": {"ID": identifier}},
        "artifact_rule_id": "fixture-artifact",
        "trace_rule_id": None,
        "origins": [
            {
                "kind": "reviewed_project_configuration",
                "source_ref": {"fixture": "tests/artifact_support.py"},
                "pointer": "/creates/0",
                "decision_ref": "fixture-review-004",
                "rationale": "Explicit fixture create.",
            }
        ],
        "rationale": "Exercise exact template realization.",
    }


def sentinel(path: Path, data: bytes = b"preserve-me") -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data
