"""Stable typed execution-graph derivation."""

from __future__ import annotations

import hashlib
from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.models import CompilerSemanticError
from score_sw_fabric.process_source.reader import InputError


def _identifier(prefix: str, key: dict[str, Any]) -> str:
    return f"{prefix}_{hashlib.sha256(canonical(key)).hexdigest()[:24]}"


def _system_node(ref: str, native_type: str, origin: dict[str, Any]) -> dict[str, Any]:
    key = {
        "plan_instance_ids": [],
        "execution_rule_id": "compiler",
        "action_purpose": ref,
        "action_role": "control",
    }
    return {
        "id": ref,
        "key": key,
        "ref": ref,
        "action_type": native_type,
        "native_type": native_type,
        "purpose": ref,
        "label": ref.title(),
        "instance_ids": [],
        "role": "control",
        "allowed_inputs": [],
        "allowed_paths": [],
        "expected_outputs": [],
        "data_destinations": [],
        "write_scope": [],
        "tool_profile": "none",
        "model_capability": "none",
        "budget": {
            "wall_time_seconds": 1,
            "attempts": 1,
            "tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_microunits": 0,
        },
        "completion_predicate": "control transition",
        "evidence_expectation": "none",
        "fallible_outcomes": ["success"],
        "prohibited_authority": ["approval", "trusted_evidence_collection"],
        "support_files": [],
        "origins": [origin],
    }


def validate_ir_counts(node_count: int, edge_count: int, profile: dict[str, Any]) -> None:
    if node_count > profile["limits"]["ir_nodes"]:
        raise CompilerSemanticError("NODE_LIMIT", "IR node limit exceeded")
    if edge_count > profile["limits"]["ir_edges"]:
        raise CompilerSemanticError("EDGE_LIMIT", "IR edge limit exceeded")


def build_ir(
    projected: dict[str, Any], mapping: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    """Build stable node and edge identifiers while retaining complete logical keys."""

    compiler_origin = {
        "kind": "reviewed_project_configuration",
        "source_ref": {"mapping_id": mapping["id"], "mapping_version": mapping["version"]},
        "pointer": "/",
        "decision_ref": None,
        "rationale": "Compiler-inserted unique workflow endpoint.",
    }
    nodes = [
        _system_node("start", "start", compiler_origin),
        _system_node("exit", "exit", compiler_origin),
    ]
    by_ref = {"start": nodes[0], "exit": nodes[1]}
    ids = {"start", "exit"}
    keys: dict[str, bytes] = {}
    native_map = {"deterministic_check": "command", "parallel_fan_in": "parallel.fan_in"}
    for action in projected["actions"]:
        key = {
            "plan_instance_ids": sorted(action["instance_ids"]),
            "execution_rule_id": action["rule_id"],
            "action_purpose": action["purpose"],
            "action_role": action["role"],
        }
        identifier = _identifier("node", key)
        if identifier in ids and keys.get(identifier) != canonical(key):
            raise CompilerSemanticError(
                "IDENTIFIER_COLLISION", f"Node identifier collision {identifier}"
            )
        if action["ref"] in by_ref:
            raise CompilerSemanticError("MAPPING_CONFLICT", f"Duplicate action ref {action['ref']}")
        ids.add(identifier)
        keys[identifier] = canonical(key)
        node = {
            "id": identifier,
            "key": key,
            "ref": action["ref"],
            "action_type": action["type"],
            "native_type": native_map.get(action["type"], action["type"]),
            "purpose": action["purpose"],
            "label": action["label"],
            "instance_ids": sorted(action["instance_ids"]),
            "role": action["role"],
            "allowed_inputs": action["allowed_inputs"],
            "allowed_paths": action["allowed_paths"],
            "expected_outputs": action["expected_outputs"],
            "data_destinations": action["data_destinations"],
            "write_scope": action["write_scope"],
            "tool_profile": action["tool_profile"],
            "model_capability": action["model_capability"],
            "budget": action["budget"],
            "completion_predicate": action["completion_predicate"],
            "evidence_expectation": action["evidence_expectation"],
            "fallible_outcomes": action["fallible_outcomes"],
            "prohibited_authority": action["prohibited_authority"],
            "support_files": action["support_files"],
            "origins": [action["origin"]],
        }
        nodes.append(node)
        by_ref[action["ref"]] = node

    edges: list[dict[str, Any]] = []
    edge_ids: dict[str, bytes] = {}
    expected_edge_fields = {"source", "target", "type", "outcome", "condition", "loop_id", "origin"}
    for index, raw in enumerate(projected["edges"]):
        if not isinstance(raw, dict) or set(raw) != expected_edge_fields:
            raise InputError("MAPPING_EDGE", f"Invalid edge at /edges/{index}")
        if raw["source"] not in by_ref or raw["target"] not in by_ref:
            raise CompilerSemanticError("DANGLING_EDGE", f"Unknown endpoint at /edges/{index}")
        source = by_ref[raw["source"]]
        target = by_ref[raw["target"]]
        key = {
            "source_node_key": source["key"],
            "target_node_key": target["key"],
            "edge_type": raw["type"],
            "outcome_or_branch": raw["outcome"] if raw["outcome"] is not None else raw["condition"],
            "loop_id_or_null": raw["loop_id"],
        }
        identifier = _identifier("edge", key)
        if identifier in edge_ids and edge_ids[identifier] != canonical(key):
            raise CompilerSemanticError(
                "IDENTIFIER_COLLISION", f"Edge identifier collision {identifier}"
            )
        if identifier in edge_ids:
            raise CompilerSemanticError("DUPLICATE_EDGE", f"Duplicate edge {identifier}")
        edge_ids[identifier] = canonical(key)
        edges.append(
            {
                "id": identifier,
                "key": key,
                "source": source["id"],
                "target": target["id"],
                "edge_type": raw["type"],
                "outcome": raw["outcome"],
                "condition": raw["condition"],
                "loop_id": raw["loop_id"],
                "origins": [raw["origin"]],
            }
        )
    validate_ir_counts(len(nodes), len(edges), profile)
    gates = [
        {
            "node_id": node["id"],
            "subjects": node["instance_ids"],
            "purpose": node["purpose"],
            "role": node["role"],
            "independent": True,
            "authority_requirement": "authenticated_external_human",
            "allowed_exclusion_ref": None,
            "origins": node["origins"],
        }
        for node in nodes
        if node["action_type"] == "human"
    ]
    return {
        "schema_version": 1,
        "id": "graph_"
        + hashlib.sha256(
            canonical({"nodes": [n["key"] for n in nodes], "edges": [e["key"] for e in edges]})
        ).hexdigest()[:24],
        "nodes": sorted(nodes, key=lambda item: item["id"]),
        "edges": sorted(edges, key=lambda item: item["id"]),
        "gates": sorted(gates, key=lambda item: item["node_id"]),
        "loop_policies": sorted(projected["loop_policies"], key=lambda item: item.get("id", "")),
        "fan_groups": sorted(projected["fan_groups"], key=lambda item: item.get("id", "")),
        "origins": [compiler_origin],
    }
