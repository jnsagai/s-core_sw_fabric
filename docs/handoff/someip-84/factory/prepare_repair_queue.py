"""Prepare bounded same-run repairs and an external mandatory human review packet."""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from collect_obligations import source_identity
from evidence import archived_binding, seal_result
from prepare import BINARY, HERE, semantic_seal, sha, write
from prepare_recheck_queue import prepare_recheck
from repair_workflow import (
    MAX_REPAIRS,
    SELECTION,
    check_passed,
    current_pass,
    graph_parts,
    latest,
    passed,
)

from score_sw_fabric.compiler.ir import build_ir
from score_sw_fabric.compiler.mapping import project_mapping
from score_sw_fabric.compiler.package import compile_request
from score_sw_fabric.runtime import supervision


def prepare_repair(previous: Path, image: str, review_archive: Path | None = None) -> Path:
    root = prepare_recheck(previous, image, "score-someip84-repair-")
    prior_root = previous.resolve().parent
    reuse = {}
    hashes = source_identity(root / "target")
    if review_archive:
        expected_archive = "0ca374da71f04130ba5abf7e8937cdf8600b1056bd2eddf2c4e6e6ce4610aabd"
        anchor = root / "legacy-review-packet.tar.gz"
        shutil.copyfile(review_archive, anchor)
        for check in ("format_precommit", "compiler_diagnostics", "native_tests"):
            binding = archived_binding(anchor, expected_archive, check)
            result = json.loads(Path(binding["path"]).read_text())
            if not current_pass(result, hashes):
                raise ValueError("Archived passing evidence differs from repair candidate")
            reuse[check] = binding
    for check in (
        ()
        if review_archive
        else ("format_precommit", "compiler_diagnostics", "native_tests", "native_integration")
    ):
        try:
            path, result = latest(prior_root, check)
            if current_pass(result, hashes) and check_passed(prior_root, check):
                reuse[check] = {
                    "path": str(path),
                    "sha256": sha(path),
                    "evidence_files": result["evidence_files"],
                }
        except (OSError, ValueError):
            pass
    write(root / "reused-evidence.json", reuse)
    failures = {}
    for path in sorted(
        (prior_root / "obligation-results").glob("native_integration-*/result.json")
    ):
        result = json.loads(path.read_text())
        log = path.with_name("qemu.stdout")
        if (
            result.get("source_hashes") == hashes
            and not current_pass(result, hashes)
            and log.exists()
            and "Couldn't change to 'root' uid=0 gid=0: Operation not permitted" in log.read_text()
        ):
            failures["native_integration"] = {
                "path": str(path),
                "sha256": sha(path),
                "logs_sha256": {
                    str(p): sha(p) for p in [log, path.with_name("qemu.stderr")] if p.exists()
                },
                "purpose": "Prior measured failure triggers repair; does not count as readiness",
            }
            break
    write(root / "initial-failure-evidence.json", failures)
    if review_archive:
        review_directory = HERE / "runs/score-someip84-repair-bi5z3qb7"
        review = json.loads((review_directory / "agent-review.json").read_text())
        reproducer = json.loads((review_directory / "review-reproducer.json").read_text())
        if review["reviewed_archive_sha256"] != expected_archive or (
            reproducer["actual_wrapper_exit"] != 0 or reproducer["direct_workload_exit"] != -11
        ):
            raise ValueError("Review diagnostic differs from the reproduced profiler defect")
        write(
            root / "review-repairs.json",
            {
                "findings": [finding["id"] for finding in review["findings"]],
                "review_sha256": sha(review_directory / "agent-review.json"),
                "reproducer_sha256": sha(review_directory / "review-reproducer.json"),
                "archive_sha256": expected_archive,
                "fresh_native_checks": ["native_integration", "native_performance"],
                "reused_checks": list(reuse),
                "tool_regression_is_native_readiness": False,
            },
        )
        diagnostic = root / "review-diagnostic/native_performance"
        diagnostic.mkdir(parents=True)
        shutil.copyfile(
            review_directory / "review-reproducer.json",
            diagnostic / "reviewed-profiler-crash.stdout",
        )
        (diagnostic / "reviewed-profiler-crash.stderr").write_text(reproducer["diagnostic_tail"])
        command = {
            "label": "reviewed-profiler-crash",
            "exit_code": 1,
            "origin": "Previously measured SIGSEGV tool regression fails nonzero-exit predicate",
            "actual_wrapper_exit": 0,
            "expected_wrapper_exit": 139,
        }
        write(diagnostic / "reviewed-profiler-crash.command.json", command)
        result = {
            "check": "native_performance",
            "status": "findings_or_execution_failure",
            "commands": [command],
            "source_hashes": hashes,
            "review_diagnostic": "R1",
            "source_binding_role": "repair scope; tool regression is separate from native tests",
        }
        seal_result(diagnostic, result)
        write(diagnostic / "result.json", result)
        failures["native_performance"] = {
            "path": str(diagnostic / "result.json"),
            "sha256": sha(diagnostic / "result.json"),
        }
        # Retain the known native capture failure as diagnosis; do not repeat it.
        archived_packet = json.loads((review_directory / "review-packet.json").read_text())
        integration_origin = Path(
            archived_packet["evidence"]["native_integration"]["path"]
        ).parents[2]
        initial = json.loads((integration_origin / "initial-failure-evidence.json").read_text())
        failures["native_integration"] = initial["native_integration"]
        # A targeted correction may retain fresh case-validated integration and
        # repair only the new profiling failure, preserving both native runs.
        try:
            integration_path, integration_result = latest(prior_root, "native_integration")
            if current_pass(integration_result, hashes) and check_passed(
                prior_root, "native_integration"
            ):
                reuse["native_integration"] = {
                    "path": str(integration_path),
                    "sha256": sha(integration_path),
                    "evidence_files": integration_result["evidence_files"],
                }
                failures.pop("native_integration")
                performance_path, performance_result = latest(prior_root, "native_performance")
                if (
                    not passed(performance_result)
                    and performance_result.get("source_hashes") == hashes
                ):
                    failures["native_performance"] = {
                        "path": str(performance_path),
                        "sha256": sha(performance_path),
                    }
                write(root / "reused-evidence.json", reuse)
                correction = json.loads((root / "review-repairs.json").read_text())
                correction["fresh_native_checks"] = ["native_performance"]
                correction["reused_checks"] = list(reuse)
                write(root / "review-repairs.json", correction)
        except (OSError, ValueError):
            pass
        write(root / "initial-failure-evidence.json", failures)
    if "native_integration" in reuse:
        try:
            path, result = latest(prior_root, "native_performance")
            if result.get("source_hashes") == hashes and not current_pass(result, hashes):
                log = path.with_name("profiling.stdout")
                failures["native_performance"] = {
                    "path": str(path),
                    "sha256": sha(path),
                    "logs_sha256": {
                        str(p): sha(p)
                        for p in [log, path.with_name("profiling.stderr")]
                        if p.exists()
                    },
                    "purpose": "Prior measured profiling failure triggers same-run repair",
                }
        except (OSError, ValueError):
            pass
        write(root / "initial-failure-evidence.json", failures)
    build_root = prior_root
    inherited_build = prior_root / "build-workspace-binding.json"
    if inherited_build.exists():
        build_root = Path(json.loads(inherited_build.read_text())["root"])
    if reuse and (build_root / "native-workspace").is_dir():
        binding = json.loads((prior_root / "supervision-binding.json").read_text())
        prior_policy = supervision.read(Path(binding["policy"]))
        prior_native = supervision.native(prior_policy)
        if prior_native["lifecycle"]["status"]["kind"] not in {
            "failed",
            "succeeded",
        } or supervision.worker_alive(prior_policy):
            raise ValueError("Cannot reuse native outputs while their queue is active")
        if build_root != prior_root:
            storage_binding = json.loads((build_root / "supervision-binding.json").read_text())
            storage_policy = supervision.read(Path(storage_binding["policy"]))
            if supervision.worker_alive(storage_policy) or supervision.native(storage_policy)[
                "lifecycle"
            ]["status"]["kind"] not in {"failed", "succeeded"}:
                raise ValueError(
                    "Inherited native build workspace still belongs to an active queue"
                )
        if source_identity(build_root / "native-workspace") != hashes:
            raise ValueError("Reusable native build workspace differs from the candidate")
        write(
            root / "build-workspace-binding.json",
            {
                "root": str(build_root),
                "prior_run_id": prior_native["id"],
                "prior_worker_alive": False,
                "source_hashes": hashes,
                "mode": "reuse_stopped_disposable_build_outputs_no_queue_migration",
            },
        )
    prior_state = prior_root / "environment-repairs.json"
    if prior_state.exists() and json.loads(prior_state.read_text()).get("integration_path"):
        write(root / "environment-repairs.json", {"integration_path": True})
    from capture_tool import acquire

    acquire(root)
    authority = {
        "instruction": (
            "Human validation outside workflow, mandatory for closure; "
            "same-run repair loops and orchestrators; integration mandatory"
        ),
        "scope": (
            "Repair only remaining format, profiling and integration failures; "
            "recheck affected regressions"
        ),
        "source_write_authority": "Existing six candidate source paths only",
        "engineering_review": "pending_external_human_validation",
        "paid_calls": "none: deterministic orchestration",
    }
    write(root / "task-authority.json", authority)
    mapping = yaml.safe_load((root / "execution_mapping.yaml").read_text())
    prototype = mapping["rules"][0]["actions"][0]
    origin = copy.deepcopy(prototype["origin"])
    origin.update(
        {
            "source_ref": {
                "path": "task-authority.json",
                "sha256": sha(root / "task-authority.json"),
            },
            "pointer": "/scope",
            "decision_ref": "user-same-run-repair-20261003",
            "rationale": (
                "Explicit user workflow correction; acceptance requires external human validation"
            ),
        }
    )
    actions, edges, loops = graph_parts(prototype, origin)
    refs = [action["ref"] for action in actions]
    for action in actions:
        action["completion_predicate"] = (
            "Fresh checks pass; integration executed all six tests; external validation pending"
        )
        action["evidence_expectation"] = "Original tool outputs, attempt history and source hashes"
    mapping.update(
        {
            "id": "someip84-same-run-repair",
            "edges": edges,
            "loop_policies": loops,
            "support_files": [
                {
                    "path": action["command_file"],
                    "origin": origin,
                    "content": "cat /workspace/.llm_tmp/overnight/repair/"
                    + action["ref"]
                    + "/result.json\n"
                    + "grep -qx 0 /workspace/.llm_tmp/overnight/repair/"
                    + action["ref"]
                    + "/pass-result\n",
                }
                for action in actions
            ],
        }
    )
    mapping["rules"][0].update(
        {"actions": actions, "instance_ids": ["repair-" + ref for ref in refs]}
    )
    mapping["review"]["reference"] = {
        **origin["source_ref"],
        "scope": "User-authorized execution only; no human acceptance",
    }
    plan = json.loads((root / "plan.json").read_text())
    plan.update(
        {
            "change": {"id": "someip84-same-run-repair"},
            "semantic_inputs": {"task_authority": sha(root / "task-authority.json")},
            "instances": [
                {
                    "instance_id": "repair-" + ref,
                    "applicability": "required",
                    "effective_disposition": "create",
                    "dependency_ids": [],
                }
                for ref in refs
            ],
        }
    )
    write(root / "plan.json", semantic_seal(plan))
    profile = yaml.safe_load((root / "compiler_profile.yaml").read_text())
    profile["limits"]["action_budget"]["attempts"] = MAX_REPAIRS + 1
    graph = build_ir(project_mapping(plan, mapping, profile), mapping, profile)
    identifiers = {node["ref"]: node["id"] for node in graph["nodes"]}
    for loop in loops:
        loop["exhausted_destination"] = identifiers["unresolved_packet"]
    for name, value in (("execution_mapping.yaml", mapping), ("compiler_profile.yaml", profile)):
        (root / name).write_text(yaml.safe_dump(semantic_seal(value)))
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
    for name, content in package["files"].items():
        destination = root / "workflow" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
    source_paths = [
        "/workspace/score/socom/" + path
        for path in (
            "BUILD",
            "impl/service_identifier.cpp",
            "impl/service_identifier.hpp",
            "test/unit/BUILD",
            "test/unit/runtime_tests.cpp",
            "test/unit/service_identifier_tests.cpp",
        )
    ]
    nodes = {}
    for node in package["manifest"]["ir"]["nodes"]:
        ref = node["ref"]
        mode, allowance, bounds = None, 120, {}
        if ref == "orchestrate_scope":
            mode = "scope"
        elif ref.startswith("check_"):
            check = ref.removeprefix("check_")
            mode, bounds = "check:" + check, SELECTION[check]
            allowance = sum(bounds.values()) + 240
        elif ref.startswith("orchestrate_"):
            mode = "orchestrate:" + ref.removeprefix("orchestrate_")
        elif ref.startswith("repair_"):
            mode = "repair:" + ref.removeprefix("repair_")
        elif ref == "affected_regressions":
            mode, allowance = "regressions", 4800
        elif ref in {"external_review_packet", "unresolved_packet"}:
            mode = "packet" if ref == "external_review_packet" else "unresolved"
        nodes[node["id"]] = {
            "ref": ref,
            "mode": mode,
            "write_paths": [],
            "repair_for": None,
            "timeout_seconds": allowance + 180,
            "collection_timeout_seconds": allowance,
            "command_timeouts": bounds,
            "selected_commands": list(bounds) if bounds else None,
        }
    policy = {
        "image_id": image,
        "deadline_epoch": None,
        "deadline": None,
        "single_pass": True,
        "supervision_required": True,
        "source_write_paths": source_paths,
        "nodes": nodes,
        "measurement_only": True,
        "in_run_repair": True,
        "recheck_selection": SELECTION,
        "predecessor_root": str(previous.resolve().parent),
        "external_human_validation_required": True,
    }
    write(root / "overnight-policy.json", policy)
    for name in (
        "repair_workflow.py",
        "repair_hooks.py",
        "perf_bridge.py",
        "capture_tool.py",
        "qualify_perf.py",
    ):
        shutil.copyfile(HERE / name, root / name)
    shutil.copyfile(Path(supervision.__file__), root / "supervision.py")
    original_controls = root / "overnight-overlay.json"
    overlay = json.loads(original_controls.read_text())
    # Native-source overlays bind proven Fabro attributes: route each measured failure
    # immediately, and fail the run when the terminal blocked/packet command fails.
    workflow = root / "workflow/workflow.fabro"
    native_source = workflow.read_text()
    native_source = re.sub(r"max_retries=\d+", "max_retries=0", native_source)
    for ref in ("unresolved_packet", "external_review_packet"):
        prefix = "  " + identifiers[ref] + " ["
        lines = native_source.splitlines(keepends=True)
        native_source = "".join(
            line.replace('on_failure="route"', 'on_failure="exit"')
            if line.startswith(prefix)
            else line
            for line in lines
        )
    workflow.write_text(native_source)
    entrypoint = root / "workflow/workflow.toml"
    # The base configuration uses the same Docker/isolation contract as prior queues.
    config = "\n[run.clone]\nenabled = false\n[run.run_branch]\nenabled = false\npush = false\n"
    config += '[run.environment.image]\ndocker = "score-someip84-agent:20261001"\n'
    config += (
        "[run.environment.lifecycle]\npreserve = true\nstop_on_terminal = true\n"
        "[run.agent]\nfabro_tools = false\n"
    )
    config += (
        '\n[[run.hooks]]\nid = "repair-isolation"\nevent = "sandbox_ready"\n'
        'blocking = true\nsandbox = false\ntimeout = "30s"\n'
    )
    config += (
        f'command = ["{sys.executable}", "{root / "isolate_docker.py"}", "{image}", '
        f'"{root / "target"}", "{root / "native-run-id"}"]\n'
    )
    for phase, event, bound in (
        ("guard", "pre_tool_use", 5),
        ("guard", "stage_start", 5),
        ("measure", "stage_start", 6000),
    ):
        config += (
            f'\n[[run.hooks]]\nid = "repair-{phase}-{event}"\nevent = "{event}"\n'
            f'blocking = true\nsandbox = false\ntimeout = "{bound}s"\n'
        )
        config += (
            f'command = ["{sys.executable}", "{root / "repair_hooks.py"}", "{root}", "{phase}"]\n'
        )
    entrypoint.write_text(entrypoint.read_text() + config)
    with (
        (root / "repair-overlay-validation.stdout").open("w") as out,
        (root / "repair-overlay-validation.stderr").open("w") as err,
    ):
        subprocess.run(
            [str(BINARY), "--json", "validate", str(workflow)],
            stdout=out,
            stderr=err,
            check=True,
            timeout=30,
        )
    dependencies = {
        **overlay["dependencies"],
        **{
            name: sha(root / name)
            for name in (
                "repair_workflow.py",
                "repair_hooks.py",
                "perf_bridge.py",
                "capture_tool.py",
                "qualify_perf.py",
                "capture-inputs.json",
                "capture-link-inputs.json",
                "reused-evidence.json",
                "initial-failure-evidence.json",
                "supervision.py",
                "task-authority.json",
            )
        },
    }
    if (root / "build-workspace-binding.json").exists():
        dependencies["build-workspace-binding.json"] = sha(root / "build-workspace-binding.json")
    if review_archive:
        dependencies["review-repairs.json"] = sha(root / "review-repairs.json")
        dependencies["legacy-review-packet.tar.gz"] = sha(root / "legacy-review-packet.tar.gz")
    write(
        root / "overnight-overlay.json",
        {
            "compiled_package_sha256": sha(root / "out/package.json"),
            "workflow_sha256": sha(workflow),
            "entrypoint_sha256": sha(entrypoint),
            "policy_sha256": sha(root / "overnight-policy.json"),
            "hook_sha256": sha(root / "overnight_hooks.py"),
            "dependencies": dependencies,
            "native_attribute_overrides": {
                "all_command_max_retries": 0,
                "terminal_failure_policy": "exit",
            },
        },
    )
    queue = json.loads((root / "overnight-queue.json").read_text())
    queue.update(
        {
            "selected_commands": SELECTION,
            "in_run_repair": True,
            "external_human_validation_required": True,
            "measurement_tasks": len(SELECTION) + 2,
            "repair_attempts_per_check": MAX_REPAIRS,
        }
    )
    write(root / "overnight-queue.json", queue)
    write(
        root / "recheck-provenance.json",
        {
            "predecessor_root": policy["predecessor_root"],
            "preserved_source": str(previous.resolve()),
            "selected_commands": SELECTION,
            "source_write_authority": source_paths,
            "engineering_acceptance": "pending_external_human_validation",
        },
    )
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preserve-from", required=True, type=Path)
    parser.add_argument("--image-id", required=True)
    parser.add_argument(
        "--review-archive",
        type=Path,
        help="Original checksum-pinned packet; repair R1–R3 and reuse only unaffected checks",
    )
    args = parser.parse_args()
    print(prepare_repair(args.preserve_from, args.image_id, args.review_archive), flush=True)


if __name__ == "__main__":
    main()
