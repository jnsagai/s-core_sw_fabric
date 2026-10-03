"""Bounded SARIF/JSON queries preserving raw identity; never return raw messages."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from score_sw_fabric.optimization.common import (
    OptimizationError,
    canonical,
    integer,
    json_object,
    raw_file,
    record,
)

OPERATIONS = {"summary", "findings", "count_by_rule", "count_by_path", "json_summary"}


def _field(value: Any, gaps: list[int]) -> str | None:
    if isinstance(value, str) and value and len(value.encode()) <= 512:
        return value
    gaps[0] += 1
    return None


def _findings(value: dict[str, Any], gaps: list[int]) -> list[dict[str, Any]]:
    runs = value.get("runs")
    if not isinstance(runs, list) or not runs or len(runs) > 1000:
        raise OptimizationError("SARIF_RUNS")
    result: list[dict[str, Any]] = []
    for run_index, run in enumerate(runs):
        if not isinstance(run, dict) or not isinstance(run.get("results"), list):
            raise OptimizationError("SARIF_RESULTS")
        tool = run.get("tool", {})
        if not isinstance(tool, dict) or not isinstance(tool.get("driver", {}), dict):
            raise OptimizationError("SARIF_TOOL")
        driver = tool.get("driver", {})
        rules = driver.get("rules", [])
        artifacts = run.get("artifacts", [])
        if not isinstance(rules, list) or not all(isinstance(item, dict) for item in rules):
            raise OptimizationError("SARIF_RULES")
        if not isinstance(artifacts, list) or not all(
            isinstance(item, dict) and isinstance(item.get("location", {}), dict)
            for item in artifacts
        ):
            raise OptimizationError("SARIF_ARTIFACTS")
        for index, raw in enumerate(run["results"]):
            if len(result) >= 100_000 or not isinstance(raw, dict):
                raise OptimizationError("FINDING_LIMIT")
            rule = raw.get("ruleId")
            if rule is None and type(raw.get("ruleIndex")) is int:
                position = raw["ruleIndex"]
                if isinstance(rules, list) and 0 <= position < len(rules):
                    rule = rules[position].get("id")
            locations = []
            raw_locations = raw.get("locations", [])
            if not isinstance(raw_locations, list):
                raise OptimizationError("SARIF_LOCATIONS")
            if len(raw_locations) > 10000:
                raise OptimizationError("SARIF_LOCATION_LIMIT")
            for location in raw_locations:
                if not isinstance(location, dict):
                    gaps[0] += 1
                    continue
                physical = location.get("physicalLocation", {})
                if not isinstance(physical, dict):
                    raise OptimizationError("SARIF_LOCATION")
                artifact = physical.get("artifactLocation", {})
                if not isinstance(artifact, dict):
                    raise OptimizationError("SARIF_LOCATION")
                uri = artifact.get("uri")
                position = artifact.get("index")
                if uri is None and type(position) is int and 0 <= position < len(artifacts):
                    uri = artifacts[position].get("location", {}).get("uri")
                path = _field(uri, gaps)
                region = physical.get("region", {})
                if not isinstance(region, dict):
                    raise OptimizationError("SARIF_REGION")
                line = region.get("startLine")
                if line is not None and (type(line) is not int or line <= 0):
                    line = None
                    gaps[0] += 1
                locations.append({"path": path, "line": line})
            result.append(
                {
                    "id": f"run:{run_index}/result:{index}",
                    "rule": _field(rule, gaps),
                    "locations": locations,
                    "locations_omitted": 0,
                    "suppressed": bool(raw.get("suppressions")),
                }
            )
    return result


def query(
    root: Path,
    path: str,
    *,
    operation: str = "summary",
    rule: str | None = None,
    file: str | None = None,
    line: int | None = None,
    offset: int = 0,
    limit: int = 10,
    expected_sha256: str | None = None,
    max_bytes: int = 12000,
) -> dict[str, Any]:
    if operation not in OPERATIONS:
        raise OptimizationError("QUERY_OPERATION")
    integer(limit, minimum=1, maximum=30)
    integer(max_bytes, minimum=1, maximum=12000)
    integer(offset)
    if line is not None:
        integer(line, minimum=1)
    for field in (rule, file):
        if field is not None and (not isinstance(field, str) or len(field.encode()) > 512):
            raise OptimizationError("FILTER_LIMIT")
    data, raw = raw_file(root, path, expected_sha256)
    value = json_object(data)
    if operation == "json_summary":
        selected = sorted(value)[offset : offset + limit]
        keys = [key for key in selected if len(key.encode()) <= 128]
        result = record(
            "evidence_summary",
            raw=raw,
            total=len(value),
            keys=keys,
            types={key: type(value[key]).__name__ for key in keys},
            omitted_fields=len(selected) - len(keys),
            offset=offset,
            next_offset=offset + limit if offset + limit < len(value) else None,
        )
    else:
        gaps = [0]
        findings = _findings(value, gaps)
        selected_findings = [
            item
            for item in findings
            if (rule is None or item["rule"] == rule)
            and (file is None or any(p["path"] == file for p in item["locations"]))
            and (
                line is None
                or any(
                    p["line"] == line and (file is None or p["path"] == file)
                    for p in item["locations"]
                )
            )
        ]
        counts: Counter[str] = Counter()
        if operation == "count_by_rule":
            counts.update(item["rule"] for item in selected_findings if item["rule"] is not None)
        elif operation == "count_by_path":
            counts.update(
                p["path"]
                for item in selected_findings
                for p in item["locations"]
                if p["path"] is not None
            )
        rows: list[dict[str, Any]] = (
            [{"key": key, "count": counts[key]} for key in sorted(counts)]
            if counts or operation.startswith("count_")
            else selected_findings
        )
        page = rows[offset : offset + limit] if operation != "summary" else []
        if operation == "findings":
            bounded_page = []
            for item in page:
                locations = [
                    location
                    for location in item["locations"]
                    if (file is None or location["path"] == file)
                    and (line is None or location["line"] == line)
                ]
                bounded_page.append(
                    {
                        **item,
                        "locations": locations[:5],
                        "locations_omitted": len(item["locations"]) - len(locations[:5]),
                    }
                )
            page = bounded_page
        fields: dict[str, Any] = {
            "raw": raw,
            "operation": operation,
            "total": len(selected_findings),
            "location_gaps": sum(not i["locations"] for i in findings),
            "omitted_fields": gaps[0],
            "offset": offset,
            "next_offset": offset + len(page) if offset + len(page) < len(rows) and page else None,
            "suppressed": sum(i["suppressed"] for i in selected_findings),
        }
        fields["counts" if operation.startswith("count_") else "findings"] = page
        result = record("evidence_summary", **fields)
        # Shrink only row count; never clip exact native identity into a fabricated value.
        while len(canonical(result)) > max_bytes and page:
            page = page[:-1]
            fields["counts" if operation.startswith("count_") else "findings"] = page
            fields["next_offset"] = offset + len(page)
            fields["truncated"] = True
            result = record("evidence_summary", **fields)
    if len(canonical(result)) > max_bytes:
        raise OptimizationError("RESULT_LIMIT")
    return result
