"""Run the compiled operational demonstration through the existing fabric runtime.

Uses a fresh disposable server, no provider secrets, and no automatic human answers.
Fabro owns the run and its wait. The runner only prepares and exports one bounded run.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml
from prepare import BINARY, HERE, PIN, REPO, SOURCE, prepare, sha, write
from storage import private_server_root

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.runtime.export import verify_export
from score_sw_fabric.runtime.operations import export, run, status
from score_sw_fabric.runtime.request import load_request


def cli_auth_file(root: Path, base_url: str, token: str) -> Path:
    """Native AuthStore format at the pinned commit, isolated from the user's login."""
    path = root / "cli-auth.json"
    record = {
        "servers": {
            base_url: {
                "kind": "dev-token",
                "token": token,
                "logged_in_at": datetime.now(UTC).isoformat(),
            }
        }
    }
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(record, stream)
    return path


def collect_measurements(root: Path, durable: Path) -> dict[str, str]:
    """Retain every available raw phase, including interrupted/never-started phases."""
    result = {}
    for phase in ("baseline", "external-candidate"):
        source = root / "target/.llm_tmp" / phase
        if not source.exists():
            result[phase] = "missing"
            continue
        dest = durable / phase
        dest.mkdir(exist_ok=False)
        for path in source.iterdir():
            if path.is_file() and path.name != "service-identifier-tests":
                shutil.copyfile(path, dest / path.name)
        result[phase] = (
            "present" if (dest / "measurement.json").is_file() else "measurement_missing"
        )
    return result


def prepare_runtime_request(root: Path, base_url: str, credential: Path | None = None):
    caps = [
        "blob_read",
        "event_read",
        "output_read",
        "question_read",
        "run_cancel",
        "run_create",
        "run_inspect",
        "run_start",
        "stage_list",
        "timeline_read",
        "workflow_register",
    ]
    profile = seal(
        {
            "schema_version": 1,
            "kind": "runtime_profile",
            "id": "someip84-disposable-candidate",
            "source_commit": PIN,
            "executable_sha256": sha(BINARY),
            "source_api_sha256": sha(SOURCE / "docs/public/api-reference/fabro-api.yaml"),
            "base_url": base_url,
            "auth_mode": "dev_token_disposable",
            "declared_capabilities": caps,
            "demonstrated_capabilities": caps,
            "limits": {"timeout_seconds": 20, "response_bytes": 4_000_000},
            "status": "candidate_only",
        }
    )
    write(root / "runtime-profile.json", profile)
    package = json.loads((root / "out/package.json").read_bytes())
    baseline = {
        "source_digest": sha(root / "measurement-inputs.json"),
        "process_digest": sha(
            HERE
            / "../../../.."
            / "specs/010-misra-quality-and-deviations/contracts/fabro-command-binding.md"
        ),
        "policy_digest": sha(root / "execution_mapping.yaml"),
        "tool_digest": sha(root / "validator_profile.yaml"),
        "subject_digest": sha(root / "task-authority.json"),
        "evidence_digests": [],
    }
    intent = seal(
        {
            "schema_version": 1,
            "kind": "runtime_intent",
            "intent_id": root.name,
            "package_ref": {
                "path": "out/package.json",
                "sha256": sha(root / "out/package.json"),
                "semantic_digest": package["digest"],
            },
            "runtime_profile_ref": {
                "path": "runtime-profile.json",
                "sha256": sha(root / "runtime-profile.json"),
                "semantic_digest": profile["digest"],
            },
            "baseline": baseline,
            "start_args": {
                "target_id": "local",
                "labels": {"scope": "external-candidate-measurement"},
            },
            "limits": {
                "timeout_seconds": 20,
                "event_pages": 100,
                "output_bytes": 4_000_000,
                "attempts": 1,
            },
        }
    )
    write(root / "intent.json", intent)
    selections = {
        "intent": "intent.json",
        "package": "out/package.json",
        "compiler_profile": "compiler_profile.yaml",
        "runtime_profile": "runtime-profile.json",
    }
    request = {
        "schema_version": 1,
        "kind": "runtime_request",
        "runtime_commit": PIN,
        **{name: {"path": path, "sha256": sha(root / path)} for name, path in selections.items()},
        "candidate": {
            "executable": str(BINARY),
            "source_api": str(SOURCE / "docs/public/api-reference/fabro-api.yaml"),
        },
        "credential_file": str(credential) if credential else "token",
        "ledger_root": "ledger",
        "target": {
            "path": str(root / "target"),
            "disposable_root": str(root),
            "environment_id": "local",
        },
        "baseline_now": None,
        "evidence": [],
        "effects": [],
        "subject": None,
        "protected_roots": [str(REPO), str(SOURCE)],
    }
    (root / "runtime.yaml").write_text(yaml.safe_dump(request, sort_keys=True))
    return load_request(root / "runtime.yaml")


