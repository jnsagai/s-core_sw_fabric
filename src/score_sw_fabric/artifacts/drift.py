"""Read-only candidate integrity and optional exact-request rederivation checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from score_sw_fabric.artifacts.models import unevaluated_capabilities
from score_sw_fabric.artifacts.package import build_candidate, validate_candidate
from score_sw_fabric.artifacts.reader import load_artifact_inputs
from score_sw_fabric.compiler.reader import semantic_digest
from score_sw_fabric.process_source.reader import InputError


def inspect_drift(
    candidate: dict[str, Any], profile: dict[str, Any], *, request: Path | None = None
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    direct = False
    try:
        validate_candidate(candidate, profile)
    except (InputError, Exception) as exc:
        direct = True
        findings.append(
            {
                "code": "GENERATED_DRIFT",
                "message": str(exc),
                "subjects": ["candidate"],
                "required_action": (
                    "Regenerate from reviewed inputs; direct output cannot be adopted."
                ),
            }
        )
    rederived_identity: str | None = None
    if request is not None and not direct:
        inputs = load_artifact_inputs(request)
        rederived = build_candidate(inputs)
        rederived_identity = rederived["candidate_identity"]
        if rederived_identity != candidate.get("candidate_identity"):
            findings.append(
                {
                    "code": "SOURCE_PROFILE_DRIFT",
                    "message": "Exact request rederivation differs",
                    "subjects": ["candidate"],
                    "required_action": "Review changed source/profile/request and regenerate.",
                }
            )
    result = {
        "schema_version": 1,
        "kind": "artifact_drift",
        "candidate": candidate.get("digest"),
        "direct_output_drift": direct,
        "source_profile_drift": any(item["code"] == "SOURCE_PROFILE_DRIFT" for item in findings),
        "rederived_candidate_identity": rederived_identity,
        "findings": findings,
        "clean": not findings,
        "capabilities": unevaluated_capabilities(),
    }
    result["digest"] = semantic_digest(result)
    return result
