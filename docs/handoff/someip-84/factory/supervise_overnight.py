"""Bind a mandatory, independently restarted repair observer to one native run."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from prepare import BINARY, HERE, REPO

from score_sw_fabric.runtime import supervision
from score_sw_fabric.runtime.account_repair import account_status
from score_sw_fabric.storage import private_server_root, validate_run_root

SERVER = Path("/home/jefferson/.local/state/s-core/fabro/someip84-server")


def ensure_supervised(root: Path) -> dict:
    validate_run_root(root)
    identifier = (root / "native-run-id").read_text().strip()
    binding = root / "supervision-binding.json"
    if binding.exists():
        previous = supervision.read(binding)
        policy = Path(previous["policy"])
        receipt = supervision.require_ready(policy, expected_run_id=identifier)
        if supervision.read(policy)["prepared_root"] != str(root):
            raise ValueError("Supervisor workspace binding differs")
        return receipt
    account_status()
    directory = private_server_root(root, "supervision")
    observer = directory / "observer.py"
    shutil.copyfile(Path(supervision.__file__), observer)
    queue = supervision.read(root / "overnight-queue.json")
    runtime_policy = supervision.read(root / "overnight-policy.json")
    controls = [
        observer,
        Path(supervision.__file__),
        HERE / "recover_infrastructure.py",
        Path(__file__).resolve(),
        REPO / "src/score_sw_fabric/runtime/account_repair.py",
    ]
    server_record = supervision.read(SERVER / "queue-server.json")
    if server_record.get("launcher"):
        controls.append(Path(server_record["launcher"]))
    signing_path = SERVER / "server-recovery-auth.json"
    if not signing_path.exists():
        # Retain only the registered server's signing key; never copy/print its environment.
        for entry in Path(f"/proc/{server_record['pid']}/environ").read_bytes().split(b"\0"):
            if entry.startswith(b"SESSION_SECRET="):
                supervision.atomic(
                    signing_path, {"session_secret": entry.split(b"=", 1)[1].decode()}
                )
                break
    server_config = Path(server_record["config_path"])
    controls.append(server_config)
    policy_path = directory / "policy.json"
    policy = {
        "schema_version": 1,
        "run_id": identifier,
        "prepared_root": str(root),
        "workspace_device": root.stat().st_dev,
        "server_url": "http://127.0.0.1:43916",
        "auth_file": str(SERVER / "cli-auth.json"),
        "fabro_binary": str(BINARY),
        "observer": str(observer),
        "unit": "score-fabric-supervisor-" + identifier.lower(),
        "attached_at": time.time(),
        "controls": {str(p): supervision.digest(p) for p in controls},
        "repair_command": [
            sys.executable,
            str(HERE / "recover_infrastructure.py"),
            str(policy_path),
        ],
        "runtime_policy": runtime_policy,
        "single_pass": queue["single_pass"],
        "all_obligations": queue["all_obligations"],
        "model": "gpt-6.1-sol",
        "reasoning_effort": "medium",
        "authentication": "ChatGPT",
        "api_fallback": False,
        "authority": "User: do it; prevent missing automatic Codex infrastructure recovery",
        "server_restore": {
            "root": str(SERVER),
            "config": str(server_config),
            "binary_sha256": supervision.digest(BINARY),
            "pid": server_record["pid"],
            "process_identity": supervision.process_identity(server_record["pid"]),
        },
    }
    supervision.atomic(policy_path, policy)
    # Bind before starting the service to prevent duplicate admission attempts.
    supervision.atomic(
        binding,
        {
            "policy": str(policy_path),
            "run_id": identifier,
            "unit": policy["unit"],
            "status": "admission_pending",
        },
    )
    receipt = supervision.start_service(policy_path)
    supervision.atomic(
        binding, {**supervision.read(binding), "status": "ready", "ready_receipt": receipt}
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    receipt = ensure_supervised(root)
    print(
        json.dumps(
            {
                "root": str(root),
                "binding": str(root / "supervision-binding.json"),
                "unit": receipt["unit"],
                "pid": receipt["pid"],
                "run_id": receipt["run_id"],
            }
        )
    )


if __name__ == "__main__":
    main()