def main() -> None:
    root = prepare()
    durable = HERE / "runs" / root.name
    durable.mkdir(parents=True)
    for name in (
        "plan.json",
        "execution_mapping.yaml",
        "compiler_profile.yaml",
        "validator_profile.yaml",
        "compile.yaml",
        "measurement-inputs.json",
        "task-authority.json",
        "native-validation.json",
    ):
        shutil.copyfile(root / name, durable / name)
    shutil.copyfile(root / "out/package.json", durable / "package.json")
    print(f"Evidence directory: {durable}", flush=True)
    server_root = private_server_root(root, "host-server")
    home = server_root / "home"
    home.mkdir()
    token = "fabro_dev_" + secrets.token_hex(32)
    fd = os.open(server_root / "token", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(token + "\n")
    (server_root / "settings.toml").write_text(
        '_version = 1\n[server.auth]\nmethods = ["dev-token"]\n'
    )
    base_url = "http://127.0.0.1:43913"
    auth_path = cli_auth_file(server_root, base_url, token)
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "FABRO_DEV_TOKEN": token,
        "FABRO_AUTH_FILE": str(auth_path),
        "SESSION_SECRET": secrets.token_hex(32),
        "NO_COLOR": "1",
        "FABRO_HTTP_PROXY_POLICY": "disabled",
        "FABRO_NO_UPGRADE_CHECK": "true",
    }
    selected = prepare_runtime_request(root, base_url, server_root / "token")
    server = None
    try:
        with (durable / "server.log").open("wb") as log:
            server = subprocess.Popen(
                [
                    str(BINARY),
                    "server",
                    "start",
                    "--foreground",
                    "--no-web",
                    "--bind",
                    "127.0.0.1:43913",
                    "--storage-dir",
                    str(server_root / "storage"),
                    "--config",
                    str(server_root / "settings.toml"),
                ],
                cwd=server_root,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        write(
            durable / "server-identity.json",
            {
                "pid": server.pid,
                "root": str(root),
                "source_commit": PIN,
                "executable_sha256": sha(BINARY),
            },
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        # Bounded server readiness check; it does not start or schedule workflow stages.
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError("Fabro server failed to start; see preserved server.log")
            if (server_root / "storage/server.json").exists():
                try:
                    req = urllib.request.Request(
                        base_url + "/api/v1/runs", headers={"Authorization": "Bearer " + token}
                    )
                    with opener.open(req, timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
            time.sleep(0.2)
        else:
            raise RuntimeError("Fabro server readiness timeout")
        identity = json.loads((server_root / "storage/server.json").read_bytes())
        pid = identity["pid"]
        if (
            Path(f"/proc/{pid}/cwd").resolve() != server_root
            or Path(f"/proc/{pid}/exe").resolve() != BINARY
        ):
            raise RuntimeError("Disposable server identity differs")
        code, binding = run(selected)
        write(durable / "binding.json", binding)
        if code != 0:
            raise RuntimeError(
                "Fabric run submission stopped; preserved binding forbids duplicate retry"
            )
        print(f"Fabro run: {binding['run_id']}", flush=True)
        with (durable / "native-wait.stdout").open("wb") as stdout:
            with (durable / "native-wait.stderr").open("wb") as stderr:
                waited = subprocess.run(
                    [
                        str(BINARY),
                        "--json",
                        "wait",
                        binding["run_id"],
                        "--server",
                        base_url,
                        "--timeout",
                        "120",
                    ],
                    cwd=root,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=150,
                    check=False,
                )
        write(
            durable / "native-wait.json",
            {
                "exit_code": waited.returncode,
                "expected_stop": "Unanswered live-agent configuration gate; wait may time out",
            },
        )
        code, snapshot = status(selected)
        write(durable / "snapshot.json", snapshot)
        _, exported = export(selected)
        write(durable / "runtime-export.json", exported)
        write(durable / "offline-verification.json", verify_export(exported))
        measurements = collect_measurements(root, durable)
        write(durable / "measurement-completeness.json", measurements)
        for name in ("runtime-profile.json", "intent.json", "runtime.yaml"):
            shutil.copyfile(root / name, durable / name)
        if waited.returncode not in {0, 1}:
            raise RuntimeError(
                f"Native waiter failed with exit {waited.returncode}; see native-wait.stderr"
            )
        if set(measurements.values()) != {"present"}:
            raise RuntimeError(
                "Measurement phases are incomplete; see measurement-completeness.json"
            )
        if snapshot["native_status"] != "blocked" or not snapshot["questions"]:
            raise RuntimeError("Expected unanswered configuration gate was not observed")
        if exported["completeness"] != "complete":
            raise RuntimeError("Native export is incomplete; original export retained")
        print(
            "Measurements exported; live implementation and engineering review remain pending.",
            flush=True,
        )
    except Exception as exc:
        write(
            durable / "execution-blocked.json",
            {
                "error": str(exc),
                "exception": type(exc).__name__,
                "fabro_run_created": (durable / "binding.json").exists(),
                "engineering_acceptance": "pending",
                "live_agent_implementation": "not_performed",
            },
        )
        print(f"Execution stopped: {exc}\nEvidence retained: {durable}", flush=True)
        raise
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


if __name__ == "__main__":
    main()
