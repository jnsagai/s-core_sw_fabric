"""Original Cppcheck XML v2, native identities and bounded independent TU execution."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.models import Budget, Inputs, environment, execute, raw_bytes

INCOMPLETE_IDS = {
    "missingInclude",
    "missingIncludeSystem",
    "syntaxError",
    "internalError",
    "cppcheckError",
    "toomanyconfigs",
    "unknownMacro",
    "preprocessorErrorDirective",
}


def parse_report(
    data: bytes, artifact_id: str, source: Path, files: dict[str, bytes], expected_version: str
) -> list[dict[str, Any]]:
    if (
        len(data) > 16 * 1024 * 1024
        or b"\x00" in data
        or b"<!DOCTYPE" in data.upper()
        or b"<!ENTITY" in data.upper()
    ):
        raise InputError("NATIVE_OUTPUT_INVALID", "XML entities/oversize output are unsupported")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise InputError("NATIVE_OUTPUT_INVALID", "Invalid Cppcheck XML") from exc
    version = root.find("cppcheck")
    errors = root.find("errors")
    if (
        root.tag != "results"
        or root.get("version") != "2"
        or version is None
        or version.get("version") != expected_version
        or errors is None
    ):
        raise InputError(
            "NATIVE_OUTPUT_INVALID", "Cppcheck report/schema/version differs from selection"
        )
    entries = list(errors)
    if len(entries) > 10000 or any(e.tag != "error" for e in entries):
        raise InputError("NATIVE_OUTPUT_INVALID", "Unsupported Cppcheck error collection")
    findings = []
    for index, error in enumerate(entries):
        if not error.get("id") or not error.get("severity") or error.get("msg") is None:
            raise InputError("NATIVE_OUTPUT_INVALID", "Native diagnostic identity missing")
        locations = []
        nodes = error.findall("location")
        if len(nodes) > 1000:
            raise InputError("LIMIT_EXCEEDED", "Too many related native locations")
        for loc in nodes:
            raw = loc.get("file", "")
            if not raw:
                relative = None
            else:
                path = Path(raw)
                path = path if path.is_absolute() else source / path
                if not path.is_relative_to(source):
                    raise InputError(
                        "NATIVE_LOCATION_UNRESOLVED", "Native path is outside frozen files"
                    )
                relative = str(path.relative_to(source))
                if relative not in files:
                    raise InputError("NATIVE_LOCATION_UNRESOLVED", "Native path is not selected")
            try:
                line, column = int(loc.get("line", "0")), int(loc.get("column", "0"))
            except ValueError as exc:
                raise InputError("NATIVE_OUTPUT_INVALID", "Invalid native position") from exc
            if (
                line < 0
                or column < 0
                or (relative is not None and line > len(files[relative].splitlines()))
            ):
                raise InputError(
                    "NATIVE_LOCATION_UNRESOLVED", "Native line is outside frozen bytes"
                )
            locations.append(
                {
                    "path": relative,
                    "line": line,
                    "column": column,
                    "native_attributes": dict(loc.attrib),
                }
            )
        findings.append(
            {
                "native_id": error.get("id"),
                "native_level": error.get("severity"),
                "artifact_id": artifact_id,
                "result_index": index,
                "locations": locations,
                "native_record": {
                    "attributes": dict(error.attrib),
                    "children_xml": [ET.tostring(c, encoding="unicode") for c in error],
                },
            }
        )
    return findings


def arguments(selected: Inputs, source: Path, units: list[str]) -> list[str]:
    c = selected.settings
    return [
        selected.toolchain["tool"]["path"],
        "--std=c++17",
        "--language=c++",
        "--enable=" + ",".join(c["enable"]),
        "--platform=" + c["platform"],
        f"--max-configs={c['max_configs']}",
        "--xml",
        "--xml-version=2",
        "--error-exitcode=2",
        *["-I" + str(source / d) for d in selected.request.get("include_dirs", [])],
        *["-D" + d for d in selected.request.get("defines", [])],
        *[str(source / u) for u in units],
    ]


def analyze(
    selected: Inputs, work: Path, budget: Budget, units: list[str], data: dict[str, bytes]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str], list[str]]:
    phases = []
    artifacts = []
    diagnostics = []
    processed = []
    gaps = []
    source = work / "source"
    for index, unit in enumerate(units):
        phase = execute(
            "analyze:" + unit,
            arguments(selected, source, [unit]),
            work,
            selected.request["timeout_seconds"],
            budget,
            environment(work, selected.toolchain),
        )
        phases.append(phase)
        raw = {
            **phase["stderr"],
            "format": "cppcheck-xml",
            "id": f"cppcheck-{index}",
            "translation_unit": unit,
        }
        artifacts.append(raw)
        if any(phase[k]["truncated"] for k in ("stdout", "stderr")):
            gaps.append("OUTPUT_TRUNCATED")
            break
        try:
            results = parse_report(
                raw_bytes(raw),
                raw["id"],
                source,
                data,
                selected.toolchain["tool"]["version"].removeprefix("Cppcheck "),
            )
        except InputError as exc:
            gaps.append(exc.code)
            results = []
        diagnostics.extend(results)
        if any(d["native_id"] in INCOMPLETE_IDS for d in results):
            gaps.append("CPPCHECK_ANALYSIS_INCOMPLETE")
        if (
            phase["timed_out"]
            or phase["error"]
            or phase["exit_code"] not in (0, 2)
            or (phase["exit_code"] == 2 and not results)
        ):
            gaps.append("PHASE_FAILED")
        elif results or (phase["exit_code"] == 0 and not gaps):
            processed.append(unit)
        if len(diagnostics) > 10000:
            diagnostics = diagnostics[:10000]
            gaps.append("FINDING_LIMIT_EXCEEDED")
            break
        if phase["timed_out"] or budget.remaining == 0:
            break
    return phases, artifacts, diagnostics, processed, gaps
