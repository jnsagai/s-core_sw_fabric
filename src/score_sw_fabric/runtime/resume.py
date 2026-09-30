"""Same-run resume admission from exact baselines, native checkpoints and effect state."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.assurance.models import digest, exact, seal, sha, stable_id, verify_digest
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.models import validate_baseline, validate_binding, validate_intent

ACTIVE_STATUSES = {
    "submitted",
    "pending",
    "runnable",
    "starting",
    "running",
    "blocked",
    "paused",
    "removing",
}
# Native interruption reasons; every other terminal reason stays terminal for the fabric.
RESUMABLE_FAILURES = {"terminated", "transient_infra"}
SETTLED_STAGE_STATUSES = {"succeeded", "failed", "cancelled", "skipped"}
EFFECT_STATES = {"confirmed_absent", "confirmed_once", "unknown"}
DECISIONS = ("refuse_terminal", "block_unknown", "block_drift", "reconciliation_required")
DECISION_FIELDS = {
    "intent_id",
    "run_id",
    "registered_version_id",
    "native_status",
    "checkpoint",
    "baseline_before_digest",
    "baseline_now_digest",
    "changed_bindings",
    "in_flight_stages",
    "effects",
    "evidence",
    "attempts",
    "attempt_limit",
    "decision",
    "native_action",
    "reason_codes",
    "production_authority",
    "engineering_readiness",
    "digest",
}


def _validate_effects(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 10_000:
        raise InputError("LIMIT_EXCEEDED", "Effect records exceed limit", "/effects")
    seen: set[str] = set()
    for index, raw in enumerate(value):
        pointer = f"/effects/{index}"
        record = exact(raw, {"stage", "effect_id", "state"}, pointer)
        stage = record["stage"]
        if not isinstance(stage, str) or len(stage) > 128 or "@" not in stage:
            raise InputError("FIELD_TYPE", "Effect stage must be a native stage ID", pointer)
        stable_id(record["effect_id"], pointer + "/effect_id")
        if record["effect_id"] in seen:
            raise InputError("DUPLICATE_ID", "Duplicate effect ID", pointer)
        seen.add(record["effect_id"])
        if record["state"] not in EFFECT_STATES:
            raise InputError("FIELD_UNKNOWN", "Unknown effect state", pointer)
    return sorted(value, key=lambda item: item["effect_id"])


def _validate_evidence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 10_000:
        raise InputError("LIMIT_EXCEEDED", "Evidence replays exceed limit", "/evidence")
    for index, raw in enumerate(value):
        pointer = f"/evidence/{index}"
        record = exact(
            raw, {"assessment_digest", "reproduced", "outcome", "assurance_domain"}, pointer
        )
        sha(record["assessment_digest"], pointer + "/assessment_digest")
        if type(record["reproduced"]) is not bool:
            raise InputError("FIELD_TYPE", "Evidence replay flag must be boolean", pointer)
    return sorted(value, key=lambda item: item["assessment_digest"])


def _created_version(inspection: dict[str, Any]) -> Any:
    created = [
        item["item"]["record"]
        for item in inspection.get("events", [])
        if isinstance(item, dict)
        and item.get("kind") == "platform"
        and isinstance(item.get("item"), dict)
        and isinstance(item["item"].get("record"), dict)
        and item["item"]["record"].get("kind") == "run.created"
    ]
    if len(created) != 1 or not isinstance(created[0].get("spec"), dict):
        return None
    return created[0]["spec"].get("workflow_version_id")


def admit_resume(
    *,
    binding: dict[str, Any],
    intent: dict[str, Any],
    baseline_now: dict[str, Any],
    inspection: dict[str, Any],
    evidence: list[dict[str, Any]],
    effects: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a sealed admission; only `admit` may reach the native resume route."""
    binding = validate_binding(binding)
    intent = validate_intent(intent)
    current = validate_baseline(baseline_now, "/baseline_now")
    selected_effects = _validate_effects(effects)
    replays = _validate_evidence(evidence)
    before = intent["baseline"]
    reasons: set[str] = set()
    decisions: set[str] = set()
    changed: set[str] = set()

    def block(decision: str, code: str) -> None:
        decisions.add(decision)
        reasons.add(code)

    run_id = binding["run_id"]
    if binding["creation_state"] != "run_known" or run_id != inspection.get("run_id"):
        block("block_unknown", "RUN_ID_UNKNOWN")
    if binding["intent_digest"] != intent["digest"]:
        changed.add("intent")
    if binding["baseline_digest"] != digest(before, exclude="__none__"):
        changed.add("baseline")
    if inspection.get("complete") is not True:
        block("block_unknown", "NATIVE_STATE_UNKNOWN")
        reasons.update(code for code in inspection.get("reason_codes", []) if isinstance(code, str))
    status = inspection.get("native_status")
    native_reason = inspection.get("native_reason")
    if status == "succeeded" or status == "dead":
        block("refuse_terminal", "RESUME_SOURCE_TERMINAL")
    elif status == "failed" and native_reason == "cancelled":
        block("refuse_terminal", "CANCELLED_TERMINAL")
    elif status == "failed" and native_reason not in RESUMABLE_FAILURES:
        block("refuse_terminal", "RESUME_SOURCE_TERMINAL")
    elif status in ACTIVE_STATUSES:
        block("block_unknown", "RESUME_SOURCE_ACTIVE")
    elif status != "failed":
        block("block_unknown", "NATIVE_STATE_UNKNOWN")
    registered = _created_version(inspection)
    if registered is None:
        block("block_unknown", "NATIVE_STATE_UNKNOWN")
    elif registered != binding["version_id"] or registered != binding["wire_digest"]:
        changed.add("workflow_version")
    checkpoints = inspection.get("checkpoints")
    checkpoint = checkpoints[-1] if isinstance(checkpoints, list) and checkpoints else None
    if not isinstance(checkpoint, dict):
        block("block_unknown", "CHECKPOINT_MISSING")
    for name in sorted(set(before) - {"evidence_digests"}):
        if before[name] != current[name]:
            changed.add(f"baseline:{name}")
    for item in sorted(set(before["evidence_digests"]) ^ set(current["evidence_digests"])):
        changed.add(f"evidence:{item}")
    replayed = {item["assessment_digest"]: item for item in replays}
    if set(replayed) != set(current["evidence_digests"]):
        for item in sorted(set(replayed) ^ set(current["evidence_digests"])):
            changed.add(f"evidence:{item}")
    for item_digest, item in replayed.items():
        if item["reproduced"] is not True or item["outcome"] != "pass":
            changed.add(f"evidence:{item_digest}")
            reasons.add("EVIDENCE_NOT_ELIGIBLE")
    if changed:
        block("block_drift", "RESUME_BASELINE_STALE")
    stages = inspection.get("stages")
    in_flight: list[str] = []
    if not isinstance(stages, list):
        block("reconciliation_required", "EFFECT_RECONCILIATION_REQUIRED")
    else:
        in_flight = sorted(
            item["id"]
            for item in stages
            if isinstance(item, dict) and item.get("status") not in SETTLED_STAGE_STATUSES
        )
    by_stage: dict[str, list[dict[str, str]]] = {}
    for effect in selected_effects:
        by_stage.setdefault(effect["stage"], []).append(effect)
    for stage in in_flight:
        # Native continuation re-executes an in-flight stage; only a confirmed absent
        # effect is safe to repeat.
        records = by_stage.get(stage, [])
        if not records or any(item["state"] != "confirmed_absent" for item in records):
            block("reconciliation_required", "EFFECT_RECONCILIATION_REQUIRED")
    if any(item["state"] == "unknown" for item in selected_effects):
        block("reconciliation_required", "EFFECT_RECONCILIATION_REQUIRED")
    attempt_limit = intent["limits"]["attempts"]
    if binding["resume_attempts"] >= attempt_limit:
        block("block_unknown", "RESUME_ATTEMPTS_EXHAUSTED")
    if "RESUME_UNCERTAIN" in binding["reason_codes"]:
        block("reconciliation_required", "EFFECT_RECONCILIATION_REQUIRED")
    decision = next((item for item in DECISIONS if item in decisions), "admit")
    return seal(
        {
            "schema_version": 1,
            "kind": "runtime_resume_decision",
            "intent_id": binding["intent_id"],
            "run_id": run_id,
            "registered_version_id": binding["version_id"],
            "native_status": {"kind": status, "reason": native_reason},
            "checkpoint": None
            if not isinstance(checkpoint, dict)
            else {
                "stage": checkpoint.get("stage"),
                "checkpoint_seq": checkpoint.get("checkpoint_seq"),
                "run_commit_sha": checkpoint.get("run_commit_sha"),
            },
            "baseline_before_digest": digest(before, exclude="__none__"),
            "baseline_now_digest": digest(current, exclude="__none__"),
            "changed_bindings": sorted(changed),
            "in_flight_stages": in_flight,
            "effects": selected_effects,
            "evidence": replays,
            "attempts": binding["resume_attempts"],
            "attempt_limit": attempt_limit,
            "decision": decision,
            "native_action": "not_sent",
            "reason_codes": sorted(reasons),
            "production_authority": "unavailable",
            "engineering_readiness": "not_evaluated",
        }
    )


def validate_decision(value: Any) -> dict[str, Any]:
    record = exact(value, DECISION_FIELDS | {"schema_version", "kind"}, "/runtime_resume_decision")
    if record["schema_version"] != 1 or record["kind"] != "runtime_resume_decision":
        raise InputError("VERSION_UNSUPPORTED", "Unsupported resume decision")
    verify_digest(record, "/runtime_resume_decision")
    if record["decision"] not in {*DECISIONS, "admit"} or record["native_action"] not in {
        "not_sent",
        "accepted",
        "uncertain",
    }:
        raise InputError("FIELD_UNKNOWN", "Unknown resume decision")
    return record
