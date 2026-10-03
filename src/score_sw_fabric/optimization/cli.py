"""Additive optimization CLI: bounded tools and derived records, no model execution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from score_sw_fabric.optimization.common import OptimizationError, canonical, json_object
from score_sw_fabric.process_source.reader import InputError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="score-fabric optimization")
    commands = result.add_subparsers(dest="operation", required=True)
    evidence = commands.add_parser("evidence", help="bounded native evidence queries")
    evidence.add_argument("--root", type=Path, required=True)
    evidence.add_argument("--path", required=True)
    evidence.add_argument("--operation", dest="query_operation", default="summary")
    for field in ("rule", "file", "expected-sha256"):
        evidence.add_argument("--" + field)
    evidence.add_argument("--line", type=int)
    evidence.add_argument("--offset", type=int, default=0)
    evidence.add_argument("--limit", type=int, default=10)
    service = commands.add_parser("serve", help="bounded stdio context service")
    service.add_argument("--root", type=Path, required=True)
    service.add_argument("--state", type=Path, required=True)
    service.add_argument("--stage", default="bounded-tools")
    service.add_argument("--sources", type=Path)
    guard = commands.add_parser("guard", help="fail-closed native command hook")
    guard.add_argument("--decision", type=Path, required=True)
    guard.add_argument("--stage", required=True)
    guard.add_argument("--instruction", type=Path)
    guard.add_argument("--instruction-sha256")
    benchmark = commands.add_parser("benchmark", help="offline comparison; no provider calls")
    benchmark.add_argument("--output", type=Path, required=True)
    audit = commands.add_parser("audit", help="011 artifact consistency")
    audit.add_argument("--root", type=Path, default=Path.cwd())
    for name in ("prepare", "govern", "context", "mode", "classify", "skills"):
        command = commands.add_parser(name, help="derive a bounded " + name + " record")
        command.add_argument("--request", type=Path, required=True)
    return result


def _prepare(path: Path) -> dict[str, Any]:
    from score_sw_fabric.agents.models import json_file, load_request
    from score_sw_fabric.optimization.common import record
    from score_sw_fabric.optimization.context_manifest import manifest
    from score_sw_fabric.optimization.impact import impact
    from score_sw_fabric.optimization.task_classification import classify

    request, base = load_request(
        path,
        "optimization_prepare_request",
        {"task", "baseline", "before", "after", "mapping", "facts"},
    )
    _, _, before = json_file(base, request["before"], "/before")
    _, _, after = json_file(base, request["after"], "/after")
    changes = impact(before, after)
    scope = manifest(request["task"], request["baseline"], changes, after, request["mapping"])
    classification = classify(request["task"], request["facts"])
    return record(
        "optimization_preparation", impact=changes, manifest=scope, classification=classification
    )


def _request(operation: str, path: Path) -> dict[str, Any]:
    if operation == "prepare":
        return _prepare(path)
    if operation == "govern":
        from score_sw_fabric.agents.admission import admit_optimized

        return admit_optimized(path)[1]
    if operation == "context":
        from score_sw_fabric.agents.context import build_optimized_context

        return build_optimized_context(path)[1]
    from score_sw_fabric.agents.models import load_request

    if operation == "classify":
        from score_sw_fabric.optimization.task_classification import classify

        request, _ = load_request(path, "optimization_classification_request", {"task", "facts"})
        return classify(request["task"], request["facts"])
    if operation == "mode":
        from score_sw_fabric.optimization.workflow_modes import mode_plan

        request, _ = load_request(
            path, "optimization_mode_request", {"mode", "mandatory_checks", "human_gates"}
        )
        return mode_plan(request["mode"], request["mandatory_checks"], request["human_gates"])
    if operation == "skills":
        from score_sw_fabric.agents.models import local_dir, yaml_file
        from score_sw_fabric.optimization.skill_selection import registry, render, select

        request, base = load_request(
            path,
            "optimization_skills_request",
            {"root", "definitions", "activity", "baseline", "reference"},
        )
        root = local_dir(base, request["root"], "/root")
        _, _, definition = yaml_file(base, request["definitions"], "/definitions")
        registered = registry(root, definition["definitions"])
        selection = select(
            registered, request["activity"], definition["mapping"], request["baseline"]
        )
        return render(
            root, registered, selection, request["baseline"], reference=request["reference"]
        )
    raise OptimizationError("COMMAND_UNKNOWN")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.operation == "evidence":
            from score_sw_fabric.optimization.evidence_query import query

            output = query(
                args.root,
                args.path,
                operation=args.query_operation,
                rule=args.rule,
                file=args.file,
                line=args.line,
                offset=args.offset,
                limit=args.limit,
                expected_sha256=args.expected_sha256,
            )
        elif args.operation == "serve":
            from score_sw_fabric.optimization.server import BoundedService, serve

            sources = json_object(args.sources.read_bytes()) if args.sources else None
            serve(BoundedService(args.root, args.state, stage=args.stage, sources=sources))
            return 0
        elif args.operation == "guard":
            from score_sw_fabric.optimization.runtime_boundary import guard

            output = guard(
                json_object(sys.stdin.buffer.read(8192)),
                json_object(args.decision.read_bytes()),
                stage=args.stage,
                instruction=args.instruction,
                instruction_sha256=args.instruction_sha256,
                host_cwd=Path.cwd(),
            )
        elif args.operation == "benchmark":
            from score_sw_fabric.optimization.benchmark import run_benchmark

            output = run_benchmark(args.output)
        elif args.operation == "audit":
            from score_sw_fabric.optimization.audit import audit

            output = audit(args.root)
        else:
            output = _request(args.operation, args.request)
        print(canonical(output).decode())
        return 1 if output.get("decision") == "refused" or output.get("state") == "blocked" else 0
    except (InputError, OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        code = exc.code if isinstance(exc, InputError) else "INPUT_REJECTED"
        diagnostic = (
            {"decision": "block", "reason": str(code)}
            if args.operation == "guard"
            else {"kind": "optimization_diagnostic", "code": str(code)}
        )
        print(json.dumps(diagnostic, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
