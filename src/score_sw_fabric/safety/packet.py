"""Safety review packet: what reviewers see and exactly what each gate would authorize."""

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
from score_sw_fabric.assurance.models import (
    ORIGINS,
    exact,
    nonempty,
    seal,
    stable_id,
    verify_digest,
)
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.safety.profile import load_profile

PACKET_FIELDS = {"profile", "report", "evidence", "protected_roots"}
DIFF_FIELDS = (
    "catalogue_id",
    "violates",
    "mitigated_by",
    "mitigation_issue",
    "failure_effect",
    "content_sha256",
    "sufficient",
    "status",
    "mitigation_state",
)


def _diff(report: dict[str, Any]) -> dict[str, Any]:
    current = {item["id"]: item for item in report["items"]}
    if report["baseline_files"] is None:
        return {"baseline": None, "added": sorted(current), "removed": [], "changed": []}
    prior = {item["id"]: item for item in report["baseline_items"]}
    changed = []
    for identifier in sorted(current.keys() & prior.keys()):
        fields = {
            name: {"from": prior[identifier][name], "to": current[identifier][name]}
            for name in DIFF_FIELDS
            if prior[identifier][name] != current[identifier][name]
        }
        if fields:
            changed.append({"item": identifier, "fields": fields})
    return {
        "baseline": report["baseline_files"],
        "added": sorted(current.keys() - prior.keys()),
        "removed": sorted(prior.keys() - current.keys()),
        "changed": changed,
    }


def _evidence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 1000:
        raise InputError("LIMIT_EXCEEDED", "Too many evidence references", "/evidence")
    result = []
    for index, raw in enumerate(value):
        pointer = f"/evidence/{index}"
        item = exact(raw, {"id", "kind", "ref", "origin", "requirement"}, pointer)
        stable_id(item["id"], pointer + "/id")
        nonempty(item["kind"], pointer + "/kind", max_length=64)
        nonempty(item["ref"], pointer + "/ref", max_length=1024)
        stable_id(item["requirement"], pointer + "/requirement")
        if item["origin"] not in ORIGINS:
            raise InputError("FIELD_ENUM", "Unknown evidence origin", pointer + "/origin")
        result.append({**item, "verification": "not_verified"})
    return result


