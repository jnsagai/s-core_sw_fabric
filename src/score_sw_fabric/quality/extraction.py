"""Independent declared extraction, phase and native report completeness checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import input_file
from score_sw_fabric.assurance.models import (
    bounded_list,
    digest,
    exact,
    sha,
    verify_digest,
    version,
)
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.import_models import ImportInputs, choice, strings, units
from score_sw_fabric.quality.models import raw_bytes
from score_sw_fabric.quality.sarif import Locations
from score_sw_fabric.runtime.request import _local

MANIFEST_FIELDS = {"source_digest", "observations", "outer_exit_code", "digest"}
OBSERVATION_FIELDS = {
    "tool",
    "identity_digest",
    "processed_units",
    "extracted_units",
    "exclusions",
    "warnings",
    "errors",
    "failed_queries",
    "filtered_checks",
    "required_reports",
    "phases",
}
PHASE_FIELDS = {"id", "role", "status", "exit_code", "timed_out", "artifacts"}
CODEQL_REPORTS = {
    "database_integrity_report.md",
    "deviations_report.md",
    "guideline_recategorizations_report.md",
    "guideline_compliance_summary.md",
}


def native_integrity(
    artifact: dict[str, Any], files: dict[str, bytes]
) -> tuple[list[str], list[str]]:
    """Check the native pinned report's counts/listing, without trusting compliance strings."""
    if artifact["raw"]["truncated"]:
        return [], ["OUTPUT_TRUNCATED"]
    try:
        text = raw_bytes(artifact["raw"]).decode("utf-8")
    except UnicodeError:
        return [], ["NATIVE_REPORT_INVALID"]
    counts = re.findall(r"^\s*-\s*(\d{1,6}) successfully analyzed files\s*$", text, re.M)
    errors = re.findall(r"^\s*-\s*(\d{1,6}) errors reported\s*$", text, re.M)
    listing = re.findall(r"^## Successfully extracted files\s*\n(.*)", text, re.M | re.S)
    if (
        "# Database integrity report" not in text.splitlines()
        or len(counts) != 1
        or len(errors) != 1
        or len(listing) != 1
    ):
        return [], ["NATIVE_REPORT_INVALID"]
    lines = listing[0].split("\n## ", 1)[0].splitlines()
    names = []
    resolver = Locations({}, Path(artifact["source_root"]), files)
    for line in lines:
        if not line.strip():
            continue
        match = re.fullmatch(r"\s*-\s+(.+?)\s*", line)
        if not match:
            return [], ["NATIVE_REPORT_INVALID"]
        try:
            names.append(resolver.artifact({"uri": match[1]}))
        except InputError:
            return [], ["NATIVE_EXTRACTION_UNRESOLVED"]
    if len(names) > 500 or len(names) != len(set(names)) or len(names) != int(counts[0]):
        return [], ["NATIVE_REPORT_INVALID"]
    gaps = ["EXTRACTION_ERROR"] if int(errors[0]) else []
    if "## Extraction errors" in text:
        body = text.split("## Extraction errors", 1)[1].split("## Successfully extracted files", 1)[
            0
        ]
        table = [line for line in body.splitlines() if line.lstrip().startswith("|")]
        if max(0, len(table) - 2) != int(errors[0]):
            gaps.append("NATIVE_REPORT_INVALID")
    return sorted(n for n in names if Path(n).suffix in {".cpp", ".cc", ".cxx"}), gaps


