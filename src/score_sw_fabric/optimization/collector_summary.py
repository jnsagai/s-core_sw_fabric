"""Compact collector feedback with unchanged host evidence references."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, canonical, raw_file, record
from score_sw_fabric.optimization.evidence_query import query
from score_sw_fabric.process_source.reader import InputError


def collector_summary(result: dict[str, Any], directory: Path) -> dict[str, Any]:
    raw = directory / "result.json"
    if not raw.exists():
        raw = directory / "measurement.json"
    data = raw.read_bytes()
    fields: dict[str, Any] = {
        "check_ref": result.get("check_ref"),
        "status": result.get("status", "unknown"),
        "raw": {"path": str(raw), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)},
        "engineering_acceptance": "pending",
        "origin": "local_unprotected_measurement",
        "command_failures": sum(i.get("exit_code") != 0 for i in result.get("commands", [])),
        "blockers": [str(i) for i in result.get("blockers", []) if len(str(i).encode()) <= 160][:8],
        "blocker_total": len(result.get("blockers", [])),
        "findings_count": len(result.get("findings", []))
        if isinstance(result.get("findings"), list)
        else None,
        "structured_evidence": [],
    }
    for name in ("check_ref", "status"):
        value = fields[name]
        if value is not None and (not isinstance(value, str) or len(value.encode()) > 160):
            fields[name] = None
            fields.setdefault("omitted_fields", []).append(name)
    for path in sorted(directory.glob("*.sarif"))[:3]:
        try:
            normalized = query(directory, path.name, operation="findings", limit=5, max_bytes=3000)
        except InputError as error:
            _, reference = raw_file(directory, path.name)
            normalized = {"raw": reference, "state": "unavailable", "reason": error.code}
        fields["structured_evidence"].append(normalized)
    summary = record("collector_summary", **fields)
    while len(canonical(summary)) > 4999 and fields["structured_evidence"]:
        fields["structured_evidence"].pop()
        fields["omitted_evidence_queries"] = True
        summary = record("collector_summary", **fields)
    if len(canonical(summary)) > 4999:
        raise OptimizationError("RESULT_LIMIT")
    return summary