def build_packet(
    profile: dict[str, Any], report: dict[str, Any], evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    items = report["items"]
    mitigations = sorted({target for item in items for target in item["mitigated_by"]})
    missing = []
    for requirement in mitigations:
        supplied = [item["id"] for item in evidence if item["requirement"] == requirement]
        missing.append(
            {
                "requirement": requirement,
                "needed": "implementation_and_verification_evidence",
                "supplied_refs": supplied,
                "state": "supplied_unverified" if supplied else "missing",
            }
        )
    reanalysis = report["reanalysis"]
    architecture = sorted(
        {target for item in items for target in item["violates"]}
        | {
            key
            for key in reanalysis["changed"] + reanalysis["new"] + reanalysis["removed"]
            if "arc" in key
        }
    )
    requirements = sorted(
        set(mitigations)
        | {
            key
            for key in reanalysis["changed"] + reanalysis["new"] + reanalysis["removed"]
            if "req" in key
        }
    )
    uncertainties = [
        {"subject": item["subject"], "code": item["code"], "detail": item["detail"]}
        for item in report["findings"]
    ]
    uncertainties += [
        {
            "subject": item["id"],
            "code": "SUFFICIENCY_UNREVIEWED",
            "detail": f"mitigation state {item['mitigation_state']}",
        }
        for item in items
        if item["mitigation_state"] != "claimed_sufficient"
    ]
    concerns = (
        [
            {
                "item": item["id"],
                "failure_id": item["catalogue_id"],
                "failure_effect": item["failure_effect"],
                "violates": item["violates"],
                "mitigation_issue": item["mitigation_issue"],
                "mitigation_state": item["mitigation_state"],
                "disposition": "pending_review",
            }
            for item in items
        ]
        if report["analysis"] == "dfa"
        else []
    )
    coverage_complete = all(
        row["state"] in {"analysed", "excluded", "allocated"} for row in report["coverage"]
    )
    aous = sorted({target for target in mitigations if target.startswith("aou_req")})
    support = {
        "Gen 1": "Structural coverage of the pinned catalogue is "
        + ("complete." if coverage_complete else "incomplete."),
        "Gen 2": "Every item states a failure effect and argument."
        if not any(
            item["code"] in {"MANDATORY_OPTION", "CONTENT_MISSING"} for item in report["findings"]
        )
        else "Some items lack a failure effect or argument.",
        "Gen 4": "No mitigation implementation or verification evidence has been verified.",
        "Gen 5": f"AoUs used as mitigation: {', '.join(aous) or 'none'}; "
        "safety-manual coverage is not checked.",
    }
    checklist = [
        {
            "id": item["id"],
            "question": item["question"],
            "answer": "pending_human",
            "support": support.get(item["id"]),
        }
        for item in profile["checklist"]
    ]
    subject_files = [
        {"path": item["path"], "sha256": item["sha256"], "role": item["role"]}
        for item in report["current_files"]
    ]
    subject_items = [{"id": item["id"], "digest": item["digest"]} for item in items]
    ready = report["design_prerequisites"]["state"] == "ready_for_design_review"
    pending_evidence = [item["requirement"] for item in missing]
    return {
        "schema_version": 1,
        "kind": "safety_review_packet",
        "report_digest": report["digest"],
        "profile": report["profile"],
        "component": report["component"],
        "analysis": report["analysis"],
        "iteration": report["iteration"],
        "design_prerequisites": report["design_prerequisites"],
        "native_diff": _diff(report),
        "coverage": report["coverage"],
        "items": items,
        "affected": {"requirements": requirements, "architecture": architecture},
        "mitigation_changes": [
            {
                "item": item["id"],
                "mitigated_by": item["mitigated_by"],
                "mitigation_issue": item["mitigation_issue"],
                "mitigation_state": item["mitigation_state"],
            }
            for item in items
        ],
        "feedback": report["feedback"],
        "dependency_concerns": concerns,
        "verification_evidence": evidence,
        "missing_evidence": missing,
        "uncertainties": uncertainties,
        "checklist": checklist,
        "approval_scopes": {
            "design_acceptance": {
                "gate_id": profile["gates"]["design"],
                "requestable": ready,
                "subject_files": subject_files,
                "subject_items": subject_items,
                "authorizes": "Detailed design and implementation of the linked mitigations "
                "as analysed in the subject items.",
                "does_not_authorize": [
                    "final safety closure",
                    "setting sufficient: yes or status: valid",
                    "release or deployment",
                ],
                "pending": report["design_prerequisites"]["reasons"],
            },
            "closure": {
                "gate_id": profile["gates"]["closure"],
                "requestable": False,
                "subject_files": subject_files,
                "subject_items": subject_items,
                "authorizes": "Closure of the implemented mitigations for the subject items.",
                "requires": [
                    "an accepted design decision for the unchanged requirements and architecture",
                    "verified implementation and verification evidence for every "
                    "mitigating requirement",
                    "subject items at sufficient: yes and status: valid in the reviewed bytes",
                ],
                "does_not_authorize": ["release or deployment"],
                "pending": pending_evidence,
            },
        },
        "packet_state": "review_requestable" if ready else "blocked_prerequisites",
        "engineering_readiness": READINESS,
        "limitations": [
            "Checklist answers are left to the named human reviewer; support notes are structural.",
            "Supplied evidence references are listed but not verified by this packet.",
            "Fixture native files are synthetic and carry no review.",
        ],
    }


def packet(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    record, base = load_request(request_path, "safety_packet_request", PACKET_FIELDS)
    profile_path, profile_bytes = input_file(base, record["profile"], "/profile")
    profile = load_profile(profile_bytes)
    report_path, _, report = json_file(base, record["report"], "/report")
    verify_digest(report, "/report")
    if (
        report.get("kind") != "safety_analysis_report"
        or report["profile"]["sha256"] != hashlib.sha256(profile_bytes).hexdigest()
    ):
        raise InputError("REPORT_MISMATCH", "Report does not bind this profile", "/report")
    output = seal(build_packet(profile, report, _evidence(record["evidence"])))
    status = 0 if output["packet_state"] == "review_requestable" else 1
    return (
        status,
        output,
        [profile_path, report_path],
        protected_roots(base, record["protected_roots"], "/protected_roots"),
    )
