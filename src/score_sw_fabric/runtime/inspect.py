"""Faithful bounded observation of one Fabro run and its ordered event stream."""

from __future__ import annotations

import json
import re
from typing import Any

from score_sw_fabric.assurance.models import sha, verify_digest
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.package import validate_package
from score_sw_fabric.compiler.render import render_native
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.client import FabroClient
from score_sw_fabric.runtime.projection import project_version

KNOWN_STATUSES = {
    "submitted",
    "pending",
    "runnable",
    "starting",
    "running",
    "blocked",
    "paused",
    "removing",
    "succeeded",
    "failed",
    "dead",
}
MAX_EVENTS = 100_000
MAX_TIMELINE = 10_000
MAX_QUESTIONS = 1_000


def _object(client: FabroClient, operation: str, path: str) -> dict[str, Any]:
    status, body = client.request(operation, "GET", path)
    if status != 200:
        raise InputError("RUNTIME_RESPONSE", f"Fabro returned HTTP {status}")
    try:
        value = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise InputError("RUNTIME_RESPONSE", "Fabro returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise InputError("RUNTIME_RESPONSE", "Fabro returned a non-object")
    return value


def inspect_run(client: FabroClient, run_id: str, *, max_pages: int = 100) -> dict[str, Any]:
    """Return native evidence with explicit completeness and no readiness inference."""
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id) is None:
        raise InputError("RUN_ID_UNKNOWN", "Invalid native run ID")
    if type(max_pages) is not int or max_pages < 1 or max_pages > 10_000:
        raise InputError("LIMIT_EXCEEDED", "Event page limit is invalid")
    root = f"/api/v1/runs/{run_id}"
    summary = _object(client, "run_inspect", root)
    if summary.get("id") != run_id:
        raise InputError("RUNTIME_RESPONSE", "Fabro returned another run")
    lifecycle = summary.get("lifecycle")
    status_record = lifecycle.get("status") if isinstance(lifecycle, dict) else None
    native_kind = status_record.get("kind") if isinstance(status_record, dict) else None
    reasons: set[str] = set()
    if native_kind not in KNOWN_STATUSES:
        reasons.add("NATIVE_STATE_UNKNOWN")
    events: list[dict[str, Any]] = []
    by_seq: dict[int, bytes] = {}
    by_id: dict[str, int] = {}
    cursor = 0
    contract_version: int | None = None
    complete = False
    for _ in range(max_pages):
        page = _object(client, "event_read", root + f"/events?after={cursor}&limit=1000")
        page_items = page.get("data")
        meta = page.get("meta")
        observed_version = page.get("event_contract_version")
        if (
            not isinstance(page_items, list)
            or not isinstance(meta, dict)
            or type(meta.get("has_more")) is not bool
            or type(observed_version) is not int
        ):
            reasons.add("EVENT_GAP")
            break
        if contract_version is None:
            contract_version = observed_version
        elif observed_version != contract_version:
            reasons.add("EVENT_GAP")
            break
        advanced = False
        for item in page_items:
            if not isinstance(item, dict):
                reasons.add("EVENT_GAP")
                break
            seq = item.get("stream_seq")
            identifier = item.get("id")
            if type(seq) is not int or seq < 1 or not isinstance(identifier, str):
                reasons.add("EVENT_GAP")
                break
            encoded = canonical(item)
            if seq <= cursor:
                if by_seq.get(seq) != encoded:
                    reasons.add("EVENT_GAP")
                    break
                continue
            if seq != cursor + 1 or len(events) >= MAX_EVENTS:
                reasons.add("EVENT_GAP")
                break
            if identifier in by_id:
                reasons.add("EVENT_GAP")
                break
            by_seq[seq] = encoded
            by_id[identifier] = seq
            events.append(item)
            cursor = seq
            advanced = True
        if "EVENT_GAP" in reasons:
            break
        if not meta["has_more"]:
            complete = True
            break
        if not advanced:
            reasons.add("EVENT_GAP")
            break
    if not complete:
        reasons.add("EVENT_GAP")
    timeline = _object(client, "timeline_read", root + "/timeline")
    checkpoints = timeline.get("entries")
    if not isinstance(checkpoints, list) or len(checkpoints) > MAX_TIMELINE:
        checkpoints = []
        reasons.add("CHECKPOINT_INCOMPLETE")
    question_page = _object(client, "question_read", root + "/questions")
    questions = question_page.get("data")
    question_meta = question_page.get("meta")
    if (
        not isinstance(questions, list)
        or len(questions) > MAX_QUESTIONS
        or not isinstance(question_meta, dict)
        or type(question_meta.get("has_more")) is not bool
        or question_meta["has_more"]
    ):
        questions = []
        reasons.add("QUESTION_INCOMPLETE")
    return {
        "run_id": run_id,
        "native_status": native_kind if native_kind in KNOWN_STATUSES else "unknown",
        "native_reason": status_record.get("reason") if isinstance(status_record, dict) else None,
        "native_blocked_reason": status_record.get("blocked_reason")
        if isinstance(status_record, dict)
        else None,
        "native_summary": summary,
        "event_contract_version": contract_version,
        "event_position": cursor,
        "events": events,
        "checkpoints": checkpoints,
        "questions": questions,
        "complete": complete and not reasons,
        "reason_codes": sorted(reasons),
        "engineering_readiness": "not_evaluated",
    }


