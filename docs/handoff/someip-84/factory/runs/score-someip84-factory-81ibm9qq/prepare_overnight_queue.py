"""Compile the user-authorized SOME/IP overnight queue without starting it."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from obligations import CHECKS as OBLIGATION_CHECKS
from obligations import SOURCES as OBLIGATION_SOURCES
from obligations import TASKS as OBLIGATION_TASKS
from prepare import HERE, semantic_seal, sha, write

from score_sw_fabric.compiler.ir import build_ir
from score_sw_fabric.compiler.mapping import project_mapping
from score_sw_fabric.compiler.package import compile_request

TASKS = [
    (
        "scope",
        (
            "Bind issue #84 to the verified baseline and list the accepted draft "
            "scope and open design questions."
        ),
        False,
    ),
    (
        "callsites",
        (
            "Map identifier construction, conversion, comparison and "
            "service-database call sites; cite real paths and lines."
        ),
        False,
    ),
    (
        "invariants",
        (
            "Derive the existing registration-key invariants from source; "
            "distinguish them from unaccepted public-interface proposals."
        ),
        False,
    ),
    (
        "reproducer",
        (
            "Create a focused failing regression for duplicate registration keys "
            "differing only in minor version."
        ),
        True,
    ),
    (
        "key_fix",
        (
            "Implement the smallest registration-key correction preserving "
            "interface representation and exact-major/minimum-minor rules."
        ),
        True,
    ),
    (
        "unit_matrix",
        (
            "Expand agent-authored tests over service IDs, instance IDs, major "
            "versions, minor boundaries and equality/ordering consistency."
        ),
        True,
    ),
    (
        "runtime_disabled",
        "Draft runtime tests for duplicate construction while both server instances are disabled.",
        True,
    ),
    (
        "runtime_enabled",
        (
            "Draft runtime tests for duplicates involving enabled servers; preserve "
            "genuine error results rather than assertions."
        ),
        True,
    ),
    (
        "lifetime_tests",
        (
            "Draft slot reuse and connector destruction tests, including changed "
            "minor versions and different major/instance slots."
        ),
        True,
    ),
    (
        "ordering_tests",
        (
            "Add property-style deterministic cases for strict weak ordering and "
            "equality of registration identifiers."
        ),
        True,
    ),
    (
        "conversion_tests",
        (
            "Add boundary coverage for identifier conversions while preserving "
            "existing public interface identity."
        ),
        True,
    ),
    (
        "compatibility",
        (
            "Review exact-major and minimum-minor compatibility against the changed "
            "key; identify untested paths and avoid changing discovery semantics."
        ),
        False,
    ),
    (
        "lifetime_review",
        (
            "Review source and drafted runtime cases for invalidation, connector "
            "lifetime and slot reuse; report concrete counterexamples."
        ),
        False,
    ),
    (
        "concurrency_review",
        (
            "Review registration and teardown ordering for concurrency assumptions, "
            "locking and assertions; propose tests without claiming safety "
            "acceptance."
        ),
        False,
    ),
    (
        "api_review",
        (
            "Review ABI/API effects and minor-version representation; retain future "
            "public identifier redesign as a human design question."
        ),
        False,
    ),
    (
        "test_metadata",
        (
            "Review native test conventions, metadata and verified requirement "
            "links; never invent native requirement identifiers."
        ),
        False,
    ),
    (
        "bazel_plan",
        (
            "Check BUILD changes and prepare the exact native Bazel validation plan "
            "from pinned repository configuration; mark unavailable execution "
            "pending."
        ),
        False,
    ),
    (
        "analyzer_plan",
        (
            "Review native analyzer configuration and the changed units; document "
            "tool/version/applicability gaps without claiming MISRA compliance."
        ),
        False,
    ),
    (
        "evidence_inventory",
        (
            "Reconcile all host measurements, changed source hashes, remaining "
            "full-runtime checks and unresolved findings; agent statements stay "
            "assertions."
        ),
        False,
    ),
    (
        "review_packet",
        (
            "Write the final review packet with changed paths, test outcomes, known "
            "limits and unanswered engineering decisions; never accept or publish."
        ),
        False,
    ),
]
CHECK_AFTER = {
    "unit_matrix": "plain",
    "lifetime_tests": "plain",
    "conversion_tests": "ubsan",
    "review_packet": "ubsan",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deadline", default="2026-10-02T07:00:00", help="Lisbon local time")
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--all-obligations", action="store_true")
    parser.add_argument("--preserve-from", type=Path)
    args = parser.parse_args()
    deadline = datetime.fromisoformat(args.deadline)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=ZoneInfo("Europe/Lisbon"))
    if deadline.timestamp() <= datetime.now().timestamp():
        raise ValueError("The overnight deadline has already passed")
    result = subprocess.run(
        [
            sys.executable,
            str(HERE / "prepare_implementation_queue.py"),
            "--selection",
            "deepseek",
            "--image-id",
            args.image_id,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    root = Path(result.stdout.strip().splitlines()[-1])
    if args.preserve_from:
        previous = args.preserve_from.resolve(strict=True)
        old_policy = json.loads((previous.parent / "overnight-policy.json").read_text())
        for path in old_policy["source_write_paths"]:
            relative = path.removeprefix("/workspace/")
            if (previous / relative).is_file():
                shutil.copyfile(previous / relative, root / "target" / relative)
        prior_reports = previous / ".llm_tmp/overnight/reports"
        if prior_reports.exists():
            shutil.copytree(prior_reports, root / "target/.llm_tmp/overnight/prior-reports")
    if args.all_obligations:
        context = root / "target/.llm_tmp/context/obligations"
        context.mkdir(parents=True)
        locations = json.loads(
            (HERE.parents[3] / "docs/discovery/reference-workspace.json").read_text()
        )["sources"]
        sources = []
        for name, (repository, commit, relative) in OBLIGATION_SOURCES.items():
            data = subprocess.check_output(
                ["git", "-C", locations[repository], "show", commit + ":" + relative]
            )
            path = context / (name + ".rst")
            path.write_bytes(data)
            sources.append(
                {
                    "id": name,
                    "repository": repository,
                    "commit": commit,
                    "path": relative,
                    "sha256": sha(path),
                    "native_acceptance": "not_inferred",
                }
            )
        write(context / "source-index.json", sources)
        write(
            context / "authority.json",
            {
                "instruction": (
                    "Abort the prior run; include all sourced obligations and additional "
                    "checks; restart unattended until 7 AM Lisbon"
                ),
                "human_reviews": "unanswered",
                "safety_class": "unknown",
                "engineering_acceptance": "pending",
                "codeql_scope": "Public Apache-2.0 eclipse-score/inc_someip_gateway; no upload",
            },
        )
    mapping = yaml.safe_load((root / "execution_mapping.yaml").read_text())
    prototype, gate = mapping["rules"][0]["actions"]
    authority = json.loads((root / "task-authority.json").read_bytes())
    authority.update(
        {
            "user_direction": (
                "Big SOME/IP #84 queue through 7 AM Lisbon; no limits for rework if needed"
            ),
            "deadline": deadline.isoformat(),
            "queue_rework_cap": None,
            "native_rework_ceiling": 500,
            "native_ceiling_reason": (
                "Pinned Petri attractor frontend MAX_FIRINGS; no lower rework cap added"
            ),
            "scope": (
                "Draft implementation, regression tests, measured focused validation "
                "and review drafts for SOME/IP #84 only"
            ),
            "all_obligations": args.all_obligations,
            "restart_authority": (
                "Owner explicitly requested abort, expansion and unattended restart"
            ),
        }
    )
    write(root / "task-authority.json", authority)
    origin = copy.deepcopy(prototype["origin"])
    origin["source_ref"]["sha256"] = sha(root / "task-authority.json")
    origin["decision_ref"] = "user-overnight-someip84-20261001"
    actions, support, stages, repairs = [], [], [], []
    collector_modes = {}
    extra_drafts = 0
    source_paths = prototype["write_scope"]
    prefix = "/workspace/.llm_tmp/overnight/reports/"
    base_prompt = (
        "Work on the bounded duplicate-server registration-key slice of SOME/IP #84. "
        "Read .llm_tmp/context/issue-snapshot.json and relevant source. "
        "Use only read_file, grep, glob and write_file; no shell, delegation, web, "
        "approval, publishing or engineering acceptance. Preserve notices. "
        "Read earlier .llm_tmp/overnight/reports and the latest host feedback under "
        ".llm_tmp/overnight/validation when relevant. Measurements are local, unprotected "
        "and scoped; full native runtime tests and human reviews remain pending. "
    )
    if args.all_obligations:
        base_prompt += (
            "Read the pinned process/platform sources in .llm_tmp/context/obligations, "
            "prior-reports, and .llm_tmp/overnight/obligations/*/result.json. "
            "A successful collection node means results were retained, not that checks passed. "
            "Do not treat missing tools, unknown applicability, incomplete extraction or "
            "unanswered human reviews as satisfied obligations. "
            "The cancelled draft has a measured GCC syntax failure: an extra closing brace "
            "in score/socom/impl/service_identifier.hpp at line 39. Inspect and correct "
            "the actual source before expanding tests; preserve the prior reports. "
        )

    def draft(ref: str, purpose: str, writable: bool, looping: bool = False) -> dict:
        action = copy.deepcopy(prototype)
        report = prefix + ref + ".md"
        action.update(
            {
                "ref": ref,
                "label": ref.replace("_", " "),
                "origin": origin,
                "instance_ids": ["overnight-" + ref],
                "purpose": base_prompt
                + purpose
                + " Write your report to "
                + report
                + ". "
                + (
                    "Only the six named candidate source paths and that report may be changed."
                    if writable
                    else "This is a review draft: only that report may be written."
                ),
                "write_scope": [report] + (source_paths if writable else []),
                "expected_outputs": [report],
                "role": "developer_draft" if writable else "review_draft",
                "tool_profile": "someip84-overnight-stage-path-hook-v1",
            }
        )
        action["budget"].update({"wall_time_seconds": 900, "attempts": 500 if looping else 1})
        return action

    tasks = list(TASKS)
    if args.all_obligations:
        # Finish all implementation/test edits before collecting the broad suite.
        metadata = next(item for item in tasks if item[0] == "test_metadata")
        tasks.remove(metadata)
        index = next(i for i, item in enumerate(tasks) if item[0] == "conversion_tests") + 1
        tasks.insert(
            index,
            (
                metadata[0],
                metadata[1]
                + (
                    " Add verified metadata to the six candidate files when "
                    "source-supported; missing identities stay explicit."
                ),
                True,
            ),
        )
        review_index = next(i for i, item in enumerate(tasks) if item[0] == "evidence_inventory")
        tasks[review_index:review_index] = OBLIGATION_TASKS

    def obligation_action(check: str, prefix: str = "collect_") -> None:
        ref = prefix + check
        collector_modes[ref] = "obligation:" + check
        action = copy.deepcopy(prototype)
        script_path = "commands/" + ref + ".sh"
        destination = "/workspace/.llm_tmp/overnight/obligations/" + check
        support.append(
            {
                "path": script_path,
                "content": "cat "
                + destination
                + "/result.json\ngrep -qx 0 "
                + destination
                + "/collection-result\n",
                "origin": origin,
            }
        )
        action.update(
            {
                "ref": ref,
                "type": "deterministic_check",
                "label": "Collect " + check,
                "instance_ids": ["overnight-" + ref],
                "role": "measurement_runner",
                "purpose": (
                    "Retain original fixed tool results, failures and blockers; successful "
                    "collection never implies verification or engineering acceptance"
                ),
                "model_capability": "none",
                "origin": origin,
                "command_file": script_path,
                "support_files": [script_path],
                "expected_outputs": [destination + "/result.json"],
                "write_scope": [],
                "tool_profile": "fixed-sourced-obligation-collector-v1",
                "data_destinations": ["local:disposable-target"],
                "budget": {
                    "wall_time_seconds": 120,
                    "attempts": 1,
                    "tool_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_microunits": 0,
                },
            }
        )
        actions.append(action)
        stages.append(ref)

    for ref, purpose, writable in tasks:
        actions.append(draft(ref, purpose, writable))
        stages.append(ref)
        if ref in CHECK_AFTER:
            check_ref = "check_" + ref
            action = copy.deepcopy(prototype)
            script_path = "commands/" + check_ref + ".sh"
            script = (
                "cat /workspace/.llm_tmp/overnight/validation/measurement.json\n"
                "grep -qx 0 /workspace/.llm_tmp/overnight/validation/check-result\n"
            )
            support.append({"path": script_path, "content": script, "origin": origin})
            action.update(
                {
                    "ref": check_ref,
                    "type": "deterministic_check",
                    "label": check_ref,
                    "instance_ids": ["overnight-" + check_ref],
                    "role": "measurement_runner",
                    "purpose": (
                        "Read fresh host-measured focused baseline/candidate GCC/GTest results; "
                        "never engineering acceptance"
                    ),
                    "model_capability": "none",
                    "origin": origin,
                    "command_file": script_path,
                    "support_files": [script_path],
                    "expected_outputs": [
                        "original command outputs, source hashes and focused test results"
                    ],
                    "write_scope": [],
                    "tool_profile": "fixed-host-gcc12-gtest-measurement",
                    "data_destinations": ["local:disposable-target"],
                    "budget": {
                        "wall_time_seconds": 120,
                        "attempts": 500,
                        "tool_calls": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cost_microunits": 0,
                    },
                }
            )
            actions.append(action)
            stages.append(check_ref)
            repair_ref = "repair_" + ref
            repairs.append((check_ref, repair_ref))
            actions.append(
                draft(
                    repair_ref,
                    "Correct the concrete compile/test findings in the latest host feedback. "
                    "Keep the correction within scope; explain any infrastructure blocker "
                    "instead of fabricating a pass.",
                    True,
                    True,
                )
            )
        if args.all_obligations and ref == "test_metadata":
            for check in OBLIGATION_CHECKS:
                if check not in {"verification_report", "rework_progress"}:
                    obligation_action(check)
            for repair_ref, purpose in (
                (
                    "tool_findings_repair",
                    "Correct concrete source defects reported by compiler, analyzers, "
                    "sanitizers, native tests and security tools. Read original diagnostics. "
                    "Do not suppress rules or fix dependencies/infrastructure outside the six "
                    "paths. Human deviations and unavailable tools remain blockers. If no safe "
                    "source correction is supported, explain the remaining findings in the report.",
                ),
                (
                    "coverage_tests_repair",
                    "Use actual line/branch coverage and native test results to add meaningful "
                    "missing regression/boundary tests within the six paths. Never pad coverage "
                    "or invent requirements. Class/tailoring selection remains human-owned; "
                    "report both platform goals and remaining gaps. Correct new source/test "
                    "failures where evidenced, otherwise record the blocker.",
                ),
            ):
                actions.append(draft(repair_ref, purpose, True, True))
                stages.append(repair_ref)
                extra_drafts += 1
            for check in OBLIGATION_CHECKS:
                if check not in {"verification_report", "rework_progress"}:
                    obligation_action(check, "recollect_")
            obligation_action("rework_progress")
            repairs.append(("collect_rework_progress", "tool_findings_repair"))
        if args.all_obligations and ref == "review_packet":
            obligation_action("verification_report")
    refs = [a["ref"] for a in actions]
    gate = copy.deepcopy(gate)
    gate.update(
        {
            "origin": origin,
            "instance_ids": ["overnight-" + ref for ref in refs],
            "label": "Overnight draft and measurements; human review pending",
        }
    )
    actions.append(gate)
    refs.append(gate["ref"])
    gate["instance_ids"].append("overnight-" + gate["ref"])
    plan = json.loads((root / "plan.json").read_bytes())
    plan["change"] = {"id": "someip84-overnight"}
    plan["semantic_inputs"] = {"task_authority": sha(root / "task-authority.json")}
    plan["instances"] = [
        {
            "instance_id": "overnight-" + ref,
            "applicability": "required",
            "effective_disposition": "create",
            "dependency_ids": [],
        }
        for ref in refs
    ]
    write(root / "plan.json", semantic_seal(plan))
    profile = yaml.safe_load((root / "compiler_profile.yaml").read_text())
    profile["limits"]["action_budget"]["attempts"] = 500
    (root / "compiler_profile.yaml").write_text(yaml.safe_dump(semantic_seal(profile)))
    mapping["id"] = "someip84-overnight-operational-queue"
    mapping["review"]["reference"] = {
        **origin["source_ref"],
        "scope": "User-authorized overnight operational queue; engineering review pending",
    }
    mapping["rules"][0].update(
        {"actions": actions, "instance_ids": ["overnight-" + ref for ref in refs]}
    )
    mapping["support_files"] = support

    def edge(source: str, target: str, outcome=None, loop=None) -> dict:
        return {
            "source": source,
            "target": target,
            "outcome": outcome,
            "type": "failure" if outcome == "failure" else "success",
            "condition": None,
            "loop_id": loop,
            "origin": origin,
        }

    mapping["edges"] = [edge("start", stages[0])]
    repair_map = dict(repairs)
    for index, ref in enumerate(stages):
        target = stages[index + 1] if index + 1 < len(stages) else gate["ref"]
        mapping["edges"].append(edge(ref, target, "success"))
        mapping["edges"].append(
            edge(
                ref,
                repair_map.get(ref, target if args.all_obligations else gate["ref"]),
                "failure",
                ref if ref in repair_map else None,
            )
        )
    for check, repair in repairs:
        if check == "collect_rework_progress":
            # Both repair agents and fresh collectors are already in the stage chain.
            continue
        next_stage = stages[stages.index(check) + 1]
        mapping["edges"].extend(
            [
                edge(repair, check, "success", check),
                edge(repair, next_stage if args.all_obligations else gate["ref"], "failure"),
            ]
        )
    mapping["edges"].append(edge(gate["ref"], "exit", "success"))
    graph = build_ir(project_mapping(plan, mapping, profile), mapping, profile)
    gate_id = next(n["id"] for n in graph["nodes"] if n["ref"] == gate["ref"])
    mapping["loop_policies"] = [
        {
            "id": check,
            "max_visits": 500,
            "retry_target": check,
            "exhausted_destination": gate_id,
            "origin": origin,
        }
        for check, _ in repairs
    ]
    (root / "execution_mapping.yaml").write_text(yaml.safe_dump(semantic_seal(mapping)))
    request = yaml.safe_load((root / "compile.yaml").read_text())
    for name, filename in (
        ("plan", "plan.json"),
        ("execution_mapping", "execution_mapping.yaml"),
        ("compiler_profile", "compiler_profile.yaml"),
    ):
        value = yaml.safe_load((root / filename).read_text())
        request["inputs"][name] = {
            "path": filename,
            "sha256": sha(root / filename),
            "semantic_digest": value["digest"],
        }
    (root / "compile.yaml").write_text(yaml.safe_dump(request))
    package = compile_request(root / "compile.yaml", root / "out/package.json")
    write(root / "native-validation.json", package["native_validation"])
    old_controls = (root / "workflow/workflow.toml").read_text().split("[run.model]", 1)[1]
    for name, content in package["files"].items():
        path = root / "workflow" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    graph_path = root / "workflow/workflow.fabro"
    graph_path.write_text(
        graph_path.read_text()
        .replace("max_node_visits=20", "max_node_visits=500")
        .replace("max_retries=499", "max_retries=0")
    )
    entrypoint = root / "workflow/workflow.toml"
    old_controls = old_controls.split('[[run.hooks]]\nid = "someip84-tool-boundary"')[0]
    old_controls = old_controls.replace(
        f'"{root / "target"}"]',
        f'"{root / "target"}", "{root / "native-run-id"}"]',
    )
    entrypoint.write_text(entrypoint.read_text() + "\n[run.model]" + old_controls)
    shutil.copyfile(HERE / "overnight_hooks.py", root / "overnight_hooks.py")
    shutil.copyfile(HERE / "measure.py", root / "measure.py")
    if args.all_obligations:
        for filename in ("collect_obligations.py", "obligations.py"):
            shutil.copyfile(HERE / filename, root / filename)
    for event in ("stage_start", "pre_tool_use"):
        with entrypoint.open("a") as stream:
            stream.write(
                f'\n[[run.hooks]]\nid = "overnight-{event}"\nevent = "{event}"\n'
                'blocking = true\nsandbox = false\ntimeout = "5s"\n'
                f'command = ["{sys.executable}", "{root / "overnight_hooks.py"}", '
                f'"{root}", "guard"]\n'
            )
    nodes = {}
    for node in package["manifest"]["ir"]["nodes"]:
        mode = (
            CHECK_AFTER.get(node["ref"].removeprefix("check_"))
            if node["ref"].startswith("check_")
            else None
        )
        if node["ref"] in collector_modes:
            mode = collector_modes[node["ref"]]
        allowance = (
            OBLIGATION_CHECKS[mode.removeprefix("obligation:")] + 60
            if mode and mode.startswith("obligation:")
            else 605
            if mode
            else 5
        )
        nodes[node["id"]] = {
            "ref": node["ref"],
            "timeout_seconds": node["budget"]["wall_time_seconds"] + allowance,
            "write_paths": node["write_scope"],
            "mode": mode,
            "repair_for": (
                "check_" + node["ref"].removeprefix("repair_")
                if node["ref"].startswith("repair_")
                else None
            ),
        }
    check_ids = [identifier for identifier, node in nodes.items() if node["mode"]]
    matcher = "^(" + "|".join(check_ids) + ")$"
    with entrypoint.open("a") as stream:
        stream.write(
            '\n[[run.hooks]]\nid = "overnight-host-measurement"\nevent = "stage_start"\n'
            f'matcher = "{matcher}"\nblocking = true\nsandbox = false\n'
            f'timeout = "{960 if args.all_obligations else 600}s"\n'
            f'command = ["{sys.executable}", "{root / "overnight_hooks.py"}", '
            f'"{root}", "measure"]\n'
        )
    write(
        root / "overnight-policy.json",
        {
            "deadline_epoch": deadline.timestamp(),
            "deadline": deadline.isoformat(),
            "image_id": args.image_id,
            "source_write_paths": source_paths,
            "nodes": nodes,
        },
    )
    reports = root / "target/.llm_tmp/overnight/reports"
    reports.mkdir(parents=True)
    queue = {
        "status": "prepared_not_submitted",
        "run_id": None,
        "scope": "SOME/IP #84",
        "deadline": deadline.isoformat(),
        "model": "deepseek-flash",
        "reasoning_effort": "high",
        "draft_tasks": len(tasks) + extra_drafts,
        "measurement_tasks": len(CHECK_AFTER) + len(collector_modes),
        "all_obligations": args.all_obligations,
        "conditional_rework_tasks": len(repairs) - (1 if args.all_obligations else 0),
        "obligation_rework": (
            "Two repair agents; remeasure changed source, reuse only matching source/tool "
            "identities; repeat while repairs change source, stop with unresolved blockers "
            "when a round makes no source progress. Native 500 visits and deadline apply."
            if args.all_obligations
            else None
        ),
        "work_items": stages,
        "rework": "No additional queue cap; native hard ceiling 500 visits per loop node",
        "blocked_by": "Pending live admission and native start",
        "native_runtime_overlay": {
            "max_node_visits": 500,
            "per_visit_auto_retries": 0,
            "reason": "Match sourced native loop ceiling; rework returns through measured checks",
        },
        "engineering_acceptance": "pending",
        "live_deadline_and_hooks": "not_verified",
    }
    write(root / "overnight-queue.json", queue)
    write(
        root / "overnight-overlay.json",
        {
            "compiled_package_sha256": sha(root / "out/package.json"),
            "workflow_sha256": sha(graph_path),
            "entrypoint_sha256": sha(entrypoint),
            "policy_sha256": sha(root / "overnight-policy.json"),
            "hook_sha256": sha(root / "overnight_hooks.py"),
            "dependencies": {
                name: sha(root / name)
                for name in (
                    "guard_agent_tools.py",
                    "isolate_docker.py",
                    "measure.py",
                    "measurement-inputs.json",
                )
                + (("collect_obligations.py", "obligations.py") if args.all_obligations else ())
            },
        },
    )
    print(root, flush=True)


if __name__ == "__main__":
    main()