def assess(
    selected: ImportInputs, native_findings: list[dict[str, Any]], base: Path
) -> dict[str, Any]:
    m = version(selected.manifest, "quality_extraction_manifest", MANIFEST_FIELDS, "/extraction")
    verify_digest(m, "/extraction")
    sha(m["source_digest"], "/extraction/source_digest")
    global_gaps = list(selected.gaps)
    if m["source_digest"] != selected.baseline["source_digest"]:
        global_gaps.append("BASELINE_DRIFT")
    if m["outer_exit_code"] is not None and type(m["outer_exit_code"]) is not int:
        raise InputError("FIELD_TYPE", "Outer exit code must be integer or null")
    if m["outer_exit_code"] != 0:
        global_gaps.append("PHASE_FAILED")
    artifacts = {a["id"]: a for a in selected.artifacts}
    observations = {}
    for raw in bounded_list(m["observations"], 32, "/observations"):
        o = exact(raw, OBSERVATION_FIELDS, "/observations")
        tool = choice(o["tool"], set(selected.identities), "/observation/tool")
        if tool in observations:
            raise InputError("DUPLICATE_ID", "Duplicate extraction observation")
        observations[tool] = o
    assessments: list[dict[str, Any]] = []
    expected = selected.baseline["expected_units"]
    for tool, identity in selected.identities.items():
        if tool not in observations:
            assessments.append(
                {"tool": tool, "adequacy": "incomplete", "gaps": ["EXTRACTION_UNOBSERVED"]}
            )
            global_gaps.append("EXTRACTION_UNOBSERVED")
            continue
        o = observations[tool]
        gaps = list(global_gaps)
        if sha(o["identity_digest"], "/identity_digest") != digest(identity):
            gaps.append("TOOL_IDENTITY_MISMATCH")
        processed = units(o["processed_units"], "/processed_units", selected.files)
        extracted = o["extracted_units"]
        if extracted is not None:
            extracted = units(extracted, "/extracted_units", selected.files)
        if tool != "codeql" and extracted is not None:
            raise InputError("FIELD_ENUM", "Non-CodeQL observation must not claim extraction")
        for name, gap in [
            ("warnings", "EXTRACTION_WARNING"),
            ("errors", "EXTRACTION_ERROR"),
            ("failed_queries", "QUERY_FAILED"),
            ("filtered_checks", "CHECK_CONFIGURATION_INCOMPLETE"),
        ]:
            if strings(o[name], "/" + name):
                gaps.append(gap)
        for raw in bounded_list(o["exclusions"], 500, "/exclusions"):
            exclusion = exact(raw, {"unit", "reason", "justification"}, "/exclusion")
            units([exclusion["unit"]], "/exclusion/unit", selected.files)
            strings([exclusion["reason"]], "/exclusion/reason")
            if exclusion["justification"] is not None:
                ref = exact(exclusion["justification"], {"path", "sha256"}, "/justification")
                fp = _local(base, ref["path"], "/justification/path")
                try:
                    size = fp.stat().st_size
                except OSError as exc:
                    raise InputError("INPUT_INVALID", "Justification file unavailable") from exc
                if size > 1024 * 1024:
                    raise InputError("LIMIT_EXCEEDED", "Justification exceeds 1 MiB")
                path, _ = input_file(base, ref, "/justification")
                selected.inputs.append(path)
            gaps.append("EXCLUSION_PENDING_REVIEW")
        reports = set(strings(o["required_reports"], "/required_reports", 500))
        if tool == "codeql":
            reports |= CODEQL_REPORTS
        diagnostic_ids = {
            a["id"] for a in selected.artifacts if a["tool"] == tool and a["role"] == "diagnostics"
        }
        artifact_units = {u for name in diagnostic_ids for u in artifacts[name]["units"]}
        if not diagnostic_ids:
            gaps.append("REPORT_MISSING")
        if set(processed) != artifact_units:
            gaps.append("PROCESSING_MANIFEST_MISMATCH")
        phase_ids = set()
        phase_roles: set[str] = set()
        analyzed: set[str] = set()
        reported: set[str] = set()
        findings = [f for f in native_findings if f["tool"] == tool]
        for raw in bounded_list(o["phases"], 1000, "/phases"):
            phase = exact(raw, PHASE_FIELDS, "/phase")
            name = strings([phase["id"]], "/phase/id")[0]
            if name in phase_ids:
                raise InputError("DUPLICATE_ID", "Duplicate phase ID")
            phase_ids.add(name)
            role = choice(phase["role"], {"extract", "analyze", "report"}, "/phase/role")
            choice(phase["status"], {"completed", "failed", "missing"}, "/phase/status")
            if type(phase["timed_out"]) is not bool or (
                phase["exit_code"] is not None and type(phase["exit_code"]) is not int
            ):
                raise InputError("FIELD_TYPE", "Malformed phase status")
            refs = strings(phase["artifacts"], "/phase/artifacts", 500)
            if any(a not in artifacts or artifacts[a]["tool"] != tool for a in refs):
                raise InputError(
                    "NATIVE_REFERENCE_UNRESOLVED", "Phase artifact/tool does not resolve"
                )
            diagnostic_exit = {"clang-tidy": 1, "cppcheck": 2, "asan": 55, "ubsan": 55}.get(tool)
            matching = [f for f in findings if f["artifact_id"] in refs]
            accepted_exit = phase["exit_code"] == 0 or (
                role == "analyze"
                and diagnostic_exit is not None
                and matching
                and phase["exit_code"] == diagnostic_exit
            )
            if phase["status"] != "completed" or phase["timed_out"] or not accepted_exit:
                gaps.append("PHASE_FAILED")
            else:
                phase_roles.add(role)
                if role == "analyze":
                    analyzed.update(refs)
                elif role == "report":
                    reported.update(refs)
        if "analyze" not in phase_roles or not diagnostic_ids <= analyzed:
            gaps.append("REPORT_MISSING")
        for name in reports:
            if (
                name not in artifacts
                or artifacts[name]["tool"] != tool
                or artifacts[name]["role"] != "supporting"
                or name not in reported
            ):
                gaps.append("REPORT_MISSING")
        native_units = None
        if tool == "codeql":
            if extracted is None:
                gaps.append("EXTRACTION_UNKNOWN")
            if not {"extract", "report"} <= phase_roles:
                gaps.append("PHASE_FAILED")
            report = artifacts.get("database_integrity_report.md")
            if report is not None and report["tool"] == tool:
                native_units, failures = native_integrity(report, selected.files)
                gaps.extend(failures)
                if extracted is not None and set(native_units) != set(extracted):
                    gaps.append("NATIVE_EXTRACTION_MISMATCH")
        actual = extracted if tool == "codeql" and extracted is not None else processed
        if expected is None:
            missing, unexpected = [], actual
            gaps.append("EXTRACTION_UNKNOWN")
        else:
            missing = sorted(set(expected) - set(actual))
            unexpected = sorted(set(actual) - set(expected))
            if not expected or not actual or not processed:
                gaps.append("EXTRACTION_EMPTY")
            if missing or unexpected or set(processed) != set(expected):
                gaps.append("EXTRACTION_PARTIAL")
        gaps = sorted(set(gaps))
        assessments.append(
            {
                **o,
                "missing_units": missing,
                "unexpected_units": unexpected,
                "native_extracted_units": native_units,
                "gaps": gaps,
                "adequacy": "unknown" if expected is None else "incomplete" if gaps else "adequate",
            }
        )
    combined = sorted(set(global_gaps + [g for o in assessments for g in o["gaps"]]))
    return {
        "manifest": m,
        "expected_state": "unknown" if expected is None else "declared",
        "expected_units": expected,
        "observations": assessments,
        "gaps": combined,
        "adequacy": "unknown" if expected is None else "incomplete" if combined else "adequate",
        "limitations": [
            "Imported phase/source/identity declarations remain unverified.",
            "Structural adequacy is not CodeQL eligibility or MISRA coverage.",
        ],
    }
