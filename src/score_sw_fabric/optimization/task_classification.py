"""Task classes derived from explicit facts, never inferred by an LLM."""

from __future__ import annotations

import hashlib
from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, canonical, integer, record

CLASSIFICATION_POLICY: dict[str, Any] = {
    "broad_modules": 3,
    "broad_paths": 30,
    "broad_requirements": 20,
    "component_requirements": 3,
    "precedence": ["unknown", "S4", "S3", "S2", "S0", "S1"],
}


def classify(task: str, facts: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "modules",
        "paths",
        "requirements",
        "unknown_dependencies",
        "metadata_only",
        "feature_change",
        "safety",
        "architecture",
        "interface",
        "security",
        "investigation",
    }
    if set(facts) - allowed or not {"modules", "paths", "requirements"} <= set(facts):
        raise OptimizationError("CLASSIFICATION_FACTS")
    for name in ("modules", "paths", "requirements"):
        integer(facts[name], maximum=10000)
    for name in allowed - {"modules", "paths", "requirements"}:
        if name in facts and type(facts[name]) is not bool:
            raise OptimizationError("CLASSIFICATION_FACTS")
    if facts.get("unknown_dependencies") or facts["modules"] == 0:
        selected, reason = "unknown", "UNRESOLVED_SCOPE"
    elif (
        facts["modules"] > CLASSIFICATION_POLICY["broad_modules"]
        or facts["paths"] > CLASSIFICATION_POLICY["broad_paths"]
        or facts["requirements"] > CLASSIFICATION_POLICY["broad_requirements"]
        or facts.get("investigation")
    ):
        selected, reason = "S4", "BROAD_OR_EXCEPTIONAL_SCOPE"
    elif any(facts.get(i) for i in ("safety", "architecture", "interface", "security")):
        selected, reason = "S3", "SENSITIVE_WORK_PRODUCT"
    elif (
        facts.get("feature_change")
        or facts["modules"] > 1
        or facts["requirements"] > CLASSIFICATION_POLICY["component_requirements"]
    ):
        selected, reason = "S2", "COMPONENT_ENGINEERING"
    elif facts.get("metadata_only"):
        selected, reason = "S0", "MECHANICAL_METADATA"
    else:
        selected, reason = "S1", "LOCAL_IMPLEMENTATION"
    return record(
        "task_classification",
        task=task,
        **{"class": selected},
        facts=facts,
        reasons=[reason],
        confidence="deterministic",
        policy="optimization-v1",
        policy_digest=hashlib.sha256(canonical(CLASSIFICATION_POLICY)).hexdigest(),
    )
