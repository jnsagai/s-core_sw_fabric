"""Draft/request selections; every approval-like field is unauthenticated."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import seal
from tests.quality_support import ROOT, ref


def write(path: Path, record: dict[str, Any]) -> dict[str, str]:
    path.write_text(json.dumps(record))
    return ref(path)


def selection(
    tmp: Path,
    origin: dict[str, Any],
    current: Path,
    adapter: str = "clang-tidy",
    **changes: Any,
) -> Path:
    findings = origin.get("diagnostics", origin.get("findings", []))
    index = next((i for i, f in enumerate(findings) if "NullDereference" in f["native_id"]), 0)
    baseline = origin["baseline"]
    source = baseline["files"][0]
    draft = seal(
        {
            "schema_version": 1,
            "kind": "quality_disposition_draft",
            "id": "draft_probe",
            "requested_kind": "correction",
            "origin_digest": origin["digest"],
            "finding_index": index,
            "construct": {"kind": "file", **source},
            "scope": {
                "component": baseline["component"],
                "translation_units": baseline["expected_units"],
            },
            "native_category": None,
            "rationale": "Draft change for independent review",
            "impact": {"safety": "Requires review", "security": "Requires review"},
            "alternatives": ["Remove unsafe construct"],
            "compensating_evidence": [],
            "expires_at": None,
            "review_triggers": ["Changed source or configuration"],
            "native_metadata": {"approved-by": "agent", "approved-on": "2026-09-30"},
            "decision_refs": [],
        }
    )
    path = tmp / "disposition-request.json"
    record = {
        "schema_version": 1,
        "kind": "quality_disposition_request",
        "origin": write(tmp / "origin.json", origin),
        "draft": write(tmp / "draft.json", draft),
        "current": {"adapter": adapter, "request": ref(current)},
        "previous": None,
        "action": "draft",
        "protected_roots": [str(ROOT)],
    }
    record.update(changes)
    write(path, record)
    return path


def change_draft(path: Path, **changes: Any) -> None:
    request = json.loads(path.read_text())
    target = Path(request["draft"]["path"])
    draft = json.loads(target.read_text())
    draft.update(changes)
    request["draft"] = write(target, seal(draft))
    write(path, request)


def change_request(path: Path, **changes: Any) -> None:
    record = json.loads(path.read_text())
    record.update(changes)
    write(path, record)
