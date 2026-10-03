"""Measured predicates and bounded orchestration for same-run SOME/IP repairs."""

from __future__ import annotations

import copy
import json
import re
import time
from pathlib import Path

from evidence import verify_result
from integration_evidence import case_outcomes

SELECTION = {
    "format_precommit": {"format": 1800},
    "native_integration": {"qemu": 3600},
    "native_performance": {"profiling": 1800},
}
REPAIRS = {
    "format_precommit": "candidate_formatting",
    "native_performance": "scoped_perf_bridge",
    "native_integration": "bazel_action_environment",
}
MAX_REPAIRS = 3


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def external_handoff_action(gate: dict, origin: dict) -> tuple[dict, dict]:
    action = copy.deepcopy(gate)
    script = "commands/external_human_validation.sh"
    action.update(
        {
            "type": "deterministic_check",
            "label": "External human validation pending",
            "purpose": "Emit handoff; external human validation is mandatory for task closure",
            "role": "review_handoff",
            "origin": origin,
            "model_capability": "none",
            "command_file": script,
            "support_files": [script],
            "write_scope": [],
            "fallible_outcomes": ["success", "failure"],
            "completion_predicate": "Handoff emitted; task closure awaits external validation",
        }
    )
    return action, {
        "path": script,
        "origin": origin,
        "content": "printf 'task_closure=pending_external_human_validation\\n'\n",
    }


def passed(result: dict) -> bool:
    commands = result.get("commands", [])
    return (
        result.get("status") == "completed"
        and bool(commands)
        and all(c.get("exit_code") == 0 for c in commands)
    )


def current_pass(result: dict, hashes: dict) -> bool:
    return passed(result) and result.get("source_hashes") == hashes


def integration_passed(text: str) -> bool:
    return bool(re.search(r"Executed 6 out of 6 tests: 6 tests pass\.\s*(?:$|\n)", text))


