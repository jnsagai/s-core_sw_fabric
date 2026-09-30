"""Explicit portable source and notice selections; no engineering acceptance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from score_sw_fabric.quality import coverage
from tests.quality_coverage_support import controls
from tests.quality_import_support import write_json
from tests.quality_support import ROOT, ref


def packet_request(tmp: Path, **changes: Any) -> Path:
    selected = controls(tmp)
    _, matrix, _, _ = coverage.measure(selected)
    original = json.loads(selected.read_text())
    notice = tmp / "NOTICE.txt"
    notice.write_text(
        "Synthetic fixtures; no proprietary guideline text or production authority.\n"
    )
    request = {
        "schema_version": 1,
        "kind": "quality_packet_request",
        "profile": original["profile"],
        "coverage": {"request": ref(selected), "report": write_json(tmp / "matrix.json", matrix)},
        "analyses": [],
        "dispositions": [],
        "source_snapshots": [
            {"baseline_digest": matrix["baseline"]["full_digest"], "root": str(tmp / "source")}
        ],
        "notices": [
            {
                "id": "fixture-notice",
                "license": "synthetic fixture",
                "notice": "Test only",
                "applies_to": [
                    "tool:codeql",
                    *("native:" + s["id"] for s in matrix["profile"]["native_sources"]),
                ],
                "ref": ref(notice),
            }
        ],
        "protected_roots": [str(ROOT)],
    }
    request.update(changes)
    path = tmp / "packet-request.json"
    write_json(path, request)
    return path
