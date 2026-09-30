"""Portable, review-only milestone report for local unit verification runs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import (
    READINESS,
    input_file,
    json_file,
    load_request,
    protected_roots,
)
from score_sw_fabric.assurance.models import seal, verify_digest
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.verification.profile import load_profile

REPORT_FIELDS = {"profile", "design_report", "runs", "safety_reports", "protected_roots"}


def _records(
    base: Path, values: Any, kind: str, pointer: str
) -> tuple[list[dict[str, Any]], list[Path]]:
    if not isinstance(values, list) or len(values) > 100:
        raise InputError("LIMIT_EXCEEDED", "Report inputs must be a bounded list", pointer)
    records: list[dict[str, Any]] = []
    paths: list[Path] = []
    for index, value in enumerate(values):
        path, _, record = json_file(base, value, f"{pointer}/{index}")
        verify_digest(record, f"{pointer}/{index}")
        if record.get("kind") != kind or record.get("schema_version") != 1:
            raise InputError("FIELD_ENUM", f"Expected {kind}", f"{pointer}/{index}")
        records.append(record)
        paths.append(path)
    return records, paths


def build_report(
    profile: dict[str, Any],
    design: dict[str, Any],
    runs: list[dict[str, Any]],
    safety: list[dict[str, Any]],
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if not runs:
        findings.append(
            {"code": "BASELINE_MISMATCH", "subject": "runs", "detail": "No verification run"}
        )
    component = design["component"]
    profile_id = design["profile"]["id"]
    for index, record in enumerate(runs):
        if record["component"] != component or record["profile"]["id"] != profile_id:
            findings.append(
                {
                    "code": "BASELINE_MISMATCH",
                    "subject": f"runs/{index}",
                    "detail": "Component or profile differs",
                }
            )
        if (
            record.get("origin") != "local_unprotected_execution"
            or record.get("assurance_eligibility") != "not_eligible"
        ):
            raise InputError("EVIDENCE_ORIGIN", "Run has an unsupported origin", f"/runs/{index}")
    for index, record in enumerate(safety):
        if record["component"] != component:
            findings.append(
                {
                    "code": "BASELINE_MISMATCH",
                    "subject": f"safety_reports/{index}",
                    "detail": "Component differs",
                }
            )
    current = runs[-1] if runs else None
    if current is not None:
        source_files = {item["path"]: item["sha256"] for item in current["baseline"]["sources"]}
        design_files = {item["path"]: item["sha256"] for item in design["files"]["sources"]}
        if source_files != design_files:
            findings.append(
                {
                    "code": "BASELINE_MISMATCH",
                    "subject": "design",
                    "detail": "Design and current source bytes differ",
                }
            )
    if design["outcome"] != "complete":
        findings.append(
            {
                "code": "DESIGN_BLOCKED",
                "subject": "design",
                "detail": "Design checks are incomplete",
            }
        )

    seen: dict[str, set[str]] = {}
    failures: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    for index, run in enumerate(runs):
        baseline = run["baseline"]
        key = baseline["full_digest"]
        seen.setdefault(key, set()).add(run["outcome"])
        history.append(
            {
                "run": index,
                "digest": run["digest"],
                "full_digest": key,
                "source_digest": baseline["source_digest"],
                "outcome": run["outcome"],
            }
        )
        if run["outcome"] != "passed":
            routes = []
            for item in run["requirements"]:
                if item["state"] == "failing":
                    units: list[str] = next(
                        (
                            entry["implemented_by"]
                            for entry in design["requirements"]
                            if entry["id"] == item["id"]
                        ),
                        [],
                    )
                    routes.append(
                        {"requirement": item["id"], "units": units, "tests": item["failing"]}
                    )
            failures.append(
                {
                    "run": index,
                    "digest": run["digest"],
                    "source_digest": baseline["source_digest"],
                    "findings": run["findings"],
                    "routes": routes,
                    "diagnostics": {"build": run["build"]["steps"], "execution": run["execution"]},
                    "resolved": False,
                }
            )
    for failure in failures:
        failure["resolved"] = any(
            later["outcome"] == "passed"
            and later["baseline"]["source_digest"] != failure["source_digest"]
            for later in runs[failure["run"] + 1 :]
        )
        if not failure["resolved"]:
            findings.append(
                {
                    "code": "FAILURE_OPEN",
                    "subject": f"runs/{failure['run']}",
                    "detail": "No changed-source passing run",
                }
            )
    nondeterminism = sorted(
        key for key, outcomes in seen.items() if "passed" in outcomes and len(outcomes) > 1
    )
    for key in nondeterminism:
        findings.append(
            {
                "code": "NONDETERMINISTIC_RESULT",
                "subject": key,
                "detail": "Same baseline has conflicting outcomes",
            }
        )
    attempts = len(runs)
    if (
        failures
        and attempts >= profile["loop"]["max_attempts"]
        and not all(item["resolved"] for item in failures)
    ):
        findings.append(
            {
                "code": "ESCALATE_TO_HUMAN",
                "subject": "attempts",
                "detail": "Attempt budget exhausted",
            }
        )

    matrix = current["requirements"] if current else []
    candidates = sorted(
        {target for report in safety for item in report["items"] for target in item["mitigated_by"]}
    )
    safety_context = [
        {
            "digest": report["digest"],
            "analysis": report["analysis"],
            "profile": report["profile"],
            "outcome": report["outcome"],
        }
        for report in safety
    ]
    requirement_ids = {item["id"] for item in matrix}
    mitigations = [
        {
            "requirement": target,
            "unit_result": next(
                (item["state"] for item in matrix if item["id"] == target), "not_in_unit_scope"
            ),
            "candidate_only": target in requirement_ids,
            "closure_evidence": "missing_005_verified_evidence",
        }
        for target in candidates
    ]
    inspection = {
        "design_digest": design["digest"],
        "units": [{"path": item["path"], "sha256": item["sha256"]} for item in design["units"]],
        "checklist": [
            {
                "id": item["id"],
                "criterion": item["criterion"],
                "source": item["source"],
                "answer": "pending_human",
            }
            for item in profile["inspection_checklist"]
        ],
    }
    outcome = (
        "blocked"
        if any(
            item["code"]
            in {
                "BASELINE_MISMATCH",
                "DESIGN_BLOCKED",
                "NONDETERMINISTIC_RESULT",
                "ESCALATE_TO_HUMAN",
            }
            for item in findings
        )
        else "failures_open"
        if findings or current is None or current["outcome"] != "passed"
        else "verified_on_baseline"
    )
    return {
        "schema_version": 1,
        "kind": "verification_milestone_report",
        "component": component,
        "profile": design["profile"],
        "current": None if current is None else history[-1],
        "history": history,
        "failures": failures,
        "nondeterminism": nondeterminism,
        "attempts": {"used": attempts, "max": profile["loop"]["max_attempts"]},
        "requirement_matrix": matrix,
        "mitigation_candidates": mitigations,
        "safety_context": safety_context,
        "inspection_packet": inspection,
        "pending_obligations": profile["pending_obligations"],
        "findings": findings,
        "outcome": outcome,
        "origin": "local_unprotected_execution",
        "assurance_eligibility": "not_eligible",
        "engineering_readiness": READINESS,
        "limitations": [
            "No protected 005 evidence or accepted design is inferred from this report."
        ],
    }


def report(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    record, base = load_request(request_path, "verification_report_request", REPORT_FIELDS)
    profile_path, profile_bytes = input_file(base, record["profile"], "/profile")
    profile = load_profile(profile_bytes)
    designs, design_paths = _records(
        base, [record["design_report"]], "detailed_design_report", "/design_report"
    )
    runs, run_paths = _records(base, record["runs"], "unit_verification_run", "/runs")
    safety, safety_paths = _records(
        base, record["safety_reports"], "safety_analysis_report", "/safety_reports"
    )
    design = designs[0]
    if design["profile"] != {
        "id": profile["id"],
        "sha256": hashlib.sha256(profile_bytes).hexdigest(),
    }:
        raise InputError("PROFILE_MISMATCH", "Design profile differs", "/design_report")
    if any(run["profile"] != design["profile"] for run in runs):
        raise InputError("PROFILE_MISMATCH", "Run profile differs", "/runs")
    result = seal(build_report(profile, design, runs, safety))
    return (
        (0 if result["outcome"] == "verified_on_baseline" else 1),
        result,
        [profile_path, *design_paths, *run_paths, *safety_paths],
        protected_roots(base, record["protected_roots"], "/protected_roots"),
    )
