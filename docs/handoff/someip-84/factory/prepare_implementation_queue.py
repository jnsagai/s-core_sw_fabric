"""Compile a submitted-only SOME/IP implementation candidate for Fabro.

This prepares a disposable target and a closed package. It never starts a run,
loads a provider secret, or treats an agent result as engineering acceptance.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess

import yaml
from measure import verify_tree
from prepare import HERE, REPO, prepare, semantic_seal, sha, write

from score_sw_fabric.compiler.package import compile_request


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", choices=("deepseek", "codex"), default="deepseek")
    parser.add_argument(
        "--image-id",
        help="Previously recorded image SHA; live Docker identity must be checked before start",
    )
    args = parser.parse_args()
    codex = args.selection == "codex"
    provider = "openai-codex" if codex else "deepseek"
    model = "gpt-6.1-sol" if codex else "deepseek-flash"
    effort = "medium" if codex else "high"
    selection = "codex-selection.yaml" if codex else "deepseek-selection.yaml"
    root = prepare()
    handoff = HERE.parent
    source = REPO / ".tools/someip-84/baseline"
    manifest = json.loads((handoff / "source-manifest.json").read_bytes())
    verify_tree(source, manifest)
    target = root / "target"
    shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
    verify_tree(target, manifest)
    context = target / ".llm_tmp/context"
    context.mkdir(parents=True)
    for name in ("source-manifest.json", "issue-snapshot.json", "candidate-files.json"):
        shutil.copyfile(handoff / name, context / name)
    shutil.copyfile(HERE / "guard_agent_tools.py", root / "guard_agent_tools.py")
    shutil.copyfile(HERE / "isolate_docker.py", root / "isolate_docker.py")
    image_id = (
        args.image_id
        or subprocess.run(
            [
                "/usr/bin/docker",
                "image",
                "inspect",
                "score-someip84-agent:20261001",
                "--format",
                "{{.Id}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
    )
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("Disposable Docker image identity is unavailable")

    authority = {
        "scope": "Draft SOME/IP #84 registration-key implementation in a disposable copy",
        "user_direction": (
            "Use my Codex non API account with Sol 6.1 Medium as an alternative to Flash; continue"
            if codex
            else "Queue DeepSeek for SOME/IP; no budget limit, go"
        ),
        "model_selection": f"docs/handoff/someip-84/factory/{selection}",
        "engineering_review": "pending",
        "live_agent_admission": "requires runtime smoke, Docker boundary and host tool-hook checks",
        "paid_calls": (
            "ChatGPT account usage authorized; platform API billing and Pro are not selected"
            if codex
            else "authorized without a user spending cap"
        ),
        "provider": provider,
        "model": model,
        "reasoning_effort": effort,
        "fallbacks": [],
    }
    write(root / "task-authority.json", authority)
    origin = {
        "kind": "authorized_human_decision",
        "source_ref": {"path": "task-authority.json", "sha256": sha(root / "task-authority.json")},
        "pointer": "/scope",
        "decision_ref": f"user-go-{args.selection}-20261001",
        "rationale": "User authorized operational execution; native engineering review is pending.",
    }

    plan = json.loads((root / "plan.json").read_bytes())
    plan["change"] = {"id": "someip84-factory-implementation-queue"}
    plan["semantic_inputs"] = {"task_authority": sha(root / "task-authority.json")}
    names = ["local-agent-implementation", "local-review-stop"]
    plan["instances"] = [
        {
            "instance_id": name,
            "applicability": "required",
            "effective_disposition": "create",
            "dependency_ids": names[index - 1 : index],
        }
        for index, name in enumerate(names)
    ]
    write(root / "plan.json", semantic_seal(plan))

    mapping = yaml.safe_load((root / "execution_mapping.yaml").read_text())
    mapping["id"] = "someip84-operational-implementation-queue"
    mapping["review"]["reference"] = {
        **origin["source_ref"],
        "scope": "Authorized operational queue only; native mapping review pending",
    }
    mapping["rules"][0]["instance_ids"] = names
    _, agent, gate = mapping["rules"][0]["actions"]
    agent.pop("command_file")
    agent.update(
        {
            "ref": "implement",
            "purpose": (
                "Draft the focused SOME/IP #84 duplicate-server registration-key correction "
                "in this disposable source copy. Read .llm_tmp/context/issue-snapshot.json "
                "and the source context. Work only in the six paths named in "
                ".llm_tmp/context/candidate-files.json. Preserve notices. "
                "Use only read_file, grep, glob, and write_file tools. "
                "Read the issue snapshot and the directly relevant source, then draft "
                "the correction promptly. Limit exploratory reads; create the named test "
                "file if it is absent. Do not call shell or delegate. "
                "Do not use the existing external candidate patch as your implementation, "
                "claim engineering acceptance, publish, merge, or deploy. Report changed "
                "paths and unresolved validation; stop when the bounded draft is done."
            ),
            "type": "agent",
            "label": f"Draft SOME/IP correction with {model}",
            "instance_ids": [names[0]],
            "role": "developer_draft",
            "allowed_inputs": [
                "task-authority.json",
                "source-manifest.json",
                "issue-snapshot.json",
            ],
            "allowed_paths": ["/workspace"],
            "expected_outputs": ["draft source changes and agent result"],
            "data_destinations": [f"provider.{provider}"],
            "write_scope": [
                "/workspace/" + name
                for name in json.loads((handoff / "candidate-files.json").read_bytes())
            ],
            "tool_profile": "someip84-file-only-host-hook-v1",
            "model_capability": "bounded-agent-v1",
            "budget": {
                "wall_time_seconds": 14400,
                "attempts": 1,
                "tool_calls": 1000,
                "input_tokens": 1000000,
                "output_tokens": 32000,
                "cost_microunits": 100000000,
            },
            "completion_predicate": "Draft files and report available for validation",
            "evidence_expectation": "Agent output is an assertion until independent checks run",
            "fallible_outcomes": ["failure", "success"],
            "support_files": [],
            "origin": origin,
        }
    )
    gate.update(
        {
            "ref": "review_stop",
            "purpose": "Stop for external review; no engineering decision is collected here",
            "label": "Draft complete; external review required",
            "instance_ids": names,
            "role": "configuration_owner",
            "model_capability": "none",
            "completion_predicate": "External review remains pending",
            "origin": origin,
        }
    )
    mapping["rules"][0]["actions"] = [agent, gate]
    mapping["edges"] = [
        {
            "source": source_ref,
            "target": target_ref,
            "type": "failure" if outcome == "failure" else "success",
            "outcome": outcome,
            "condition": None,
            "loop_id": None,
            "origin": origin,
        }
        for source_ref, target_ref, outcome in (
            ("start", "implement", None),
            ("implement", "review_stop", "success"),
            ("implement", "review_stop", "failure"),
            ("review_stop", "exit", "success"),
        )
    ]
    mapping["support_files"] = []
    (root / "execution_mapping.yaml").write_text(
        yaml.safe_dump(semantic_seal(mapping), sort_keys=True)
    )

    request = yaml.safe_load((root / "compile.yaml").read_text())
    for name in ("plan", "execution_mapping"):
        path = root / ("plan.json" if name == "plan" else "execution_mapping.yaml")
        value = yaml.safe_load(path.read_text())
        request["inputs"][name] = {
            "path": path.name,
            "sha256": sha(path),
            "semantic_digest": value["digest"],
        }
    (root / "compile.yaml").write_text(yaml.safe_dump(request, sort_keys=True))
    package = compile_request(root / "compile.yaml", root / "out/package.json")
    write(root / "native-validation.json", package["native_validation"])
    native = root / "workflow"
    for name, content in package["files"].items():
        path = native / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    # Native run controls are an explicit operational overlay because the current
    # fabric compiler renders only the workflow graph and a minimal TOML entrypoint.
    entrypoint = native / "workflow.toml"
    entrypoint.write_text(
        entrypoint.read_text()
        + f'\n[run.model]\nprovider = "{provider}"\nname = "{model}"\n'
        + f'\n[run.model.fallbacks]\n"{model}" = []\n'
        + f'\n[run.model.controls]\nreasoning_effort = "{effort}"\n'
        + "\n[run.clone]\nenabled = false\n"
        + "\n[run.run_branch]\nenabled = false\npush = false\n"
        + '\n[run.environment.image]\ndocker = "score-someip84-agent:20261001"\n'
        + "\n[run.environment.lifecycle]\npreserve = true\nstop_on_terminal = true\n"
        + "\n[run.agent]\nfabro_tools = false\n"
        + '\n[[run.hooks]]\nid = "someip84-docker-isolation"\n'
        + 'event = "sandbox_ready"\nblocking = true\nsandbox = false\n'
        + 'timeout = "15s"\n'
        + (
            f'command = ["/usr/bin/python3", "{root / "isolate_docker.py"}", '
            f'"{image_id}", "{target}"]\n'
        )
        + '\n[[run.hooks]]\nid = "someip84-tool-boundary"\n'
        + 'event = "pre_tool_use"\nmatcher = ".*"\nblocking = true\n'
        + 'sandbox = false\ntimeout = "10s"\n'
        + f'command = ["/usr/bin/python3", "{root / "guard_agent_tools.py"}"]\n'
    )
    write(
        root / "operational-overlay.json",
        {
            "compiled_package_sha256": sha(root / "out/package.json"),
            "native_entrypoint_sha256": sha(entrypoint),
            "purpose": (
                f"{effort.capitalize()} reasoning with disposable 32768-event Petri capacity; "
                "Docker isolation, denied network and file-only hook"
            ),
            "tool_hook_sha256": sha(root / "guard_agent_tools.py"),
            "sandbox_hook_sha256": sha(root / "isolate_docker.py"),
            "docker_image_id": image_id,
            "image_identity_check": (
                "recorded_identity_only; live check required" if args.image_id else "live_inspect"
            ),
            "provider": provider,
            "model": model,
            "reasoning_effort": effort,
            "status": "pending_live_admission",
        },
    )
    print(root, flush=True)


if __name__ == "__main__":
    main()
