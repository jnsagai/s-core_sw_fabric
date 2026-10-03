"""Admit and start one prepared overnight queue on the existing isolated Fabro server."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from prepare import BINARY, sha, write
from queue_tools import validate_tools
from storage import validate_run_root
from supervise_overnight import SERVER, ensure_supervised

from score_sw_fabric.runtime.account_repair import account_status


def start_supervised(cli, root: Path, identifier: str) -> None:
    receipt = ensure_supervised(root)
    if receipt["run_id"] != identifier:
        raise ValueError("Supervisor readiness belongs to another native run")
    cli("overnight-start", ["start", identifier])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared_root", type=Path)
    args = parser.parse_args()
    root = args.prepared_root.resolve(strict=True)
    validate_run_root(root)
    queue = json.loads((root / "overnight-queue.json").read_bytes())
    if queue["status"] != "prepared_not_submitted":
        raise ValueError("Inspect existing native state before submitting this queue again")
    policy = json.loads((root / "overnight-policy.json").read_bytes())
    if policy.get("supervision_required") is not True:
        raise ValueError("Prepare the queue with mandatory infrastructure supervision")
    account_status()
    if policy["deadline_epoch"] is not None and time.time() + 1560 >= policy["deadline_epoch"]:
        raise ValueError("Too little time remains before the authorized overnight cutoff")
    overlay = json.loads((root / "overnight-overlay.json").read_bytes())
    for filename, key in (
        ("out/package.json", "compiled_package_sha256"),
        ("workflow/workflow.fabro", "workflow_sha256"),
        ("workflow/workflow.toml", "entrypoint_sha256"),
        ("overnight-policy.json", "policy_sha256"),
        ("overnight_hooks.py", "hook_sha256"),
    ):
        if sha(root / filename) != overlay[key]:
            raise ValueError("Prepared file changed: " + filename)
    for filename, expected in overlay["dependencies"].items():
        if sha(root / filename) != expected:
            raise ValueError("Prepared dependency changed: " + filename)
    if queue["all_obligations"]:
        validate_tools(root / "queue-tools.json")
    try:
        with socket.create_connection(("127.0.0.1", 43916), timeout=2):
            pass
    except PermissionError:
        raise SystemExit("Session denies Fabro socket access; no run submitted.") from None
    image = subprocess.check_output(
        ["docker", "image", "inspect", "score-someip84-agent:20261001", "--format", "{{.Id}}"],
        text=True,
        timeout=10,
    ).strip()
    if image != policy["image_id"]:
        raise ValueError("Live Docker image differs from the prepared identity")
    native = json.loads((root / "native-validation.json").read_bytes())
    if sha(BINARY) != native["validator"]["executable_sha256"]:
        raise ValueError("Fabro executable changed")
    server_root = SERVER
    env = dict(
        os.environ,
        HOME=str(server_root / "home"),
        FABRO_AUTH_FILE=str(server_root / "cli-auth.json"),
        FABRO_NO_UPGRADE_CHECK="true",
        FABRO_SERVER="http://127.0.0.1:43916",
    )

    def cli(label: str, command: list[str]) -> str:
        with (root / (label + ".stdout")).open("w") as stdout:
            with (root / (label + ".stderr")).open("w") as stderr:
                subprocess.run(
                    [str(BINARY), "--json", *command],
                    env=env,
                    cwd=root,
                    stdout=stdout,
                    stderr=stderr,
                    check=True,
                    timeout=120,
                )
        return (root / (label + ".stdout")).read_text()

    if queue.get("measurement_only"):
        package = json.loads((root / "out/package.json").read_bytes())
        if any(node["action_type"] == "agent" for node in package["manifest"]["ir"]["nodes"]):
            raise ValueError("Measurement-only queue contains an agent node")
        write(root / "model-smoke.json", {"status": "not_needed_no_agent_nodes"})
        if queue.get("in_run_repair"):
            # Resolve every frozen host hook dependency before native create/start.
            with (root / "hook-import-smoke.stdout").open("w") as out:
                with (root / "hook-import-smoke.stderr").open("w") as err:
                    subprocess.run(
                        [sys.executable, "-c", "import repair_hooks, repair_workflow, perf_bridge"],
                        cwd=root,
                        stdout=out,
                        stderr=err,
                        check=True,
                        timeout=30,
                    )
    else:
        check_model_tools(cli)
    cli(
        "overnight-preflight",
        [
            "preflight",
            str(root / "workflow/workflow.toml"),
            "--model",
            "deepseek-flash",
            "--provider",
            "deepseek",
            "--environment",
            # Preflight builds against the CLI's seeded catalogue. Create below
            # resolves the actual server-managed someip84 Docker environment.
            "default",
        ],
    )
    queue["status"] = "submission_attempted_inspect_native_state_before_retry"
    write(root / "overnight-queue.json", queue)
    native_run = json.loads(
        cli(
            "overnight-create",
            [
                "create",
                str(root / "workflow/workflow.toml"),
                "--target-from",
                str(root / "target"),
                "--model",
                "deepseek-flash",
                "--provider",
                "deepseek",
                "--environment",
                "someip84",
                "--label",
                "scope=someip84-overnight",
            ],
        )
    )
    queue.update({"status": "native_submitted", "run_id": native_run["run_id"]})
    write(root / "overnight-queue.json", queue)
    binding = root / "native-run-id"
    with binding.open("x") as stream:
        stream.write(native_run["run_id"] + "\n")
    # Bind ownership before sandbox startup, including when another queue uses this image.
    if policy["deadline_epoch"] is not None and time.time() + 1560 >= policy["deadline_epoch"]:
        raise ValueError("Run remains submitted; the overnight start window has closed")
    start_supervised(cli, root, native_run["run_id"])
    queue["status"] = "native_start_requested"
    queue["blocked_by"] = None
    write(root / "overnight-queue.json", queue)
    print(json.dumps({"run_id": native_run["run_id"], "deadline": queue["deadline"]}), flush=True)


def check_model_tools(cli) -> None:
    print("Checking DeepSeek Flash tools before submission.", flush=True)
    smoke = json.loads(
        cli(
            "flash-smoke",
            [
                "model",
                "test",
                "--provider",
                "deepseek",
                "--model",
                "deepseek-flash",
                "--reasoning-effort",
                "high",
                "--tools",
            ],
        )
    )
    if not (
        smoke["total"] == 1
        and smoke["failures"] == 0
        and smoke["skipped"] == 0
        and smoke["results"][0]["provider"] == "deepseek"
        and smoke["results"][0]["result"] == "pass"
    ):
        raise RuntimeError("Flash tool probe did not pass; no queue submitted")


if __name__ == "__main__":
    main()
