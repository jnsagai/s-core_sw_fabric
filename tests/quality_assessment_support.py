"""Independent assessment selections, with explicit source freshness and fixture time."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from score_sw_fabric.quality import packet
from tests.quality_import_support import write_json
from tests.quality_packet_support import packet_request


def assessment_request(tmp: Path, **changes: Any) -> Path:
    selected = packet_request(tmp)
    _, record, _, _ = packet.packet(selected)
    current = json.loads(selected.read_text())
    matrix_request = json.loads(Path(current["coverage"]["request"]["path"]).read_text())
    request = {
        "schema_version": 1,
        "kind": "quality_assessment_request",
        "profile": current["profile"],
        "packet": write_json(tmp / "packet.json", record),
        "current_baseline": matrix_request["baseline"],
        "decisions": [],
        "assurance_domain": "fixture_contract",
        "as_of": "2026-12-01T10:00:00Z",
        "protected_roots": [],
    }
    request.update(changes)
    path = tmp / "assessment-request.json"
    write_json(path, request)
    return path
