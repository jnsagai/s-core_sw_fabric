"""Canonical native Fabro source rendering."""

from __future__ import annotations

import json
from typing import Any

from score_sw_fabric.compiler.models import CompilerSemanticError
from score_sw_fabric.process_source.reader import InputError


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _node_line(node: dict[str, Any]) -> str:
    attributes: dict[str, str] = {
        "allow_partial": "false",
        "label": _quote(node["label"]),
        "max_retries": str(max(0, node["budget"]["attempts"] - 1)),
        "max_visits": str(node["budget"]["attempts"]),
        "on_failure": _quote("route"),
        "selection": _quote("deterministic"),
        "timeout": _quote(f"{node['budget']['wall_time_seconds']}s"),
        "type": _quote(node["native_type"]),
    }
    if node["native_type"] in {"start", "exit"}:
        attributes = {"label": _quote(node["label"]), "type": _quote(node["native_type"])}
    elif node["native_type"] == "command":
        attributes["script"] = _quote("true")
    elif node["native_type"] in {"agent", "prompt"}:
        attributes["prompt"] = _quote(node["purpose"])
        attributes["max_tokens"] = str(node["budget"]["output_tokens"])
        attributes["project_memory"] = "false"
    elif node["native_type"] == "human":
        attributes["question_type"] = _quote("yes_no")
    rendered = ", ".join(f"{name}={attributes[name]}" for name in sorted(attributes))
    return f"  {node['id']} [{rendered}];"


def _condition(edge: dict[str, Any]) -> str | None:
    explicit = edge["condition"]
    if isinstance(explicit, str):
        return explicit
    outcomes = {
        "success": "succeeded",
        "failure": "failed",
        "blocked": "failed",
        "timeout": "failed",
        "unknown": "failed",
        "malformed": "failed",
        "infrastructure": "failed",
        "exhausted": "failed",
    }
    outcome = edge["outcome"]
    if outcome == "success":
        return None
    return (
        f"outcome={outcomes[outcome]}" if isinstance(outcome, str) and outcome in outcomes else None
    )


def render_native(graph: dict[str, Any], support_files: list[dict[str, Any]]) -> dict[str, str]:
    """Render a sorted explicit Fabro graph and its closed support-file set."""

    lines = [
        "digraph SCoreWorkflow {",
        (
            '  graph [goal="Execute reviewed S-CORE obligations", '
            'max_node_visits=20, on_failure="route"];'
        ),
        "  rankdir=LR;",
    ]
    for node in graph["nodes"]:
        lines.append(_node_line(node))
    for edge in graph["edges"]:
        condition = _condition(edge)
        suffix = f" [condition={_quote(condition)}]" if condition else ""
        lines.append(f"  {edge['source']} -> {edge['target']}{suffix};")
    lines.append("}")
    files = {
        "workflow.fabro": "\n".join(lines) + "\n",
        "workflow.toml": '_version = 1\n\n[workflow]\ngraph = "workflow.fabro"\n',
    }
    expected = {"path", "content", "origin"}
    for index, item in enumerate(support_files):
        if not isinstance(item, dict) or set(item) != expected:
            raise InputError("SUPPORT_FILE", f"Invalid support file at /support_files/{index}")
        path = item["path"]
        content = item["content"]
        if not isinstance(path, str) or not isinstance(content, str):
            raise InputError("SUPPORT_FILE", "Support file path and content must be strings")
        if path in files:
            raise CompilerSemanticError("SUPPORT_FILE_CONFLICT", f"Duplicate generated path {path}")
        files[path] = content.replace("\r\n", "\n").replace("\r", "\n")
    return dict(sorted(files.items()))