def latest(root: Path, check: str) -> tuple[Path, dict]:
    paths = sorted((root / "obligation-results").glob(check + "-*/result.json"))
    if not paths:
        reuse = root / "reused-evidence.json"
        bindings = json.loads(reuse.read_text()) if reuse.exists() else {}
        failed = root / "initial-failure-evidence.json"
        if failed.exists():
            bindings.update(json.loads(failed.read_text()))
        if check not in bindings:
            raise ValueError("Missing measured result: " + check)
        import hashlib

        path = Path(bindings[check]["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != bindings[check]["sha256"]:
            raise ValueError("Reused evidence identity changed")
        for filename, expected in bindings[check].get("logs_sha256", {}).items():
            if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != expected:
                raise ValueError("Prior diagnostic identity changed")
        result = json.loads(path.read_text())
        verify_result(path, result, bindings[check])
        return path, result
    path = paths[-1]
    result = json.loads(path.read_text())
    verify_result(path, result)
    return path, result


def check_passed(root: Path, check: str) -> bool:
    path, result = latest(root, check)
    if not passed(result):
        return False
    if check == "native_integration":
        log = path.with_name("qemu.stdout")
        return log.exists() and case_outcomes(path.parent, result, log.read_text())["passed"]
    if check == "native_performance":
        log = path.with_name("profiling.stdout")
        if not log.exists():
            return False
        content = log.read_text()
        return bool(
            re.search(r"Executed 2 out of 2 tests: 2 tests pass\.\s*(?:$|\n)", content)
        ) and not re.search(r"\b[1-9][0-9]* skipped\b", content)
    return True


def diagnose(root: Path, check: str) -> dict:
    path, result = latest(root, check)
    if passed(result) and check != "native_integration":
        raise ValueError("Repair requires a current measured failure")
    history = root / "repair-history"
    history.mkdir(exist_ok=True)
    previous = sorted(history.glob(check + "-*.json"))
    attempt = len(previous) + 1
    if attempt > MAX_REPAIRS:
        raise ValueError("Same-run repair attempts exhausted: " + check)
    repair = REPAIRS[check]
    if check == "native_performance" and not result.get("review_diagnostic"):
        output = path.with_name("profiling.stdout")
        if (
            output.exists()
            and "echo_server.perf.data" in output.read_text()
            and "CalledProcessError" in output.read_text()
        ):
            repair = "native_echo_server_cleanup"
    if check == "native_integration":
        output = "\n".join(
            p.read_text(errors="replace")
            for p in (path.with_name("qemu.stdout"), path.with_name("qemu.stderr"))
            if p.exists()
        )
        if "Couldn't change to 'root' uid=0 gid=0: Operation not permitted" in output:
            repair = "namespace_capture_identity"
        elif "cloud-localds" in output and ("not found" in output or "No such file" in output):
            repair = "bazel_action_environment"
        else:
            raise ValueError("Integration failure needs a new scoped repair: " + str(path))
    if any(json.loads(p.read_text()).get("repair") == repair for p in previous):
        raise ValueError("Repair did not resolve the measured failure: " + repair)
    record = {
        "check": check,
        "attempt": attempt,
        "repair": repair,
        "failed_result": str(path),
        "source_hashes": result.get("source_hashes", {}),
        "commands": result.get("commands", []),
        "diagnosed_at": time.time(),
        "engineering_acceptance": "pending_external_human_validation",
    }
    write(history / (check + "-" + str(attempt) + ".json"), record)
    return record


def graph_parts(prototype: dict, origin: dict) -> tuple[list[dict], list[dict], list[dict]]:
    actions, edges, loops = [], [], []

    def action(ref: str, attempts=1):
        value = copy.deepcopy(prototype)
        value.update(
            {
                "ref": ref,
                "label": ref.replace("_", " "),
                "type": "deterministic_check",
                "instance_ids": ["repair-" + ref],
                "origin": origin,
                "purpose": (
                    "Same-run repair; external human validation is required for task closure"
                ),
                "command_file": "commands/" + ref + ".sh",
                "support_files": ["commands/" + ref + ".sh"],
                "write_scope": [],
                "model_capability": "none",
                "expected_outputs": ["host-measured result"],
                "fallible_outcomes": ["success", "failure"],
                "budget": {
                    "wall_time_seconds": 120,
                    "attempts": attempts,
                    "tool_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_microunits": 0,
                },
            }
        )
        actions.append(value)

    def edge(source: str, target: str, outcome=None, loop=None):
        edges.append(
            {
                "source": source,
                "target": target,
                "outcome": outcome,
                "type": "failure" if outcome == "failure" else "success",
                "condition": None,
                "loop_id": loop,
                "origin": origin,
            }
        )

    action("orchestrate_scope")
    edge("start", "orchestrate_scope")
    edge("orchestrate_scope", "check_format_precommit", "success")
    edge("orchestrate_scope", "unresolved_packet", "failure")
    checks = list(SELECTION)
    for index, check in enumerate(checks):
        action("check_" + check, MAX_REPAIRS + 1)
        action("orchestrate_" + check, MAX_REPAIRS + 1)
        action("repair_" + check, MAX_REPAIRS)
        target = (
            "check_" + checks[index + 1] if index + 1 < len(checks) else "external_review_packet"
        )
        if check == "format_precommit":
            target = "affected_regressions"
        edge("check_" + check, target, "success")
        edge("check_" + check, "orchestrate_" + check, "failure", check)
        edge("orchestrate_" + check, "repair_" + check, "success", check)
        edge("orchestrate_" + check, "unresolved_packet", "failure")
        edge("repair_" + check, "check_" + check, "success", check)
        edge("repair_" + check, "check_" + check, "failure", check)
        loops.append(
            {
                "id": check,
                "max_visits": MAX_REPAIRS + 1,
                "retry_target": "check_" + check,
                "exhausted_destination": "unresolved_packet",
                "origin": origin,
            }
        )
    action("affected_regressions")
    edge("affected_regressions", "check_native_integration", "success")
    edge("affected_regressions", "unresolved_packet", "failure")
    action("external_review_packet")
    action("unresolved_packet")
    for ref in ("external_review_packet", "unresolved_packet"):
        edge(ref, "exit", "success")
        edge(ref, "exit", "failure")
    return actions, edges, loops
