"""Synthetic guideline declarations; no native MISRA mapping or licensed execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import digest, seal
from score_sw_fabric.quality import imports
from tests.quality_import_support import identity, selection, write_json
from tests.quality_support import ROOT, ref


def manifest(tmp: Path) -> dict[str, Any]:
    source = tmp / "guidelines.json"
    write_json(
        source,
        {
            "schema_version": 1,
            "kind": "quality_guideline_source",
            "id": "fixture-source",
            "guideline_ids": ["fixture-guideline-a", "fixture-guideline-b"],
            "license": "synthetic fixture",
            "notice": "IDs only; no MISRA text",
            "native_status": "fixture_only",
        },
    )
    expected = [
        {
            "guideline_id": "fixture-guideline-" + name,
            "native_category": "fixture_advisory",
            "applicability": "applicable",
            "rationale": "Synthetic coverage test",
            "source_ids": ["fixture-source"],
        }
        for name in ("a", "b")
    ]
    tool = {
        "id": "fixture-tool",
        "kind": "tool",
        "automation_class": "automatic",
        "tool": "codeql",
        "native_id": "fixture/check",
        "identity_digest": digest(identity()),
        "availability": "supported",
        "enabled": True,
        "limitations": ["Test-only association"],
        "source_ids": ["fixture-source"],
    }
    manual = {
        **tool,
        "id": "fixture-manual",
        "kind": "manual",
        "automation_class": "manual",
        "tool": None,
        "native_id": None,
        "identity_digest": None,
        "enabled": None,
    }
    return seal(
        {
            "schema_version": 1,
            "kind": "quality_guideline_manifest",
            "id": "fixture-mapping",
            "origin": "fixture",
            "scope": {
                "component": "fixture_component",
                "files": ["check.cpp"],
                "translation_units": ["check.cpp"],
            },
            "expected_guidelines": expected,
            "source_refs": [
                {
                    "id": "fixture-source",
                    "ref": ref(source),
                    "license": "synthetic fixture",
                    "notice": "IDs only; no MISRA text",
                    "native_status": "fixture_only",
                }
            ],
            "rows": [
                {
                    "guideline_id": expected[i]["guideline_id"],
                    "source_ids": ["fixture-source"],
                    "mechanisms": [mechanism],
                    "expected_evidence": ["analysis"],
                    "manual_evidence": [],
                }
                for i, mechanism in enumerate([tool, manual])
            ],
            "review_state": "pending_human",
        }
    )


def controls(tmp: Path, *, clean: bool = False) -> Path:
    from tests.quality_import_support import sarif

    imported = selection(tmp, native=sarif([]) if clean else None)
    _, report, _, _ = imports.import_outputs(imported)
    selected = json.loads(imported.read_text())
    request = {
        "schema_version": 1,
        "kind": "quality_coverage_request",
        "profile": selected["profile"],
        "baseline": selected["baseline"],
        "manifest": write_json(tmp / "mapping.json", manifest(tmp)),
        "previous_manifest": None,
        "analyses": [{"request": ref(imported), "report": write_json(tmp / "report.json", report)}],
        "protected_roots": [str(ROOT)],
    }
    path = tmp / "coverage.json"
    write_json(path, request)
    return path


def change_mapping(path: Path, **changes: Any) -> dict[str, Any]:
    request = json.loads(path.read_text())
    p = Path(request["manifest"]["path"])
    value = json.loads(p.read_text())
    value.update(changes)
    value = seal(value)
    request["manifest"] = write_json(p, value)
    write_json(path, request)
    return value
