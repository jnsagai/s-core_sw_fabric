"""Deterministic, licensed planning fixtures for contract and integration tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric.catalog.export import seal


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_yaml(path: Path, value: dict[str, Any]) -> str:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return sha256(path)


def catalogue_payload(
    native_ids: tuple[str, ...] = ("wp__plan", "wp__fdr_reports"),
) -> dict[str, Any]:
    source = {
        "id": "process",
        "repository": "https://example.invalid/process",
        "commit": "1" * 40,
    }
    entities = []
    for position, native_id in enumerate(native_ids, 1):
        source_ref = {
            "source_id": "process",
            "repository": source["repository"],
            "commit": source["commit"],
            "native_id": native_id,
            "native_version": 1,
            "path": "process/workproducts.rst",
            "lineno": position,
        }
        entities.append(
            {
                "source_id": "process",
                "native_id": native_id,
                "native_version": 1,
                "type": "workproduct",
                "title": native_id,
                "status": "valid",
                "source_ref": source_ref,
                "raw": {"id": native_id, "version": 1},
                "normalized": {"id": native_id, "version": 1},
            }
        )
    return {
        "schema_version": 1,
        "manifest": {"sources": [source]},
        "metamodel_raw": {},
        "types": [{"name": "workproduct", "source_ref": {"source_id": "process"}}],
        "entities": entities,
        "relations": [],
        "engineering_readiness": "not_evaluated",
    }


def write_catalogue(
    path: Path, native_ids: tuple[str, ...] = ("wp__plan", "wp__fdr_reports")
) -> tuple[dict[str, Any], str]:
    catalogue, data = seal(catalogue_payload(native_ids))
    path.write_bytes(data)
    return catalogue, sha256(path)


def native_rule(native_id: str, *, selector: str = "self") -> dict[str, Any]:
    purposes = ["plan", "package"] if native_id == "wp__fdr_reports" else ["primary"]
    return {
        "id": f"rule__{native_id}",
        "native": {
            "source_id": "process",
            "native_id": native_id,
            "native_version": 1,
        },
        "scope_kinds": ["feature", "component", "module", "platform"],
        "scope_selector": selector,
        "when": [],
        "purposes": purposes,
        "dependencies": [],
        "rationale": "Fixture rule derived from the declared native work-product source.",
        "source_refs": [{"fixture_origin": "tests/planning_support.py", "native_id": native_id}],
        "template_refs": [],
        "required_reviews": [],
    }


def default_scopes() -> list[dict[str, Any]]:
    facts = {
        "development_origin": "new",
        "language": "cpp17",
        "environment": "linux",
        "safety_classification": "QM",
        "security_relevance": "not_relevant",
        "reuse_route": "not_applicable",
        "has_subcomponents": False,
        "relevant_interactions": False,
    }
    return [
        {"kind": "platform", "id": "platform", "parent": None, "facts": dict(facts)},
        {
            "kind": "module",
            "id": "module",
            "parent": {"kind": "platform", "id": "platform"},
            "facts": dict(facts),
        },
        {
            "kind": "component",
            "id": "component",
            "parent": {"kind": "module", "id": "module"},
            "facts": dict(facts),
        },
        {
            "kind": "feature",
            "id": "feature",
            "parent": {"kind": "module", "id": "module"},
            "facts": dict(facts),
        },
    ]


def prepare_case(
    root: Path,
    *,
    native_ids: tuple[str, ...] = ("wp__plan", "wp__fdr_reports"),
    scopes: list[dict[str, Any]] | None = None,
    rules: list[dict[str, Any]] | None = None,
    inventory: dict[str, Any] | None = None,
    decisions: dict[str, Any] | None = None,
    source_conflicts: list[dict[str, Any]] | None = None,
) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "reference").mkdir()
    (root / "out").mkdir()
    catalogue, catalogue_sha = write_catalogue(root / "catalogue.json", native_ids)
    profile = {
        "schema_version": 1,
        "id": "fixture-profile",
        "version": 1,
        "status": "review_draft",
        "catalogue_digest": catalogue["digest"],
        "expected_workproduct_count": len(native_ids),
        "supported": {
            "language": ["cpp17"],
            "environment": ["linux"],
            "safety_classification": ["QM", "ASIL_B"],
            "security_relevance": ["relevant", "not_relevant"],
        },
        "active_revisions": [
            {"source_id": "process", "native_id": native_id, "native_version": 1}
            for native_id in native_ids
        ],
        "limits": {
            "scopes": 1000,
            "rules": 10000,
            "coverage_rows": 100000,
            "instances": 10000,
            "dependency_edges": 100000,
        },
        "source_refs": [{"fixture_origin": "tests/planning_support.py"}],
    }
    mapping = {
        "schema_version": 1,
        "coverage_basis": {"fixture_origin": "tests/planning_support.py"},
        "rules": rules if rules is not None else [native_rule(item) for item in native_ids],
        "source_conflicts": source_conflicts or [],
    }
    documents = {
        "profile": profile,
        "mapping": mapping,
        "inventory": inventory
        or {"schema_version": 1, "completeness": "complete", "artifacts": []},
        "decisions": decisions or {"schema_version": 1, "references": []},
    }
    document_refs: dict[str, dict[str, str]] = {}
    for name, document in documents.items():
        path = root / f"{name}.yaml"
        document_refs[name] = {"path": path.name, "sha256": write_yaml(path, document)}
    selected_scopes = scopes if scopes is not None else default_scopes()
    intake = {
        "schema_version": 1,
        "target_namespace": "fixture-target",
        "change": {"id": "change-1", "intent": "Exercise deterministic planning."},
        "scopes": selected_scopes,
        "affected_scopes": [{"kind": item["kind"], "id": item["id"]} for item in selected_scopes],
        "catalogue": {
            "path": "catalogue.json",
            "sha256": catalogue_sha,
            "digest": catalogue["digest"],
        },
        **document_refs,
        "local_paths": {"output_root": "out", "reference_roots": ["reference"]},
    }
    intake_path = root / "intake.yaml"
    write_yaml(intake_path, intake)
    return intake_path, root / "out" / "plan.json"
