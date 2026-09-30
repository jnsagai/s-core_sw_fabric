"""Deterministic compiler fixtures and side-effect recording validator stub."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.reader import semantic_digest


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["digest"] = semantic_digest(result)
    return result


def _origin(pointer: str) -> dict[str, Any]:
    return {
        "kind": "reviewed_project_configuration",
        "source_ref": {"fixture_origin": "tests/compiler_support.py"},
        "pointer": pointer,
        "decision_ref": "fixture-review-1",
        "rationale": "Synthetic reviewed compiler fixture; never production authority.",
    }


def compiler_profile() -> dict[str, Any]:
    return _seal(
        {
            "schema_version": 1,
            "id": "deterministic-compiler-v1",
            "version": 1,
            "canonicalization": "canonical-json-v1",
            "semantic_rules": "s-core-workflow-v1",
            "allowed_actions": [
                "agent",
                "prompt",
                "command",
                "deterministic_check",
                "human",
                "conditional",
                "parallel",
                "parallel_fan_in",
            ],
            "allowed_native_types": [
                "start",
                "exit",
                "agent",
                "prompt",
                "command",
                "human",
                "conditional",
                "parallel",
                "parallel.fan_in",
            ],
            "model_capabilities": [
                {"id": "none", "model_allowed": False},
                {
                    "id": "bounded-agent-v1",
                    "model_allowed": True,
                    "required": ["reasoning", "structured_output"],
                    "prohibited": ["approval", "trusted_evidence_collection"],
                },
            ],
            "limits": {
                "input_bytes": 67_108_864,
                "plan_instances": 10_000,
                "plan_dependencies": 100_000,
                "mapping_rules": 50_000,
                "ir_nodes": 50_000,
                "ir_edges": 200_000,
                "cyclic_components": 10_000,
                "package_bytes": 67_108_864,
                "native_files": 512,
                "native_file_bytes": 524_288,
                "native_total_bytes": 2_097_152,
                "action_budget": {
                    "wall_time_seconds": 14_400,
                    "attempts": 20,
                    "tool_calls": 1_000,
                    "input_tokens": 1_000_000,
                    "output_tokens": 200_000,
                    "cost_microunits": 100_000_000,
                },
            },
        }
    )


def validator_profile() -> dict[str, Any]:
    return _seal(
        {
            "schema_version": 1,
            "id": "fabro-conformance-1b4fb152-v1",
            "version": 1,
            "source_commit": "1b4fb15281ebb724426f9e480dce48d0100ff79b",
            "source_hashes": {
                "Cargo.toml": "a6cd812cfc2513400c2ba37f8c861daefd7099123036af9ffed24622739b338c",
                "Cargo.lock": "6c7e174e55528f4d677836045739ba94ddf6b614d187ded849108f6fe84800ee",
                "docs/public/reference/dot-language.mdx": (
                    "643eb11902d94a686474a006d1d79d86e8d2bf6cfb6fdee626915129449f423b"
                ),
                "docs/public/execution/run-configuration.mdx": (
                    "e84de643e25ad8dd8a695fe9d9d989b336d0f054968095bb5f4311682852fe8a"
                ),
                "lib/apps/fabro-cli/src/commands/validate.rs": (
                    "b87b2ee176e68b8c61a2da3b6ba49fdd28e2e8dfb98818b51870ab97f9d69da4"
                ),
                "lib/apps/fabro-cli/src/args.rs": (
                    "f12bcb9269c56f8814d60112a243bfa335d3d8c33bb440ab4a5792ea54aab492"
                ),
                "lib/components/fabro-tool/src/workflow_version.rs": (
                    "5b54c27120b09790b98e379be70581d17916051015c07870298587c99fcf9479"
                ),
            },
            "license": "MIT",
            "command": "validate",
            "timeout_seconds": 30,
            "executable_sha256": None,
        }
    )


def plan(instance_ids: tuple[str, ...] = ("obligation-a", "obligation-b")) -> dict[str, Any]:
    instances = []
    for index, identifier in enumerate(instance_ids):
        instances.append(
            {
                "instance_id": identifier,
                "applicability": "required",
                "effective_disposition": "create",
                "dependency_ids": [instance_ids[index - 1]] if index else [],
            }
        )
    return _seal(
        {
            "schema_version": 1,
            "plan_kind": "draft",
            "planning_status": "complete",
            "closure_complete": True,
            "engineering_readiness": "not_evaluated",
            "target_namespace": "fixture-target",
            "change": {"id": "fixture-change"},
            "semantic_inputs": {},
            "scopes": [],
            "coverage": [],
            "instances": instances,
            "findings": [],
        }
    )


def action(ref: str, instance_ids: list[str], *, action_type: str = "command") -> dict[str, Any]:
    model = action_type in {"agent", "prompt"}
    return {
        "ref": ref,
        "purpose": f"Execute {ref}",
        "type": action_type,
        "label": ref.replace("_", " ").title(),
        "instance_ids": instance_ids,
        "role": "reviewer" if action_type == "human" else "implementer",
        "allowed_inputs": ["reviewed-plan"],
        "allowed_paths": ["workspace/**"],
        "expected_outputs": [f"evidence/{ref}.json"],
        "data_destinations": ["package:evidence"],
        "write_scope": ["workspace/**"] if action_type != "human" else [],
        "tool_profile": "none" if action_type == "human" else "local-deterministic-v1",
        "model_capability": "bounded-agent-v1" if model else "none",
        "budget": {
            "wall_time_seconds": 60,
            "attempts": 2,
            "tool_calls": 4,
            "input_tokens": 1_000 if model else 0,
            "output_tokens": 500 if model else 0,
            "cost_microunits": 1_000 if model else 0,
        },
        "completion_predicate": f"{ref} produced declared evidence",
        "evidence_expectation": f"evidence/{ref}.json",
        "fallible_outcomes": ["success"],
        "prohibited_authority": [
            "approval",
            "trusted_evidence_collection",
            "automatic_approval",
            "replayed_approval",
        ],
        "support_files": [],
        "origin": _origin(f"/rules/fixture/actions/{ref}"),
    }


def edge(
    source: str,
    target: str,
    outcome: str | None = None,
    *,
    edge_type: str = "prerequisite",
    loop_id: str | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "type": edge_type,
        "outcome": outcome,
        "condition": None,
        "loop_id": loop_id,
        "origin": _origin(f"/edges/{source}-{target}-{outcome}"),
    }


def mapping(scenario: str = "linear") -> dict[str, Any]:
    if scenario == "shared-parallel-review":
        actions = [
            action("prepare", ["obligation-a"]),
            action("fork", ["obligation-a", "obligation-b"], action_type="parallel"),
            action("branch_a", ["obligation-a"]),
            action("branch_b", ["obligation-b"]),
            action(
                "join",
                ["obligation-a", "obligation-b"],
                action_type="parallel_fan_in",
            ),
            action("shared_review", ["obligation-a", "obligation-b"], action_type="human"),
            action("package", ["obligation-b"]),
        ]
        edges = [
            edge("start", "prepare"),
            edge("prepare", "fork", "success", edge_type="success"),
            edge("fork", "branch_a", edge_type="branch"),
            edge("fork", "branch_b", edge_type="branch"),
            edge("branch_a", "join", "success", edge_type="merge"),
            edge("branch_b", "join", "success", edge_type="merge"),
            edge("join", "shared_review", "success", edge_type="success"),
            edge("shared_review", "package", "success", edge_type="success"),
            edge("package", "exit", "success", edge_type="success"),
        ]
    elif scenario == "bounded-correction":
        actions = [
            action("prepare", ["obligation-a"]),
            action("check", ["obligation-b"], action_type="deterministic_check"),
            action("correct", ["obligation-b"]),
        ]
        actions[1]["fallible_outcomes"] = ["failure", "success"]
        edges = [
            edge("start", "prepare"),
            edge("prepare", "check", "success", edge_type="success"),
            edge("check", "exit", "success", edge_type="success"),
            edge("check", "correct", "failure", edge_type="failure", loop_id="correction"),
            edge("correct", "check", "success", edge_type="retry", loop_id="correction"),
        ]
    else:
        actions = [action("prepare", ["obligation-a"]), action("package", ["obligation-b"])]
        edges = [
            edge("start", "prepare"),
            edge("prepare", "package", "success", edge_type="success"),
            edge("package", "exit", "success", edge_type="success"),
        ]
    return _seal(
        {
            "schema_version": 1,
            "id": f"fixture-{scenario}",
            "version": 1,
            "plan_version": 1,
            "compiler_profile": "deterministic-compiler-v1",
            "review": {"state": "reviewed", "reference": {"fixture_review": "fixture-review-1"}},
            "rules": [
                {
                    "id": "fixture-rule",
                    "instance_ids": ["obligation-a", "obligation-b"],
                    "actions": actions,
                }
            ],
            "edges": edges,
            "loop_policies": (
                [
                    {
                        "id": "correction",
                        "max_visits": 3,
                        "retry_target": "check",
                        "exhausted_destination": "exit",
                        "origin": _origin("/loop_policies/correction"),
                    }
                ]
                if scenario == "bounded-correction"
                else []
            ),
            "fan_groups": (
                [
                    {
                        "id": "fixture-parallel",
                        "fan_out": "fork",
                        "branch_starts": ["branch_a", "branch_b"],
                        "branch_ends": ["branch_a", "branch_b"],
                        "fan_in": "join",
                        "required_branches": ["branch_a", "branch_b"],
                        "allow_partial": False,
                        "origin": _origin("/fan_groups/fixture-parallel"),
                    }
                ]
                if scenario == "shared-parallel-review"
                else []
            ),
            "support_files": [],
        }
    )


def _write_yaml(path: Path, value: dict[str, Any]) -> tuple[str, str]:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest(), value["digest"]


def prepare_case(root: Path, scenario: str = "linear") -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "out").mkdir(exist_ok=True)
    (root / "protected").mkdir(exist_ok=True)
    documents = {
        "plan": plan(),
        "execution_mapping": mapping(scenario),
        "compiler_profile": compiler_profile(),
        "validator_profile": validator_profile(),
    }
    references = {}
    for name, value in documents.items():
        suffix = ".json" if name == "plan" else ".yaml"
        path = root / f"{name}{suffix}"
        if suffix == ".json":
            path.write_bytes(canonical(value))
            transport = hashlib.sha256(path.read_bytes()).hexdigest()
            semantic = value["digest"]
        else:
            transport, semantic = _write_yaml(path, value)
        references[name] = {"path": path.name, "sha256": transport, "semantic_digest": semantic}
    request = {
        "schema_version": 1,
        "inputs": references,
        "local_paths": {"output_root": "out", "protected_roots": ["protected"]},
    }
    request_path = root / "request.yaml"
    request_path.write_text(yaml.safe_dump(request, sort_keys=False), encoding="utf-8")
    return request_path, root / "out" / "package.json"


class RecordingValidator:
    """Native-validator test double that records invocation and returns no runtime effects."""

    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, str], str, dict[str, Any]]] = []

    def __call__(
        self, files: dict[str, str], entrypoint: str, profile: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append((copy.deepcopy(files), entrypoint, copy.deepcopy(profile)))
        return {
            "validator": {"source_commit": profile["source_commit"], "profile": "test-double"},
            "source_set_digest": hashlib.sha256(canonical(files)).hexdigest(),
            "workflow_name": "SCoreWorkflow",
            "nodes": files["workflow.fabro"].count(" ["),
            "edges": files["workflow.fabro"].count(" -> "),
            "diagnostics": [],
            "accepted": True,
        }


def sentinel(path: Path, content: bytes = b"preserve-me") -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content
