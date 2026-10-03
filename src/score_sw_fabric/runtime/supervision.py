"""Derived Fabro supervision with explicit account repair; never an execution scheduler."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import pwd
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

MAX_JSON = 4 * 1024**2


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or path.stat().st_size > MAX_JSON:
        raise ValueError("Unsafe supervision record")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("Supervision record must be an object")
    return value


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Supervision state must not contain symbolic ancestors")
    stage = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    with stage.open("w") as stream:
        os.chmod(stage, 0o600)
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    stage.replace(path)


def process_identity(pid: int) -> str:
    data = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    if data[0] == "Z":
        raise ValueError("Process is a zombie")
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip() + ":" + data[19]


def same_process(pid: int, identity: str) -> bool:
    try:
        return process_identity(pid) == identity
    except (OSError, ValueError, IndexError):
        return False


def require_ready(
    policy_path: Path, *, now: float | None = None, expected_run_id: str | None = None
) -> dict[str, Any]:
    policy = read(policy_path)
    if expected_run_id is not None and policy["run_id"] != expected_run_id:
        raise ValueError("Supervisor is bound to another run")
    receipt = read(policy_path.parent / "heartbeat.json")
    if (
        receipt.get("run_id") != policy["run_id"]
        or receipt.get("policy_sha256") != digest(policy_path)
        or receipt.get("phase") != "observing"
        or receipt.get("dependencies_verified") is not True
        or not same_process(receipt["pid"], receipt["process_identity"])
        or not 0 <= (time.time() if now is None else now) - receipt["observed_at"] <= 30
    ):
        raise ValueError("Missing, stale, substituted or unhealthy run supervisor")
    for name, expected in policy["controls"].items():
        if digest(Path(name)) != expected:
            raise ValueError("Supervisor control changed: " + name)
    return receipt


def classify(
    record: dict[str, Any],
    state: dict[str, Any],
    worker: bool,
    misses: int,
    measurement: dict[str, Any],
    age: float,
) -> str | None:
    native_status = record["lifecycle"]["status"]
    status = native_status["kind"]
    if (
        state.get("pending_interviews")
        or native_status.get("reason") == "cancelled"
        or status
        in {
            "waiting",
            "blocked",
            "cancelled",
            "canceled",
            "succeeded",
            "completed",
        }
    ):
        return None
    if status == "failed":
        return "native_failure"
    if measurement.get("status") == "unavailable":
        return "host_collector_failure"
    if status == "running" and not worker and misses >= 3 and age >= 60:
        return "worker_missing"
    return None


def worker_alive(policy: dict[str, Any]) -> bool:
    title = "fabro " + policy["run_id"][:12] + " running"
    for process in Path("/proc").glob("[0-9]*"):
        try:
            args = (process / "cmdline").read_bytes()[:8192].replace(b"\0", b" ").decode()
            exact = args.strip() == title or (
                "--run-id " + policy["run_id"] in args and "__run-worker" in args
            )
            if exact and (process / "exe").resolve() == Path(policy["fabro_binary"]).resolve():
                process_identity(int(process.name))
                return True
        except (OSError, ValueError, UnicodeError):
            continue
    return False


def native(policy: dict[str, Any], suffix: str = "") -> dict[str, Any]:
    base = policy["server_url"]
    token = read(Path(policy["auth_file"]))["servers"][base]["token"]
    request = urllib.request.Request(
        base + "/api/v1/runs/" + policy["run_id"] + suffix,
        headers={"Authorization": "Bearer " + token},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=8) as response:
        payload = response.read(MAX_JSON + 1)
    if len(payload) > MAX_JSON:
        raise ValueError("Native observation exceeds supervision read bound")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("Invalid native observation")
    if not suffix and value.get("id") != policy["run_id"]:
        raise ValueError("Native observation belongs to another run")
    return value


def claim(directory: Path, incident: dict[str, Any]) -> Path | None:
    key = hashlib.sha256(json.dumps(incident, sort_keys=True).encode()).hexdigest()
    folder = directory / "incidents" / key
    folder.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        folder.mkdir(mode=0o700)
    except FileExistsError:
        return None
    atomic(folder / "incident.json", incident)
    return folder / "incident.json"


def watch(policy_path: Path) -> None:
    policy = read(policy_path)
    directory = policy_path.parent
    with (directory / "observer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for path, expected in policy["controls"].items():
            if digest(Path(path)) != expected:
                raise ValueError("Changed frozen supervision control")
        dependencies_verified = False
        try:
            native(policy)
            dependencies_verified = True
        except OSError:
            if not (directory / "heartbeat.json").exists():
                raise  # Initial admission requires an authenticated native observation.
            # An admitted observer must still recover server loss after its own restart.
        pid, identity = os.getpid(), process_identity(os.getpid())
        state_path = directory / "observer-state.json"
        state = read(state_path) if state_path.exists() else {"phase": "observing"}
        misses = errors = 0
        child: subprocess.Popen[bytes] | None = None
        child_log: Any = None
        while True:
            phase = state["phase"]
            atomic(
                directory / "heartbeat.json",
                {
                    "run_id": policy["run_id"],
                    "policy_sha256": digest(policy_path),
                    "pid": pid,
                    "process_identity": identity,
                    "observed_at": time.time(),
                    "phase": phase,
                    "dependencies_verified": dependencies_verified,
                    "unit": policy["unit"],
                },
            )
            if phase == "repairing":
                incident_path = Path(state["incident"])
                result_path = incident_path.parent / "result.json"
                if result_path.exists():
                    result = read(result_path)
                    if child is not None:
                        child.wait(timeout=10)
                        child_log.close()
                        child = None
                    if result.get("status") == "replaced":
                        atomic(state_path, {**state, "phase": "replaced", "result": result})
                        return
                    state = {**state, "phase": "blocked", "result": result}
                    atomic(state_path, state)
                elif child is None:
                    # The adapter locks the incident and reconciles its saved intents on resume.
                    child_log = (incident_path.parent / "adapter.log").open("ab")
                    child = subprocess.Popen(
                        [*policy["repair_command"], str(incident_path)],
                        stdout=child_log,
                        stderr=child_log,
                        start_new_session=True,
                    )
                elif child.poll() is not None:
                    code = child.returncode
                    child_log.close()
                    child = None
                    if code != 75:  # Another adapter still owns the incident lock.
                        state = {**state, "phase": "blocked", "adapter_exit": code}
                        atomic(state_path, state)
                time.sleep(5)
                continue
            if phase == "blocked":
                time.sleep(5)
                continue
            record: dict[str, Any] = {}
            runtime_state: dict[str, Any] = {}
            measured: dict[str, Any] = {}
            fault = None
            try:
                # The full /state projection embeds every stage's output and grows
                # with the run. Supervision needs only lifecycle and human gates.
                record = native(policy)
                questions = native(policy, "/questions").get("data")
                if not isinstance(questions, list):
                    raise ValueError("Invalid native pending-question observation")
                runtime_state = {"pending_interviews": questions}
                alive = worker_alive(policy)
                misses = 0 if alive else misses + 1
                age = time.time() - policy["attached_at"]
                path = Path(policy["prepared_root"]) / "latest-measurement.json"
                measured = read(path) if path.exists() else {}
                fault = classify(record, runtime_state, alive, misses, measured, age)
                terminal = record["lifecycle"]["status"]["kind"]
                if policy.get("runtime_policy", {}).get("in_run_repair") and terminal == "failed":
                    atomic(
                        state_path,
                        {
                            "phase": "finished",
                            "native_status": terminal,
                            "reason": "Same-run repair stopped; no successor authorized",
                        },
                    )
                    return
                if (
                    terminal in {"succeeded", "completed", "cancelled", "canceled"}
                    or record["lifecycle"]["status"].get("reason") == "cancelled"
                ):
                    atomic(state_path, {"phase": "finished", "native_status": terminal})
                    return
                if not runtime_state.get("pending_interviews"):
                    root = Path(policy["prepared_root"])
                    if root.stat().st_dev != policy["workspace_device"]:
                        fault = "bound_storage_lost"
                    else:
                        probe = root / (".supervisor-write-" + str(pid))
                        with probe.open("w") as stream:
                            stream.write("storage write probe\n")
                        probe.unlink()
                errors = 0
                dependencies_verified = True
            except (OSError, ValueError, KeyError) as error:
                dependencies_verified = False
                errors += 1
                if errors >= 3:
                    fault = "observer_dependency_failure"
                    measured = {"error_type": type(error).__name__, "detail": str(error)[:4096]}
            if fault:
                incident = {
                    "run_id": policy["run_id"],
                    "kind": fault,
                    "measurement": measured,
                    "native_status": record.get("lifecycle"),
                    "native_conclusion": runtime_state.get("conclusion"),
                }
                claimed = claim(directory, incident)
                if claimed:
                    state = {"phase": "repairing", "incident": str(claimed)}
                    atomic(state_path, state)
                else:
                    key = hashlib.sha256(json.dumps(incident, sort_keys=True).encode()).hexdigest()
                    previous = directory / "incidents" / key / "incident.json"
                    # Resume an intent left between claim and state publication. The adapter's
                    # lock and invocation journal prohibit duplicate account calls/submission.
                    state = {"phase": "repairing", "incident": str(previous)}
                    atomic(state_path, state)
            time.sleep(5)


def start_service(policy_path: Path) -> dict[str, Any]:
    policy = read(policy_path)
    unit = policy["unit"]
    if not unit.startswith("score-fabric-supervisor-") or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in unit
    ):
        raise ValueError("Unsafe supervisor service name")

    def quote(value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("Unsafe supervisor service argument")
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'

    # Transient systemd-run units disappear on reboot. Keep the exact observer
    # and policy binding in an owner-only user unit so crash recovery survives it.
    directory = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".config/systemd/user"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (unit + ".service")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Supervisor service path must not contain symbolic ancestors")
    content = (
        "[Unit]\nDescription=S-CORE Fabro infrastructure observer\n"
        "[Service]\nType=simple\nRestart=on-failure\nRestartSec=5\nKillMode=process\n"
        "WorkingDirectory=" + str(policy_path.parent).replace("%", "%%") + "\n"
        "Environment=" + quote("PATH=" + os.environ["PATH"]) + "\n"
        "ExecStart="
        + " ".join(
            quote(v) for v in (sys.executable, policy["observer"], "watch", str(policy_path))
        )
        + "\n[Install]\nWantedBy=default.target\n"
    )
    if path.exists() and path.read_text() != content:
        raise ValueError("Existing supervisor service differs from its bound policy")
    if not path.exists():
        with path.open("x") as stream:
            os.chmod(path, 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        check=True,
        capture_output=True,
        timeout=15,
    )
    subprocess.run(
        ["systemctl", "--user", "enable", "--now", unit + ".service"],
        check=True,
        capture_output=True,
        timeout=15,
    )
    for _ in range(40):
        try:
            return require_ready(policy_path)
        except (OSError, ValueError, KeyError):
            time.sleep(0.25)
    raise RuntimeError("No verified supervisor readiness receipt; native start refused")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["watch"])
    parser.add_argument("policy", type=Path)
    args = parser.parse_args()
    watch(args.policy)


if __name__ == "__main__":
    main()