def bind_pending_questions(
    inspection: dict[str, Any],
    package: dict[str, Any],
    compiler_profile: dict[str, Any],
    subject: dict[str, Any],
    *,
    expected_subject_digest: str,
) -> list[dict[str, Any]]:
    """Map each native question to one sealed 003 gate and exact 005 subject identity."""
    validate_package(package, compiler_profile)
    projection = project_version(package, compiler_profile)
    generated = render_native(package["manifest"]["ir"], [])
    if any(
        package["files"].get(name) != generated[name]
        for name in ("workflow.fabro", "workflow.toml")
    ):
        raise InputError("QUESTION_SUBJECT_UNKNOWN", "Required gate graph is not compiler rendered")
    verify_digest(subject, "/subject")
    sha(expected_subject_digest, "/expected_subject_digest")
    candidate = subject.get("artifact_candidate")
    bindings = candidate.get("bindings") if isinstance(candidate, dict) else None
    if (
        subject.get("kind") != "assurance_subject"
        or subject.get("schema_version") != 1
        or subject["digest"] != expected_subject_digest
        or not isinstance(bindings, dict)
        or bindings.get("workflow_package") != package["digest"]
    ):
        raise InputError("QUESTION_SUBJECT_UNKNOWN", "005 subject does not bind this package")
    expected_ids = subject.get("expected_obligation_ids")
    if not isinstance(expected_ids, list) or any(not isinstance(x, str) for x in expected_ids):
        raise InputError("QUESTION_SUBJECT_UNKNOWN", "005 subject obligations are unavailable")
    questions = inspection.get("questions")
    if not isinstance(questions, list):
        raise InputError("QUESTION_SUBJECT_UNKNOWN", "Native questions are unavailable")
    if not questions:
        return []
    if (
        inspection.get("native_status") != "blocked"
        or inspection.get("native_blocked_reason") != "human_input_required"
        or inspection.get("complete") is not True
    ):
        raise InputError("QUESTION_SUBJECT_UNKNOWN", "Native human waiting is not complete")
    created = []
    for item in inspection.get("events", []):
        if not isinstance(item, dict) or item.get("kind") != "platform":
            continue
        envelope = item.get("item")
        record = envelope.get("record") if isinstance(envelope, dict) else None
        if isinstance(record, dict) and record.get("kind") == "run.created":
            created.append(record)
    if len(created) != 1:
        raise InputError("QUESTION_SUBJECT_UNKNOWN", "Native run creation is not unique")
    spec = created[0].get("spec")
    settings = spec.get("settings") if isinstance(spec, dict) else None
    run_settings = settings.get("run") if isinstance(settings, dict) else None
    execution = run_settings.get("execution") if isinstance(run_settings, dict) else None
    if (
        not isinstance(spec, dict)
        or spec.get("workflow_version_id") != projection["wire_digest"]
        or not isinstance(execution, dict)
        or execution.get("approval") != "prompt"
    ):
        raise InputError("QUESTION_SUBJECT_UNKNOWN", "Native run may bypass required human input")
    answered = {
        record.get("question")
        for item in inspection["events"]
        if isinstance(item, dict)
        and item.get("kind") == "platform"
        and isinstance(item.get("item"), dict)
        and isinstance(record := item["item"].get("record"), dict)
        and record.get("kind") == "interview.answered"
    }
    gates = package["manifest"]["ir"]["gates"]
    source_entries = [item for item in package["source_map"] if item["kind"] == "gate"]
    mapped: list[dict[str, Any]] = []
    used_stages: set[str] = set()
    for question in questions:
        if not isinstance(question, dict):
            raise InputError("QUESTION_SUBJECT_UNKNOWN", "Native question is malformed")
        question_id = question.get("id")
        stage = question.get("stage")
        if (
            not isinstance(question_id, str)
            or len(question_id) > 256
            or not isinstance(stage, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,120}@[1-9][0-9]{0,6}", stage) is None
            or stage in used_stages
            or question_id in answered
            or any(
                name in question for name in ("default_choice", "timeout_default", "auto_approve")
            )
        ):
            raise InputError("QUESTION_SUBJECT_UNKNOWN", "Native question identity is ambiguous")
        used_stages.add(stage)
        node_id = stage.rsplit("@", 1)[0]
        gate_matches = [item for item in gates if item["node_id"] == node_id]
        source_matches = [item for item in source_entries if item["id"] == node_id]
        if len(gate_matches) != 1 or len(source_matches) != 1:
            raise InputError("QUESTION_SUBJECT_UNKNOWN", "Question has no unique 003 gate")
        gate = gate_matches[0]
        source = source_matches[0]
        covered_ids = gate["subjects"]
        if (
            not isinstance(covered_ids, list)
            or not covered_ids
            or not set(covered_ids) <= set(expected_ids)
            or source["plan_instance_ids"] != sorted(covered_ids)
            or gate["authority_requirement"] != "authenticated_external_human"
        ):
            raise InputError("QUESTION_SUBJECT_UNKNOWN", "Gate and 005 subject differ")
        mapped.append(
            {
                "question_id": question_id,
                "stage": stage,
                "gate_id": node_id,
                "gate_purpose": gate["purpose"],
                "covered_obligation_ids": sorted(covered_ids),
                "subject_digest": subject["digest"],
                "assurance_domain": subject.get("assurance_domain"),
                "source_map_binding": source["content_binding"],
                "next_action": "external_authorized_human_decision_required",
                "engineering_readiness": "not_evaluated",
            }
        )
    return sorted(mapped, key=lambda item: item["question_id"])
