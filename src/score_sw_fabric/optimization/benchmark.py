"""Five deterministic fixture comparisons; never impersonate provider usage or acceptance."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from score_sw_fabric.optimization.common import canonical, record, token_estimate

TASKS = (
    "metadata",
    "cpp-correction",
    "unit-test-correction",
    "component-feature",
    "safety-architecture",
)


def baseline() -> dict[str, Any]:
    rows = []
    for number, name in enumerate(TASKS, 1):
        documents = {
            f"native-fixture-{index}": (
                f"Synthetic development reference {index}: constraints, "
                "source and unrelated history.\n"
            )
            * 20
            for index in range(50)
        }
        required = sorted(documents)[: number + 1]
        rows.append(
            {
                "id": f"B{number}",
                "task": name,
                "documents": documents,
                "required": required,
                "mandatory_checks": ["structure", "trace", "freshness", "human-pending"],
                "evidence_refs": ["fixture-raw-evidence"],
                "provider_usage": None,
                "baseline_estimated_tokens": token_estimate(canonical(documents)),
            }
        )
    return record(
        "optimization_benchmark_baseline",
        origin="synthetic_context_control",
        tasks=rows,
        measurement="utf8_bytes_upper_bound",
        live_calls=0,
    )


def run_benchmark(output: Path) -> dict[str, Any]:
    from score_sw_fabric.optimization.common import checked, json_object

    output.mkdir(parents=True, exist_ok=True)
    path = output / "baseline.json"
    if path.exists():
        original = checked(json_object(path.read_bytes()), "optimization_benchmark_baseline")
    else:
        original = baseline()
        path.write_bytes(canonical(original) + b"\n")
    comparisons = []
    for row in original["tasks"]:
        import hashlib

        from score_sw_fabric.optimization.context_budget import build_bundle
        from score_sw_fabric.optimization.context_manifest import manifest
        from score_sw_fabric.optimization.impact import impact

        nodes = [
            {"key": key, "fingerprint": hashlib.sha256(text.encode()).hexdigest()}
            for key, text in sorted(row["documents"].items())
        ]
        relations = [{"source": key, "target": row["required"][0]} for key in row["required"]]
        old = record("artifact_index", needs=nodes, wrappers=[], relations=relations)
        revised = [dict(node) for node in nodes]
        next(node for node in revised if node["key"] == row["required"][0])["fingerprint"] = (
            "fixture-change"
        )
        new = record("artifact_index", needs=revised, wrappers=[], relations=relations)
        changes = impact(old, new)
        mapping = {key: ["fixture/" + key + ".rst"] for key in row["documents"]}
        scope = manifest(row["id"], new["digest"], changes, new, mapping)
        scoped = {mapping[key][0]: row["documents"][key] for key in scope["native_ids"]}
        context = build_bundle(
            scope,
            new["digest"],
            {
                "constraints": ["preserve every declared fixture check", "human remains pending"],
                "output_contract": "fixture-structured-draft",
            },
            scoped,
            max_tokens=24000,
        )
        count = context["context_accounting"]["estimated_tokens"]["total"]

        # Evaluate exactly the same development-only structural predicates on both contexts.
        def evaluate(
            documents: dict[str, str],
            mapping: dict[str, list[str]] = mapping,
            row: dict[str, Any] = row,
        ) -> dict[str, Any]:
            found = {
                key: documents.get(mapping[key][0], documents.get(key)) for key in row["required"]
            }
            return {
                "structure": all(isinstance(text, str) and text for text in found.values()),
                "trace": sorted(key for key, value in found.items() if value is not None),
                "freshness": all(found[key] == row["documents"][key] for key in found),
                "human": "pending",
                "mandatory_checks": row["mandatory_checks"],
            }

        baseline_outcome = evaluate(row["documents"])
        optimized_outcome = evaluate(context["l1"])
        if baseline_outcome != optimized_outcome:
            from score_sw_fabric.optimization.common import OptimizationError

            raise OptimizationError("BENCHMARK_OUTCOME_MISMATCH")
        comparisons.append(
            {
                "id": row["id"],
                "task": row["task"],
                "baseline_estimated_tokens": row["baseline_estimated_tokens"],
                "optimized_estimated_tokens": count,
                "estimated_reduction_percent": round(
                    100 * (1 - count / row["baseline_estimated_tokens"]), 2
                ),
                "mandatory_checks": row["mandatory_checks"],
                "native_ids": row["required"],
                "evidence_refs": row["evidence_refs"],
                "baseline_outcome": baseline_outcome,
                "optimized_outcome": optimized_outcome,
                "context_digest": context["digest"],
                "impact_digest": changes["digest"],
                "deterministic_outcome": "development_fixture_pass_human_pending",
                "provider_metrics": {
                    key: None
                    for key in (
                        "input_tokens",
                        "cached_input_tokens",
                        "uncached_input_tokens",
                        "output_tokens",
                        "reasoning_tokens",
                        "cost_microusd",
                        "model_calls",
                        "tool_calls",
                        "wall_time",
                        "corrections",
                        "critic_calls",
                        "escalations",
                    )
                },
                "live_savings": "unmeasured",
            }
        )
    result = record(
        "optimization_benchmark",
        baseline_digest=original["digest"],
        measurement="utf8_bytes_upper_bound",
        origin="synthetic_context_control",
        comparisons=comparisons,
        engineering_acceptance="pending",
    )
    (output / "optimized.json").write_bytes(canonical(result) + b"\n")
    return result
