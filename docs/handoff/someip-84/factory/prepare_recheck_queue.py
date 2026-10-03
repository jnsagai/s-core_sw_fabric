"""Prepare only the user-authorized missing/timed-out SOME/IP measurements."""

from __future__ import annotations

import argparse
import copy
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from obligations import CHECKS
from prepare import HERE, prepare, semantic_seal, sha, write
from queue_tools import freeze_tools
from repair_workflow import external_handoff_action

from score_sw_fabric.compiler.package import compile_request
from score_sw_fabric.runtime import supervision
from score_sw_fabric.storage import new_run_root, validate_run_root

# No passed commands or checks with already retained substantive findings are selected.
SELECTION = {
    "native_docs": {"docs": 1800},
    "native_traceability": {"traceability": 300},
    "format_precommit": {"format": 1800},
    "native_lint": {"clang-tidy": 1800},
    "native_performance": {"benchmarks": 1800, "profiling": 1800},
    "native_integration": {"qemu": 3600},
}


def public_git_bundle(root: Path, source_manifest: dict) -> None:
    """Acquire real public history; no reference checkout or private Git config is used."""
    repo = source_manifest["repository"]
    if repo != "eclipse-score/inc_someip_gateway":
        raise ValueError("Unexpected native Git source")
    directory = root / "git-acquisition"
    empty = root / "empty-git-template"
    empty.mkdir()
    home = root / "git-home"
    home.mkdir()
    scratch = root / "git-tmp"
    scratch.mkdir()
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "GIT_TERMINAL_PROMPT": "0",
        "TMPDIR": str(scratch),
    }
    git = ["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "-c", "credential.helper="]
    with (root / "git-acquisition.log").open("wb") as log:
        subprocess.run(
            [
                *git,
                "clone",
                "--no-checkout",
                "--template=" + str(empty),
                "https://github.com/" + repo,
                str(directory),
            ],
            env=env,
            stdout=log,
            stderr=log,
            check=True,
            timeout=180,
        )
        actual = subprocess.check_output(
            [*git, "rev-parse", source_manifest["commit"] + "^{tree}"],
            cwd=directory,
            env=env,
            text=True,
            timeout=15,
        ).strip()
        if actual != source_manifest["tree"]:
            raise ValueError("Public Git baseline tree differs from the frozen source manifest")
        bundle = root / "native-git-baseline.bundle"
        baseline_ref = "refs/heads/score-source-baseline"
        subprocess.run(
            [*git, "update-ref", baseline_ref, source_manifest["commit"]],
            cwd=directory,
            env=env,
            stdout=log,
            stderr=log,
            check=True,
            timeout=15,
        )
        subprocess.run(
            [*git, "bundle", "create", str(bundle), baseline_ref],
            cwd=directory,
            env=env,
            stdout=log,
            stderr=log,
            check=True,
            timeout=120,
        )
    write(
        root / "native-git-baseline.json",
        {
            "repository": repo,
            "commit": source_manifest["commit"],
            "tree": actual,
            "bundle_sha256": sha(bundle),
        },
    )


def prepare_recheck(previous: Path, image: str, root_prefix="score-someip84-recheck-") -> Path:
    previous = previous.resolve(strict=True)
    predecessor = previous.parent
    validate_run_root(predecessor)
    root = prepare(new_run_root(root_prefix))
    shutil.copytree(
        previous,
        root / "target",
        dirs_exist_ok=True,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git"),
    )
    freeze_tools(root)
    for name in (
        "collect_obligations.py",
        "evidence.py",
        "integration_evidence.py",
        "obligations.py",
        "queue_tools.py",
        "native_git.py",
        "overnight_hooks.py",
        "isolate_docker.py",
        "guard_agent_tools.py",
        "measure.py",
    ):
        shutil.copyfile(HERE / name, root / name)
    shutil.copyfile(Path(supervision.__file__), root / "supervision.py")
    source_manifest = json.loads((HERE.parent / "source-manifest.json").read_text())
    public_git_bundle(root, source_manifest)
    # Retain downloaded public archives, rather than copying mutable build outputs or Git hooks.
    repositories = predecessor / "bazel-cache/cache/repos"
    if repositories.is_dir():
        shutil.copytree(repositories, root / "bazel-cache/cache/repos", symlinks=True)
    write(
        root / "task-authority.json",
        {
            "instruction": (
                "Install cloud-localds, repair disposable Git metadata and rerun missing checks"
            ),
            "scope_correction": "be sure to not run everything again, just want is missing",
            "scope": "Deterministic selected missing/timed-out commands only; preserved source",
            "paid_calls": "none: no agent nodes",
            "engineering_review": "pending",
        },
    )
    mapping = yaml.safe_load((root / "execution_mapping.yaml").read_text())
    prototype, _, human = mapping["rules"][0]["actions"]
    origin = {
        "kind": "authorized_human_decision",
        "source_ref": {"path": "task-authority.json", "sha256": sha(root / "task-authority.json")},
        "pointer": "/scope",
        "decision_ref": "user-selected-missing-checks-20261003",
        "rationale": "User explicitly narrowed the rerun; engineering review remains unanswered",
    }
    actions, support, refs = [], [], []
    selected = {**SELECTION, "verification_report": {}}
    for check in selected:
        ref = "collect_" + check
        script = "commands/" + ref + ".sh"
        destination = "/workspace/.llm_tmp/overnight/obligations/" + check
        content = "cat " + shlex.quote(destination + "/result.json") + "\n"
        content += "grep -qx 0 " + shlex.quote(destination + "/collection-result") + "\n"
        action = copy.deepcopy(prototype)
        action.update(
            {
                "ref": ref,
                "label": ref,
                "type": "deterministic_check",
                "instance_ids": ["recheck-" + ref],
                "origin": origin,
                "purpose": (
                    "Collect only selected missing/timed-out results; collection is not acceptance"
                ),
                "command_file": script,
                "support_files": [script],
                "write_scope": [],
                "model_capability": "none",
                "expected_outputs": [destination + "/result.json"],
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
        refs.append(ref)
        support.append({"path": script, "content": content, "origin": origin})
    gate = copy.deepcopy(human)
    gate.update(
        {
            "ref": "review_stop",
            "label": "Selected rechecks collected; human review pending",
            "origin": origin,
            "instance_ids": ["recheck-review_stop"],
        }
    )
    gate, handoff = external_handoff_action(gate, origin)
    support.append(handoff)
    actions.append(gate)
    refs.append(gate["ref"])
    plan = json.loads((root / "plan.json").read_text())
    plan["change"] = {"id": "someip84-selected-recheck"}
    plan["semantic_inputs"] = {"task_authority": sha(root / "task-authority.json")}
    plan["instances"] = [
        {
            "instance_id": "recheck-" + ref,
            "applicability": "required",
            "effective_disposition": "create",
            "dependency_ids": [],
        }
        for ref in refs
    ]
    write(root / "plan.json", semantic_seal(plan))
    mapping["id"] = "someip84-selected-missing-measurements"
    mapping["review"]["reference"] = {**origin["source_ref"], "scope": "Operational rechecks only"}
    mapping["rules"][0].update({"actions": actions, "instance_ids": ["recheck-" + r for r in refs]})
    mapping["support_files"] = support
    mapping["edges"] = []
    chain = ["start", *refs, "exit"]
    for source, target in zip(chain, chain[1:], strict=False):
        outcomes = [None] if source == "start" else ["success", "failure"]
        for outcome in outcomes:
            mapping["edges"].append(
                {
                    "source": source,
                    "target": target,
                    "outcome": outcome,
                    "type": "failure" if outcome == "failure" else "success",
                    "condition": None,
                    "loop_id": None,
                    "origin": origin,
                }
            )
    (root / "execution_mapping.yaml").write_text(yaml.safe_dump(semantic_seal(mapping)))
    request = yaml.safe_load((root / "compile.yaml").read_text())
    for name, filename in (("plan", "plan.json"), ("execution_mapping", "execution_mapping.yaml")):
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
        path = root / "workflow" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    nodes = {}
    for node in package["manifest"]["ir"]["nodes"]:
        check = node["ref"].removeprefix("collect_")
        mode = "obligation:" + check if check in selected else None
        bounds = selected.get(check, {})
        allowance = sum(bounds.values()) + 240 if bounds else CHECKS.get(check, 5)
        nodes[node["id"]] = {
            "ref": node["ref"],
            "mode": mode,
            "write_paths": [],
            "repair_for": None,
            "timeout_seconds": allowance + node["budget"]["wall_time_seconds"] + 60,
            "collection_timeout_seconds": allowance,
            "command_timeouts": bounds,
            "selected_commands": list(bounds) if bounds else None,
        }
    write(
        root / "overnight-policy.json",
        {
            "image_id": image,
            "deadline_epoch": None,
            "deadline": None,
            "single_pass": True,
            "supervision_required": True,
            "source_write_paths": [],
            "nodes": nodes,
            "measurement_only": True,
            "recheck_selection": SELECTION,
        },
    )
    entrypoint = root / "workflow/workflow.toml"
    controls = (
        "\n[run.clone]\nenabled = false\n[run.run_branch]\nenabled = false\npush = false\n"
        '[run.environment.image]\ndocker = "score-someip84-agent:20261001"\n'
        "[run.environment.lifecycle]\npreserve = true\nstop_on_terminal = true\n"
        "[run.agent]\nfabro_tools = false\n"
    )
    controls += (
        '\n[[run.hooks]]\nid = "someip84-docker-isolation"\nevent = "sandbox_ready"\n'
        'blocking = true\nsandbox = false\ntimeout = "30s"\n'
        f'command = ["{sys.executable}", "{root / "isolate_docker.py"}", '
        f'"{image}", "{root / "target"}", "{root / "native-run-id"}"]\n'
    )
    for phase, event, bound in (
        ("guard", "pre_tool_use", 5),
        ("guard", "stage_start", 5),
        ("measure", "stage_start", 4200),
    ):
        controls += (
            f'\n[[run.hooks]]\nid = "recheck-{phase}-{event}"\nevent = "{event}"\n'
            f'blocking = true\nsandbox = false\ntimeout = "{bound}s"\n'
            f'command = ["{sys.executable}", "{root / "overnight_hooks.py"}", '
            f'"{root}", "{phase}"]\n'
        )
    entrypoint.write_text(entrypoint.read_text() + controls)
    write(
        root / "overnight-queue.json",
        {
            "status": "prepared_not_submitted",
            "run_id": None,
            "deadline": None,
            "single_pass": True,
            "all_obligations": True,
            "measurement_only": True,
            "selected_commands": SELECTION,
            "draft_tasks": 0,
            "measurement_tasks": len(selected),
            "engineering_acceptance": "pending",
            "predecessor_root": str(predecessor),
        },
    )
    dependencies = [
        "guard_agent_tools.py",
        "isolate_docker.py",
        "measure.py",
        "measurement-inputs.json",
        "storage.py",
        "workspace_transfer.py",
        "supervision.py",
        "collect_obligations.py",
        "evidence.py",
        "integration_evidence.py",
        "obligations.py",
        "queue_tools.py",
        "queue-tools.json",
        "native_git.py",
        "native-git-baseline.json",
        "native-git-baseline.bundle",
        "storage-selection.json",
    ]
    write(
        root / "overnight-overlay.json",
        {
            "compiled_package_sha256": sha(root / "out/package.json"),
            "workflow_sha256": sha(root / "workflow/workflow.fabro"),
            "entrypoint_sha256": sha(entrypoint),
            "policy_sha256": sha(root / "overnight-policy.json"),
            "hook_sha256": sha(root / "overnight_hooks.py"),
            "dependencies": {name: sha(root / name) for name in dependencies},
        },
    )
    write(
        root / "recheck-provenance.json",
        {
            "predecessor_root": str(predecessor),
            "preserved_source": str(previous),
            "selected_commands": SELECTION,
            "source_write_authority": "none",
            "engineering_acceptance": "pending",
        },
    )
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preserve-from", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    args = parser.parse_args()
    print(prepare_recheck(args.preserve_from, args.image_id), flush=True)


if __name__ == "__main__":
    main()
