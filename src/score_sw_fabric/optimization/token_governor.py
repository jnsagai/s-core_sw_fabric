"""Operational limits narrow a verified 007 admission; they cannot authorize live calls."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.optimization.common import checked, integer, record
from score_sw_fabric.optimization.telemetry import aggregate

ENVELOPES = {
    "S0": {"input_tokens": 20000, "output_tokens": 2000, "calls": 1},
    "S1": {"input_tokens": 80000, "output_tokens": 10000, "calls": 2},
    "S2": {"input_tokens": 150000, "output_tokens": 12000, "calls": 3},
    "S3": {"input_tokens": 300000, "output_tokens": 20000, "calls": 3},
}


def govern(
    task_class: str,
    admission: dict[str, Any],
    context_tokens: int,
    entries: list[dict[str, Any]],
    *,
    corrections: int = 0,
    human_gate: bool = False,
    manifest_digest: str | None = None,
    gates_passed: bool = False,
    reviewer_required: bool = False,
) -> dict[str, Any]:
    checked(admission, "agent_admission")
    integer(context_tokens)
    integer(corrections)
    reasons = []
    if task_class not in ENVELOPES:
        reasons.append("EXPLICIT_SCOPE_AUTHORIZATION_REQUIRED")
    if admission.get("decision") != "admissible":
        reasons.append("ADMISSION_REFUSED")
    if not admission.get("provider_configured") or not admission.get("offering"):
        reasons.append("PROVIDER_UNAVAILABLE")
    if human_gate:
        reasons.append("HUMAN_GATE")
    if corrections > 1:
        reasons.append("CORRECTION_LIMIT")
    metrics = aggregate(entries)["metrics"]
    if entries and any(
        metrics.get(i) is None for i in ("input_tokens", "output_tokens", "cost_microusd")
    ):
        reasons.append("USAGE_UNKNOWN")
    envelope = ENVELOPES.get(task_class, ENVELOPES["S0"])
    limits = {}
    for name, maximum in envelope.items():
        remaining = admission.get("remaining", {}).get(name)
        if remaining is None:
            reasons.append("USAGE_UNKNOWN")
            remaining = 0
        integer(remaining)
        reported = len(entries) if name == "calls" else metrics.get(name)
        original_spent = admission.get("used", {}).get(name)
        spent = max(reported or 0, original_spent or 0)
        limits[name] = max(0, min(maximum - (spent or 0), remaining))
    limits["output_tokens"] = min(
        limits["output_tokens"], admission["profile"]["max_output_tokens"]
    )
    limits.update({"context_tokens": 24000, "tool_result_tokens": 12000, "correction_visits": 1})
    if context_tokens > limits["context_tokens"] or context_tokens > limits["input_tokens"]:
        reasons.append("CONTEXT_BUDGET")
    estimate = admission.get("estimate", {}).get("input_tokens", context_tokens)
    if estimate is None or estimate > limits["input_tokens"]:
        reasons.append("OPERATIONAL_INPUT_LIMIT")
    if limits["calls"] < 1 or limits["output_tokens"] < 1:
        reasons.append("BUDGET_EXHAUSTED")
    from score_sw_fabric.optimization.model_router import route

    routing = (
        route(
            task_class,
            gates_passed=gates_passed,
            corrections=min(corrections, 1),
            reviewer_required=reviewer_required,
        )
        if task_class in ENVELOPES
        else None
    )
    return record(
        "token_governor_decision",
        task_class=task_class,
        admission_digest=admission["digest"],
        manifest_digest=manifest_digest,
        ledger_digests=[i["digest"] for i in entries],
        limits=limits,
        model_profile=admission["profile"]["id"],
        decision="refused" if reasons else "admissible",
        reasons=sorted(set(reasons)),
        call_authorized=False,
        routing=routing,
    )
