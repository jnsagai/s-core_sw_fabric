"""Runtime command operations with stable 0/1/2 outcomes and no implicit authority."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.assurance.package import verify_assessment
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.client import (
    FabroClient,
    validate_runtime_profile,
    verify_candidate_files,
)
from score_sw_fabric.runtime.export import build_export
from score_sw_fabric.runtime.inspect import bind_pending_questions, inspect_run
from score_sw_fabric.runtime.ledger import IntentLedger
from score_sw_fabric.runtime.projection import project_version
from score_sw_fabric.runtime.request import RuntimeRequest, parse_json
from score_sw_fabric.runtime.resume import admit_resume

Outcome = tuple[int, dict[str, Any]]


def selected_client(request: RuntimeRequest) -> FabroClient:
    """Check the reviewed candidate profile and local bytes before any native request."""
    profile = validate_runtime_profile(
        request.runtime_profile, expected_commit=request.runtime_commit
    )
    verify_candidate_files(profile, executable=request.executable, source_api=request.source_api)
    return FabroClient(
        profile, expected_commit=request.runtime_commit, credential_provider=request.credential
    )


def _ledger(request: RuntimeRequest) -> IntentLedger:
    return IntentLedger(request.ledger_root)


def _known(request: RuntimeRequest) -> dict[str, Any]:
    binding = _ledger(request).read(request.intent["intent_id"])
    if binding["creation_state"] != "run_known" or binding["run_id"] is None:
        raise InputError("RUN_ID_UNKNOWN", "The intent has no safely known native run")
    return binding


def register(request: RuntimeRequest, client: FabroClient | None = None) -> Outcome:
    client = client or selected_client(request)
    projection = project_version(request.package, request.compiler_profile)
    version_id = client.register_package(request.package, request.compiler_profile)
    binding = _ledger(request).prepare(
        request.intent,
        version_id=version_id,
        runtime_commit=request.runtime_commit,
        source_package_digest=request.package["digest"],
        wire_digest=projection["wire_digest"],
    )
    return 0, binding


def run(request: RuntimeRequest, client: FabroClient | None = None) -> Outcome:
    """Register, create once and start once; uncertainty is published and stops."""
    client = client or selected_client(request)
    _, binding = register(request, client)
    ledger = _ledger(request)
    identifier = binding["intent_id"]
    if binding["creation_state"] == "create_in_flight":
        return 1, ledger.mark_create_uncertain(identifier)
    if binding["creation_state"] == "reconciliation_required":
        return 1, binding
    if binding["creation_state"] == "prepared":
        try:
            binding = client.create_run(
                ledger,
                identifier,
                target=request.target,
                disposable_root=request.disposable_root,
                environment_id=request.environment_id,
                labels=request.intent["start_args"]["labels"],
            )
        except InputError:
            current = ledger.read(identifier)
            if current["creation_state"] == "reconciliation_required":
                return 1, current
            raise
    if binding["start_state"] == "start_in_flight":
        return 1, ledger.mark_start_uncertain(identifier)
    if binding["start_state"] == "reconciliation_required":
        return 1, binding
    try:
        binding = client.start_known_run(ledger, identifier)
    except InputError:
        current = ledger.read(identifier)
        if current["start_state"] == "reconciliation_required":
            return 1, current
        raise
    return 0, binding


def status(request: RuntimeRequest, client: FabroClient | None = None) -> Outcome:
    client = client or selected_client(request)
    binding = _known(request)
    inspection = inspect_run(
        client, binding["run_id"], max_pages=request.intent["limits"]["event_pages"]
    )
    reasons = set(inspection["reason_codes"])
    handoff: list[dict[str, Any]] | None = None
    if inspection["questions"]:
        if request.subject is None:
            reasons.add("QUESTION_SUBJECT_UNKNOWN")
        else:
            try:
                handoff = bind_pending_questions(
                    inspection,
                    request.package,
                    request.compiler_profile,
                    request.subject,
                    expected_subject_digest=request.intent["baseline"]["subject_digest"],
                )
            except InputError as exc:
                reasons.add(str(exc.code))
    waiting = inspection["native_blocked_reason"] == "human_input_required" and bool(handoff)
    if waiting:
        reasons.add("HUMAN_GATE_WAITING")
    lifecycle = inspection["native_summary"].get("lifecycle")
    checkpoints = inspection["checkpoints"]
    snapshot = seal(
        {
            "schema_version": 1,
            "kind": "runtime_snapshot",
            "intent_id": binding["intent_id"],
            "run_id": binding["run_id"],
            "version_id": binding["version_id"],
            "native_status": inspection["native_status"],
            "native_reason": inspection["native_reason"],
            "native_blocked_reason": inspection["native_blocked_reason"],
            "pending_control": lifecycle.get("pending_control")
            if isinstance(lifecycle, dict)
            else None,
            "event_position": inspection["event_position"],
            "event_contract_version": inspection["event_contract_version"],
            "checkpoint_count": len(checkpoints),
            "last_checkpoint": checkpoints[-1] if checkpoints else None,
            "stages": inspection["stages"],
            "questions": inspection["questions"],
            "gate_handoff": handoff,
            "complete": inspection["complete"],
            "reason_codes": sorted(reasons),
            "next_action": "external_authorized_human_decision_required" if waiting else "none",
            "assurance_decisions": 0,
            "engineering_readiness": "not_evaluated",
        }
    )
    faithful = inspection["complete"] and not (reasons - {"HUMAN_GATE_WAITING"})
    return (0 if faithful else 1), snapshot


def _replays(request: RuntimeRequest) -> list[dict[str, Any]]:
    replays = []
    for _, assessment_bytes, _, context_bytes in request.evidence:
        assessment = parse_json(assessment_bytes, "/evidence/assessment")
        if not isinstance(assessment, dict) or not isinstance(assessment.get("digest"), str):
            raise InputError("FIELD_TYPE", "Selected 005 assessment is not a sealed record")
        try:
            result = verify_assessment(assessment, parse_json(context_bytes, "/evidence/context"))
        except InputError:
            result = {"reproduced": False, "outcome": None, "assurance_domain": None}
        replays.append(
            {
                "assessment_digest": assessment["digest"],
                "reproduced": result.get("reproduced") is True,
                "outcome": result.get("outcome"),
                "assurance_domain": result.get("assurance_domain"),
            }
        )
    return replays


def resume(request: RuntimeRequest, client: FabroClient | None = None) -> Outcome:
    """Admit same-run continuation only after exact baseline and effect checks."""
    if request.baseline_now is None:
        raise InputError("RESUME_BASELINE_STALE", "Resume requires the current baseline vector")
    client = client or selected_client(request)
    binding = _known(request)
    inspection = inspect_run(
        client, binding["run_id"], max_pages=request.intent["limits"]["event_pages"]
    )
    decision = admit_resume(
        binding=binding,
        intent=request.intent,
        baseline_now=request.baseline_now,
        inspection=inspection,
        evidence=_replays(request),
        effects=request.effects,
    )
    if decision["decision"] != "admit":
        return 1, decision
    if "run_resume" not in client.profile["demonstrated_capabilities"]:
        return 1, seal(
            {
                **decision,
                "decision": "block_unknown",
                "reason_codes": sorted(
                    set(decision["reason_codes"]) | {"RUNTIME_CAPABILITY_UNAVAILABLE"}
                ),
            }
        )
    ledger = _ledger(request)
    ledger.begin_resume(binding["intent_id"], attempt_limit=decision["attempt_limit"])
    try:
        client.resume_run(decision)
    except InputError:
        ledger.mark_resume_uncertain(binding["intent_id"])
        return 1, seal(
            {
                **decision,
                "decision": "reconciliation_required",
                "native_action": "uncertain",
                "reason_codes": sorted(set(decision["reason_codes"]) | {"RESUME_UNCERTAIN"}),
            }
        )
    return 0, seal({**decision, "native_action": "accepted"})


def cancel(request: RuntimeRequest, client: FabroClient | None = None) -> Outcome:
    client = client or selected_client(request)
    binding = _known(request)
    polls = min(request.intent["limits"]["timeout_seconds"] * 5, 1000)
    result = client.cancel_run(binding["run_id"], polls=polls)
    record = seal(
        {
            "schema_version": 1,
            "kind": "runtime_cancellation",
            "intent_id": binding["intent_id"],
            "version_id": binding["version_id"],
            **result,
        }
    )
    return (0 if result["cancellation"] == "confirmed" else 1), record


def export(request: RuntimeRequest, client: FabroClient | None = None) -> Outcome:
    client = client or selected_client(request)
    binding = _known(request)
    references = [
        {
            "assessment_digest": item["assessment_digest"],
            "assurance_domain": item["assurance_domain"],
            "outcome": item["outcome"],
            "origin": "authenticated_005_reference"
            if item["reproduced"]
            else "runtime_observation",
        }
        for item in _replays(request)
    ]
    record = build_export(
        client,
        binding,
        package_bytes=request.package_bytes,
        compiler_profile_bytes=request.compiler_profile_bytes,
        assurance_references=references,
        output_limit=request.intent["limits"]["output_bytes"],
        max_pages=request.intent["limits"]["event_pages"],
    )
    return (0 if record["completeness"] == "complete" else 1), record
