"""Mandatory L0/L1 plus explicitly requested L2; token accounting never claims provider usage."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.optimization.common import (
    OptimizationError,
    canonical,
    checked,
    integer,
    record,
    token_estimate,
)


def build_bundle(
    scope: dict[str, Any],
    baseline: str,
    envelope: dict[str, Any],
    required: dict[str, str],
    *,
    optional: dict[str, str] | None = None,
    skills: list[dict[str, Any]] | None = None,
    observations: list[dict[str, Any]] | None = None,
    tool_schema: str = "",
    max_tokens: int = 24000,
) -> dict[str, Any]:
    integer(max_tokens, minimum=1, maximum=24000)
    checked(scope, "context_manifest")
    if scope["baseline"] != baseline:
        raise OptimizationError("BASELINE_DRIFT")
    if not envelope.get("constraints"):
        raise OptimizationError("L0_MISSING")
    if set(scope["primary"]) - set(required):
        raise OptimizationError("REQUIRED_CONTEXT_MISSING")
    if set(required) - set(scope["primary"] + scope["related"]):
        raise OptimizationError("CONTEXT_OUT_OF_SCOPE")
    selected_skills = skills or []
    for skill in selected_skills:
        checked(skill, "rendered_skill")
        if skill["baseline"] != baseline:
            raise OptimizationError("SKILL_BASELINE_DRIFT")
    selected_observations = sorted(
        observations or [], key=lambda i: (i.get("baseline") != baseline, i["id"])
    )[:20]
    metadata = [
        {key: row.get(key) for key in ("id", "baseline", "line_sha256", "state")}
        for row in selected_observations
    ]
    l0 = {
        **envelope,
        "task": scope["task"],
        "baseline": baseline,
        "native_ids": scope["native_ids"],
    }
    counts = {
        "l0": token_estimate(canonical(l0)),
        "l1": token_estimate(canonical(required)),
        "skills": token_estimate(canonical(selected_skills)),
        "observations": token_estimate(canonical(metadata)),
        "tool_schema": token_estimate(tool_schema),
    }
    mandatory_total = sum(counts.values())
    if mandatory_total > max_tokens:
        raise OptimizationError("REQUIRED_CONTEXT_LIMIT")
    extra: dict[str, str] = {}
    omissions = []
    if len(observations or []) > len(metadata):
        omissions.append("OBSERVATION_INDEX_LIMIT")
    for key, value in sorted((optional or {}).items()):
        if key not in scope["related"]:
            omissions.append("L2_OUT_OF_SCOPE:" + key)
        elif mandatory_total + token_estimate(canonical({**extra, key: value})) <= max_tokens:
            extra[key] = value
        else:
            omissions.append("L2_CONTEXT_LIMIT:" + key)
    counts["l2"] = token_estimate(canonical(extra))
    counts["total"] = sum(counts.values())
    # Empty container accounting must not overshoot a tight envelope.
    if counts["total"] > max_tokens:
        raise OptimizationError("REQUIRED_CONTEXT_LIMIT")
    result = record(
        "optimized_context_bundle",
        manifest_digest=scope["digest"],
        l0=l0,
        l1=required,
        l2=extra,
        skills=selected_skills,
        observations=metadata,
        omissions=omissions,
        context_accounting={
            "estimated_tokens": counts,
            "limit": max_tokens,
            "method": "utf8_bytes_upper_bound",
        },
    )

    # Account for the complete serialized bundle, including bookkeeping and omission metadata.
    while True:
        actual = token_estimate(canonical(result)) + counts["tool_schema"]
        if actual <= max_tokens:
            for _ in range(5):
                counts["total"] = token_estimate(canonical(result)) + counts["tool_schema"]
                result = record(
                    "optimized_context_bundle",
                    **{
                        key: value
                        for key, value in result.items()
                        if key not in {"schema_version", "kind", "digest"}
                    },
                )
            if counts["total"] <= max_tokens:
                return result
        if not extra:
            raise OptimizationError("REQUIRED_CONTEXT_LIMIT")
        key = sorted(extra)[-1]
        extra.pop(key)
        omissions.append("L2_SERIALIZED_CONTEXT_LIMIT:" + key)
        counts["l2"] = token_estimate(canonical(extra))
        result = record(
            "optimized_context_bundle",
            **{
                key: value
                for key, value in result.items()
                if key not in {"schema_version", "kind", "digest"}
            },
        )
