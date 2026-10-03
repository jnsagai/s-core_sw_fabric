"""Trusted host handlers invoked by Fabro's bounded repair graph."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from collect_obligations import FORMAT, collect, snapshot, source_identity
from isolate_docker import docker
from measure import digest
from repair_workflow import SELECTION, check_passed, current_pass, diagnose, latest, write
from storage import validate_run_root


def owned(root: Path, policy: dict) -> str:
    run = (root / "native-run-id").read_text().strip()
    ids = docker("ps", "--filter", "label=petri.run=" + run, "--format", "{{.ID}}").split()
    if len(ids) != 1:
        raise ValueError("Same-run repair requires exactly one owned container")
    record = json.loads(docker("inspect", ids[0]))[0]
    if record["Image"] != policy["image_id"] or record["NetworkSettings"]["Networks"]:
        raise ValueError("Same-run repair container image/network differs")
    return ids[0]


def feedback(root: Path, policy: dict, ref: str, record: dict, success: bool) -> None:
    out = root / "repair-feedback" / (ref + "-" + str(time.time_ns()))
    out.mkdir(parents=True)
    write(out / "result.json", record)
    (out / "pass-result").write_text("0\n" if success else "1\n")
    destination = "/workspace/.llm_tmp/overnight/repair/" + ref
    from score_sw_fabric.optimization.collector_summary import collector_summary
    from score_sw_fabric.optimization.common import canonical

    agent_feedback = out / "agent-feedback"
    agent_feedback.mkdir()
    (agent_feedback / "summary.json").write_bytes(canonical(collector_summary(record, out)) + b"\n")
    shutil.copyfile(out / "pass-result", agent_feedback / "pass-result")
    container = owned(root, policy)
    docker("exec", container, "mkdir", "-p", destination)
    docker("cp", str(agent_feedback) + "/.", container + ":" + destination + "/")


def repair(root: Path, policy: dict, check: str) -> dict:
    history = sorted((root / "repair-history").glob(check + "-*.json"))
    if not history:
        raise ValueError("Repair lacks a measured orchestration decision")
    decision = json.loads(history[-1].read_text())
    state_path = root / "environment-repairs.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if check == "format_precommit":
        container = owned(root, policy)
        scratch = root / "format-repairs" / str(time.time_ns())
        scratch.mkdir(parents=True)
        changes = []
        for path in policy["source_write_paths"]:
            if not path.endswith((".cpp", ".hpp")):
                continue
            target = scratch / Path(path).name
            docker("cp", container + ":" + path, str(target))
            before = digest(target)
            subprocess.run(
                [FORMAT, "-style=file:" + str(root / "target/.clang-format"), "-i", str(target)],
                check=True,
                timeout=60,
            )
            after = digest(target)
            if before != after:
                docker("cp", str(target), container + ":" + path)
                changes.append({"path": path, "before_sha256": before, "after_sha256": after})
        decision["changes"] = changes
    elif check == "native_integration":
        if decision["repair"] == "namespace_capture_identity":
            from capture_tool import build

            build(root)
            state["capture_identity"] = True
        else:
            state["integration_path"] = True
    elif check == "native_performance":
        from perf_bridge import provision

        provision(root, policy["image_id"])
        state["profiling_bridge"] = True
    else:
        raise ValueError("No authorized deterministic repair for " + check)
    write(state_path, state)
    decision["repair_completed_at"] = time.time()
    write(history[-1], decision)
    return decision


def packet(root: Path, policy: dict, unresolved=False) -> dict:
    out = root / "external-review"
    out.mkdir(exist_ok=True)
    # A fresh owned snapshot binds every current candidate file and mandatory result.
    capture = out / ("capture-" + str(time.time_ns()))
    capture.mkdir()
    source, container = snapshot(root, policy, capture)
    hashes = source_identity(source)
    evidence = {}
    complete = not unresolved
    for check in [*SELECTION, "compiler_diagnostics", "native_tests"]:
        try:
            path, result = latest(root, check)
            valid = current_pass(result, hashes) and check_passed(root, check)
            evidence[check] = {"path": str(path), "sha256": digest(path), "current_pass": valid}
            complete = complete and valid
            shutil.copyfile(path, out / (check + "-result.json"))
            logs = out / "evidence" / check
            logs.mkdir(parents=True, exist_ok=True)
            retained = {}
            for log in path.parent.iterdir():
                if log.is_file() and log.suffix in {".stdout", ".stderr", ".json"}:
                    destination = logs / log.name
                    shutil.copyfile(log, destination)
                    retained[str(destination.relative_to(out))] = digest(destination)
            for name, expected in result.get("native_artifacts", {}).items():
                original = path.parent / name
                if not original.resolve().is_relative_to(path.parent.resolve()):
                    raise ValueError("Native artifact escapes measured result directory")
                if digest(original) != expected:
                    raise ValueError("Native artifact identity changed")
                destination = logs / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, destination)
                retained[str(destination.relative_to(out))] = digest(destination)
            if check == "native_integration":
                origin = path.parents[2]
                manifest = origin / "capture-tool.json"
                if manifest.exists():
                    tool = json.loads(manifest.read_text())
                    binary = Path(tool["path"]).resolve(strict=True)
                    if not binary.is_relative_to(origin) or digest(binary) != tool["sha256"]:
                        raise ValueError("Original integration capture tool identity changed")
                    provenance = logs / "capture-tool"
                    provenance.mkdir(exist_ok=True)
                    for name in (
                        "capture-tool.json",
                        "capture-identity.patch",
                        "capture-inputs.json",
                    ):
                        shutil.copyfile(origin / name, provenance / name)
                    shutil.copyfile(binary, provenance / "tcpdump")
                    inputs = json.loads((origin / "capture-inputs.json").read_text())
                    for name, expected in inputs["identities"].items():
                        if digest(origin / "capture-inputs" / name) != expected:
                            raise ValueError("Original capture source or license changed")
                    with tarfile.open(provenance / "original-inputs.tar.gz", "w:gz") as archive:
                        archive.add(
                            origin / "capture-inputs",
                            arcname="capture-inputs",
                            filter=lambda member: (
                                None if ".git" in Path(member.name).parts else member
                            ),
                        )
                    retained.update(
                        {
                            str(p.relative_to(out)): digest(p)
                            for p in provenance.rglob("*")
                            if p.is_file()
                        }
                    )
            evidence[check]["portable_evidence"] = retained
        except (OSError, ValueError):
            evidence[check] = {"current_pass": False, "reason": "Missing mandatory result"}
            complete = False
    record = {
        "run_id": (root / "native-run-id").read_text().strip(),
        "technical_completion": "complete" if complete else "blocked",
        "task_closure": "pending_external_human_validation",
        "human_validation": {"required": True, "location": "outside_fabro", "status": "pending"},
        "source_hashes": hashes,
        "candidate_directory": str(source.relative_to(out)),
        "evidence": evidence,
        "prior_evidence": policy["predecessor_root"],
        "engineering_acceptance": "pending",
        "published": False,
    }
    for name in (
        "capture-tool.json",
        "capture-identity.patch",
        "perf-bridge.json",
        "reused-evidence.json",
        "legacy-review-packet.tar.gz",
        "review-repairs.json",
        "initial-failure-evidence.json",
    ):
        if (root / name).exists():
            shutil.copyfile(root / name, out / name)
    if (root / "profiler-signal-regression").is_dir():
        shutil.copytree(
            root / "profiler-signal-regression",
            out / "profiler-signal-regression",
            dirs_exist_ok=True,
        )
    if (root / "review-diagnostic").is_dir():
        shutil.copytree(root / "review-diagnostic", out / "review-diagnostic", dirs_exist_ok=True)
    if (root / "repair-history").exists():
        shutil.copytree(root / "repair-history", out / "repair-history", dirs_exist_ok=True)
    write(out / "review-packet.json", record)
    return record


def main() -> int:
    root = Path(sys.argv[1]).resolve(strict=True)
    phase = sys.argv[2]
    if phase == "guard":
        from overnight_hooks import main as guard

        return guard()
    validate_run_root(root)
    policy = json.loads((root / "overnight-policy.json").read_text())
    from supervision import require_ready

    binding = json.loads((root / "supervision-binding.json").read_text())
    require_ready(
        Path(binding["policy"]), expected_run_id=(root / "native-run-id").read_text().strip()
    )
    context = json.load(sys.stdin)
    node = policy["nodes"][context["node_id"]]
    mode = node.get("mode")
    if not mode or context["event"] != "stage_start":
        return 0
    ref = node["ref"]
    record, success = {}, False
    try:
        if mode.startswith("check:"):
            check = mode.removeprefix("check:")
            failed_path = root / "initial-failure-evidence.json"
            failed = json.loads(failed_path.read_text()) if failed_path.exists() else {}
            reuse = (
                json.loads((root / "reused-evidence.json").read_text())
                if (root / "reused-evidence.json").exists()
                else {}
            )
            initial_failure = check in failed and not any(
                (root / "repair-history").glob(check + "-*.json")
            )
            if check in reuse or initial_failure:
                capture = root / ("reuse-source-" + str(time.time_ns()))
                capture.mkdir()
                source, _ = snapshot(root, policy, capture)
                _, prior = latest(root, check)
                if prior.get("source_hashes") != source_identity(source) or (
                    not initial_failure and not current_pass(prior, source_identity(source))
                ):
                    raise ValueError("Source differs from reused evidence")
            else:
                collect(root, policy, {**node, "mode": "obligation:" + check})
            _, record = latest(root, check)
            success = check_passed(root, check)
        elif mode.startswith("orchestrate:"):
            record = diagnose(root, mode.removeprefix("orchestrate:"))
            success = True
        elif mode.startswith("repair:"):
            record = repair(root, policy, mode.removeprefix("repair:"))
            success = True
        elif mode == "scope":
            record = {
                "selected": SELECTION,
                "integration_mandatory": True,
                "repair_execution": "same_native_run",
                "external_human_validation": "required_for_task_closure",
            }
            success = True
        elif mode == "regressions":
            records = []
            for check, bounds in (("compiler_diagnostics", {}), ("native_tests", {"tests": 1800})):
                reuse = (
                    json.loads((root / "reused-evidence.json").read_text())
                    if (root / "reused-evidence.json").exists()
                    else {}
                )
                if check in reuse:
                    capture = root / ("reuse-source-" + str(time.time_ns()))
                    capture.mkdir()
                    source, _ = snapshot(root, policy, capture)
                    _, prior = latest(root, check)
                    if not current_pass(prior, source_identity(source)):
                        raise ValueError("Source differs from reused evidence")
                else:
                    collect(
                        root,
                        policy,
                        {
                            **node,
                            "mode": "obligation:" + check,
                            "collection_timeout_seconds": 2400,
                            "command_timeouts": bounds,
                            "selected_commands": list(bounds) if bounds else None,
                        },
                    )
                _, item = latest(root, check)
                records.append(item)
            record = {"results": records}
            success = all(check_passed(root, c) for c in ("compiler_diagnostics", "native_tests"))
        elif mode in {"packet", "unresolved"}:
            record = packet(root, policy, mode == "unresolved")
            success = record["technical_completion"] == "complete"
        else:
            raise ValueError("Unknown repair handler mode")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        record = {"status": "blocked", "reason": type(error).__name__, "detail": str(error)[:4096]}
    feedback(root, policy, ref, record, success)
    if mode in {"packet", "unresolved"} and not success:
        return 2  # A blocking native hook prevents explicit exit edges hiding failure.
    return 0  # Fabro's command result, rather than collection, owns routing.


if __name__ == "__main__":
    raise SystemExit(main())
