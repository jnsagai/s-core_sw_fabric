"""Separate safety design-acceptance and closure gates bound to verified 005 decisions."""

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
from score_sw_fabric.assurance.models import exact, seal, verify_digest
from score_sw_fabric.assurance.package import verify_assessment
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.safety.profile import load_profile

GATE_FIELDS = {"profile", "packet", "decisions", "protected_roots"}
MAX_DECISIONS = 20


def summarize(
    assessment: dict[str, Any], trust_context: dict[str, Any], packet: dict[str, Any]
) -> dict[str, Any]:
    """Replay one 005 assessment and describe how it binds the packet's exact files."""
    replay = verify_assessment(assessment, trust_context)
    result = assessment["gate_results"][0]
    subject = assessment.get("subject", {})
    manifest = subject.get("manifest", {}) if isinstance(subject, dict) else {}
    closure = {
        (str(item.get("path")), str(item.get("sha256")))
        for item in manifest.get("file_closure", [])
        if isinstance(item, dict)
    }
    files = packet["approval_scopes"]["design_acceptance"]["subject_files"]
    basis = [item for item in files if item["role"] != "analysis"]
    return {
        "assessment_digest": assessment["digest"],
        "gate_id": result.get("gate_id"),
        "assurance_domain": result.get("assurance_domain"),
        "outcome": result.get("outcome"),
        "reproduced": replay.get("reproduced") is True,
        "binding": "exact"
        if all((item["path"], item["sha256"]) in closure for item in files)
        else "other_subject",
        "design_basis_binding": "exact"
        if basis and all((item["path"], item["sha256"]) in closure for item in basis)
        else "other_subject",
    }


def evaluate(
    profile: dict[str, Any], packet: dict[str, Any], decisions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Pure gate evaluation over verified-decision summaries produced by `summarize`."""
    gates = profile["gates"]
    notes: list[str] = []
    usable = []
    for decision in decisions:
        if not decision["reproduced"]:
            notes.append("DECISION_NOT_REPRODUCED")
        elif decision["assurance_domain"] == "production":
            notes.append("PRODUCTION_AUTHORITY_UNAVAILABLE")
        elif decision["outcome"] != "pass":
            notes.append("DECISION_NOT_PASS")
        else:
            usable.append(decision)

    def state(gate_id: str, key: str, prerequisites: list[str]) -> dict[str, Any]:
        matching = [item for item in usable if item["gate_id"] == gate_id]
        exact_match = [item for item in matching if item[key] == "exact"]
        if prerequisites:
            return {"state": "blocked", "reasons": prerequisites, "decision": None, "domain": None}
        if exact_match:
            chosen = exact_match[0]
            return {
                "state": "accepted",
                "reasons": [],
                "decision": chosen["assessment_digest"],
                "domain": chosen["assurance_domain"],
            }
        if matching:
            return {
                "state": "stale",
                "reasons": ["DECISION_SUBJECT_MISMATCH"],
                "decision": None,
                "domain": None,
            }
        return {
            "state": "awaiting_decision",
            "reasons": ["DECISION_MISSING"],
            "decision": None,
            "domain": None,
        }

    design_blockers = (
        []
        if packet["design_prerequisites"]["state"] == "ready_for_design_review"
        else ["DESIGN_PREREQUISITES_BLOCKED", *packet["design_prerequisites"]["reasons"]]
    )
    design = state(gates["design"], "binding", design_blockers)
    basis = state(gates["design"], "design_basis_binding", [])
    closure_blockers = []
    if basis["state"] != "accepted":
        closure_blockers.append("DESIGN_NOT_ACCEPTED")
    if any(item["mitigation_state"] != "claimed_sufficient" for item in packet["items"]):
        closure_blockers.append("ITEMS_NOT_CLAIMED_SUFFICIENT")
    closure = state(gates["closure"], "binding", [])
    if closure["state"] != "accepted":
        closure_blockers.append("MITIGATION_EVIDENCE_MISSING")
    if closure_blockers:
        closure = {
            "state": "blocked",
            "reasons": sorted(set(closure_blockers)),
            "decision": None,
            "domain": None,
            "missing_evidence": [item["requirement"] for item in packet["missing_evidence"]],
        }
    return {
        "design_acceptance": design,
        "closure": closure,
        "decision_notes": sorted(set(notes)),
    }


def gate(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    record, base = load_request(request_path, "safety_gate_request", GATE_FIELDS)
    profile_path, profile_bytes = input_file(base, record["profile"], "/profile")
    profile = load_profile(profile_bytes)
    packet_path, _, packet = json_file(base, record["packet"], "/packet")
    verify_digest(packet, "/packet")
    if (
        packet.get("kind") != "safety_review_packet"
        or packet["profile"]["sha256"] != hashlib.sha256(profile_bytes).hexdigest()
    ):
        raise InputError("PACKET_MISMATCH", "Packet does not bind this profile", "/packet")
    raw = record["decisions"]
    if not isinstance(raw, list) or len(raw) > MAX_DECISIONS:
        raise InputError("LIMIT_EXCEEDED", "Too many decisions", "/decisions")
    summaries = []
    inputs = [profile_path, packet_path]
    for index, item in enumerate(raw):
        pointer = f"/decisions/{index}"
        entry = exact(item, {"assessment", "trust_context"}, pointer)
        assessment_path, _, assessment = json_file(
            base, entry["assessment"], pointer + "/assessment"
        )
        context_path, _, context = json_file(
            base, entry["trust_context"], pointer + "/trust_context"
        )
        inputs += [assessment_path, context_path]
        summaries.append(summarize(assessment, context, packet))
    evaluation = evaluate(profile, packet, summaries)
    output = seal(
        {
            "schema_version": 1,
            "kind": "safety_gate_evaluation",
            "packet_digest": packet["digest"],
            "profile": packet["profile"],
            "component": packet["component"],
            "analysis": packet["analysis"],
            "decisions": summaries,
            **evaluation,
            "engineering_readiness": READINESS,
            "limitations": [
                "Decisions count only from reproduced 005 assessments bound to the exact files.",
                "Production decisions are ineligible while 005 T009 is open.",
                "Fixture-domain acceptance is a contract demonstration, never safety acceptance.",
            ],
        }
    )
    status = 0 if evaluation["design_acceptance"]["state"] == "accepted" else 1
    return (
        status,
        output,
        inputs,
        protected_roots(base, record["protected_roots"], "/protected_roots"),
    )
