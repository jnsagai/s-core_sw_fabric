"""Deterministic fabric-semantic validation for typed execution graphs."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from score_sw_fabric.compiler.models import CompilerSemanticError, ValidationFinding

EDGE_TYPES = {
    "prerequisite",
    "success",
    "failure",
    "blocked",
    "timeout",
    "unknown",
    "malformed",
    "infrastructure",
    "exhausted",
    "condition",
    "branch",
    "merge",
    "retry",
    "feedback",
}


def _finding(
    code: str, message: str, subjects: list[str], path: list[str] | None = None
) -> ValidationFinding:
    return {
        "code": code,
        "phase": "fabric_semantics",
        "message": message,
        "subjects": sorted(subjects),
        "path": path or [],
        "required_action": "Correct the reviewed mapping and compile again.",
    }


def _reachable(start: str, adjacency: dict[str, list[str]], blocked: str | None = None) -> set[str]:
    seen: set[str] = set()
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current == blocked or current in seen:
            continue
        seen.add(current)
        queue.extend(adjacency.get(current, []))
    return seen


def _shortest(
    start: str, end: str, adjacency: dict[str, list[str]], blocked: str | None = None
) -> list[str]:
    queue = deque([(start, [start])])
    seen: set[str] = set()
    while queue:
        current, path = queue.popleft()
        if current == blocked or current in seen:
            continue
        if current == end:
            return path
        seen.add(current)
        for target in adjacency.get(current, []):
            queue.append((target, [*path, target]))
    return []


def _components(nodes: set[str], adjacency: dict[str, list[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indexes: dict[str, int] = {}
    low: dict[str, int] = {}
    result: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = index
        low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in adjacency.get(node, []):
            if target not in indexes:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indexes[target])
        if low[node] == indexes[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            result.append(sorted(component))

    for node in sorted(nodes):
        if node not in indexes:
            visit(node)
    return sorted(result)


def validate_cyclic_component_count(count: int, profile: dict[str, Any]) -> None:
    if count > profile["limits"]["cyclic_components"]:
        raise CompilerSemanticError("CYCLE_LIMIT", "Cyclic-component limit exceeded")


def validate_graph(graph: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Return a stable receipt or raise with ordered semantic findings."""

    findings: list[ValidationFinding] = []
    nodes = graph["nodes"]
    edges = graph["edges"]
    by_id = {item["id"]: item for item in nodes}
    if len(by_id) != len(nodes):
        findings.append(_finding("DUPLICATE_NODE", "Node IDs must be unique", []))
    starts = [item["id"] for item in nodes if item["native_type"] == "start"]
    exits = [item["id"] for item in nodes if item["native_type"] == "exit"]
    if starts != ["start"]:
        findings.append(_finding("START_COUNT", "Exactly one start node is required", starts))
    if exits != ["exit"]:
        findings.append(_finding("EXIT_COUNT", "Exactly one success exit is required", exits))
    adjacency: dict[str, list[str]] = defaultdict(list)
    reverse: dict[str, list[str]] = defaultdict(list)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        if edge["edge_type"] not in EDGE_TYPES:
            findings.append(_finding("EDGE_TYPE", "Unsupported edge type", [edge["id"]]))
        if edge["source"] not in by_id or edge["target"] not in by_id:
            findings.append(_finding("DANGLING_EDGE", "Edge endpoint is absent", [edge["id"]]))
            continue
        adjacency[edge["source"]].append(edge["target"])
        reverse[edge["target"]].append(edge["source"])
        outgoing[edge["source"]].append(edge)
    for value in adjacency.values():
        value.sort()
    for value in reverse.values():
        value.sort()
    if starts and exits:
        reachable = _reachable(starts[0], adjacency)
        can_exit = _reachable(exits[0], reverse)
        for node_id in sorted(set(by_id) - reachable):
            findings.append(
                _finding("UNREACHABLE_NODE", "Node is unreachable from start", [node_id])
            )
        for node_id in sorted(set(by_id) - can_exit):
            findings.append(
                _finding("NO_SUCCESS_PATH", "Node cannot reach success exit", [node_id])
            )
        for gate in graph["gates"]:
            gate_id = gate["node_id"]
            path = _shortest(starts[0], exits[0], adjacency, blocked=gate_id)
            subjects = set(gate["subjects"])
            if (
                path
                and subjects
                and any(
                    subjects & set(by_id[item]["instance_ids"]) for item in path if item in by_id
                )
            ):
                findings.append(
                    _finding("GATE_BYPASS", "Required gate can be bypassed", [gate_id], path)
                )

    for node in nodes:
        if node["native_type"] == "exit":
            continue
        actual = [edge["outcome"] for edge in outgoing[node["id"]] if edge["outcome"] is not None]
        duplicates = sorted({item for item in actual if actual.count(item) > 1})
        if duplicates:
            findings.append(
                _finding("OUTCOME_OVERLAP", f"Overlapping outcomes: {duplicates}", [node["id"]])
            )
        declared = set(node["fallible_outcomes"])
        routed = set(actual)
        if node["native_type"] not in {"start", "parallel"} and not declared <= routed:
            findings.append(
                _finding(
                    "OUTCOME_GAP", f"Unrouted outcomes: {sorted(declared - routed)}", [node["id"]]
                )
            )
        if "unknown" in declared and "unknown" not in routed:
            findings.append(
                _finding("UNKNOWN_FALLTHROUGH", "Unknown outcome cannot fall through", [node["id"]])
            )
        prohibited = set(node["prohibited_authority"])
        if (
            node["action_type"] == "human"
            and not {"automatic_approval", "replayed_approval"} <= prohibited
        ):
            findings.append(
                _finding(
                    "APPROVAL_AUTHORITY",
                    "Human gates must prohibit automatic and replayed approval",
                    [node["id"]],
                )
            )
        if node["model_capability"] != "none" and node["action_type"] not in {"agent", "prompt"}:
            findings.append(
                _finding("MODEL_AUTHORITY", "Non-model action has model capability", [node["id"]])
            )

    components = _components(set(by_id), adjacency)
    cyclic = [
        component
        for component in components
        if len(component) > 1 or (component and component[0] in adjacency.get(component[0], []))
    ]
    policies = {item.get("id"): item for item in graph["loop_policies"] if isinstance(item, dict)}
    try:
        validate_cyclic_component_count(len(cyclic), profile)
    except CompilerSemanticError:
        findings.append(_finding("CYCLE_LIMIT", "Cyclic-component limit exceeded", []))
    for component in cyclic:
        loop_ids = {
            edge["loop_id"]
            for edge in edges
            if edge["source"] in component
            and edge["target"] in component
            and edge["loop_id"] is not None
        }
        if len(loop_ids) != 1 or next(iter(loop_ids), None) not in policies:
            findings.append(
                _finding(
                    "UNBOUNDED_CYCLE", "Cycle lacks one declared loop policy", component, component
                )
            )
            continue
        policy = policies[next(iter(loop_ids))]
        visits = policy.get("max_visits")
        if (
            type(visits) is not int
            or visits < 1
            or visits > profile["limits"]["action_budget"]["attempts"]
        ):
            findings.append(
                _finding("LOOP_BOUND", "Loop bound is missing or invalid", component, component)
            )
        exhausted = policy.get("exhausted_destination")
        if exhausted not in by_id or exhausted in component:
            findings.append(
                _finding(
                    "LOOP_EXHAUSTION",
                    "Loop needs an external exhausted destination",
                    component,
                    component,
                )
            )

    refs = {node["ref"]: node["id"] for node in nodes}
    for fan in graph["fan_groups"]:
        required = {
            "id",
            "fan_out",
            "branch_starts",
            "branch_ends",
            "fan_in",
            "required_branches",
            "allow_partial",
            "origin",
        }
        if not isinstance(fan, dict) or set(fan) != required:
            findings.append(_finding("FAN_FIELDS", "Fan group has invalid fields", []))
            continue
        starts_set = set(fan["branch_starts"])
        ends_set = set(fan["branch_ends"])
        required_set = set(fan["required_branches"])
        if (
            not starts_set
            or len(starts_set) != len(fan["branch_starts"])
            or len(ends_set) != len(starts_set)
        ):
            findings.append(
                _finding("FAN_MISMATCH", "Fan branches must be nonempty and paired", [fan["id"]])
            )
        if fan["allow_partial"] is not False or required_set != starts_set:
            findings.append(
                _finding("PARTIAL_MERGE", "Mandatory fan-in must require every branch", [fan["id"]])
            )
        if any(ref not in refs for ref in starts_set | ends_set | {fan["fan_out"], fan["fan_in"]}):
            findings.append(
                _finding("FAN_DANGLING", "Fan group references an absent action", [fan["id"]])
            )

    findings.sort(key=lambda item: (item["code"], item["subjects"], item["path"]))
    receipt = {
        "ruleset": profile["semantic_rules"],
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "gates": len(graph["gates"]),
            "cyclic_components": len(cyclic),
        },
        "findings": findings,
        "valid": not findings,
    }
    if findings:
        raise CompilerSemanticError(
            "SEMANTIC_INVALID", "Workflow graph violates fabric semantics", findings=findings
        )
    return receipt
