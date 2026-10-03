"""Narrow existing reviewed action projections before IR IDs/pins are computed."""

from __future__ import annotations

import copy
from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, canonical, checked, record
from score_sw_fabric.optimization.prompts import render_prompt


def narrow_projection(
    projected: dict[str, Any], bindings: dict[str, dict[str, Any]], mode: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    checked(mode, "optimization_mode_plan")
    result = copy.deepcopy(projected)
    actions = {action["ref"]: action for action in result["actions"]}
    agents = {ref for ref, action in actions.items() if action["type"] in {"agent", "prompt"}}
    if set(bindings) != agents:
        raise OptimizationError("AGENT_CONTEXT_BINDING")
    for ref in mode["mandatory_checks"]:
        if ref not in actions or actions[ref]["type"] not in {"command", "deterministic_check"}:
            raise OptimizationError("MANDATORY_CHECK_MISSING")
    for ref in mode["human_gates"]:
        if ref not in actions or actions[ref]["type"] != "human":
            raise OptimizationError("HUMAN_GATE_MISSING")
    if not mode["agent_required"] and agents:
        # Caller supplies a reviewed command-only projection; never remove obligation nodes.
        raise OptimizationError("MODE_REQUIRES_COMMAND_ONLY_PROJECTION")
    receipts = []
    for ref in sorted(agents):
        context, governor = bindings[ref]["context"], bindings[ref]["governor"]
        checked(context, "optimized_context_bundle")
        checked(governor, "token_governor_decision")
        if (
            governor["decision"] != "admissible"
            or governor["manifest_digest"] != context["manifest_digest"]
        ):
            raise OptimizationError("GOVERNOR_CONTEXT_BINDING")
        action = actions[ref]
        prompt = render_prompt(
            action["purpose"],
            action["prohibited_authority"],
            "Use only the mandatory digest-bound bounded tool service.",
            canonical({"l1": context["l1"], "skills": context["skills"]}).decode(),
            context["l0"],
            {"manifest_digest": context["manifest_digest"]},
        )
        if len(prompt.encode()) > governor["limits"]["context_tokens"]:
            raise OptimizationError("REQUIRED_CONTEXT_LIMIT")
        action["purpose"] = prompt
        for name in ("input_tokens", "output_tokens"):
            action["budget"][name] = min(action["budget"][name], governor["limits"][name])
        action["budget"]["attempts"] = min(
            action["budget"]["attempts"], governor["limits"]["calls"]
        )
        receipts.append(
            {"ref": ref, "context_digest": context["digest"], "governor_digest": governor["digest"]}
        )
    return result, record(
        "optimized_projection_binding",
        mode_digest=mode["digest"],
        agent_bindings=receipts,
        mandatory_guard="repository_bounded_command_hook",
        native_activation="unqualified",
        execution_authorized=False,
    )
