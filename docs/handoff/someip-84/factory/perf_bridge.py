"""Run-scoped perf attachment with container capabilities, without global sysctl edits."""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

PID_RESOLVER = r"""
import os, sys, signal, subprocess, hashlib, json
namespace, start, pid, owner_uid, owner_gid, control = sys.argv[1:7]
args = sys.argv[7:]
if namespace != "none":
    found = []
    for name in os.listdir("/proc"):
        if not name.isdigit(): continue
        try:
            if str(os.stat("/proc/" + name + "/ns/pid").st_ino) != namespace: continue
            fields = open("/proc/" + name + "/status").read().splitlines()
            nspid = next(line for line in fields if line.startswith("NSpid:")).split()[-1]
            stat = open("/proc/" + name + "/stat").read().rsplit(")", 1)[1].split()
            if nspid == pid and stat[19] == start: found.append(name)
        except (OSError, StopIteration): pass
    if len(found) != 1: raise SystemExit("Cannot bind the exact native profiling workload")
    index = args.index("--pid") + 1
    args[index] = found[0]
    print("score perf: namespace PID " + pid + " bound to host PID " + found[0], file=sys.stderr)
if control != "none": args += ["--control=fifo:" + control]
child = subprocess.Popen(["/opt/score-perf", *args])
def forward(sig, _frame):
    if child.poll() is None:
        if control != "none":
            with open(control, "w") as output: output.write("stop\n")
        else: child.send_signal(sig)
signal.signal(signal.SIGINT, forward)
signal.signal(signal.SIGTERM, forward)
code = child.wait()
if args and args[0] == "record" and "-o" in args:
    data = args[args.index("-o") + 1]
    if os.path.isfile(data):
        os.chmod(data, 0o644)
        os.chown(data, int(owner_uid), int(owner_gid))
        receipt = data + ".receipt.json"
        with open(receipt, "w") as output:
            json.dump({"sha256": hashlib.file_digest(open(data, "rb"), "sha256").hexdigest(),
                       "perf_exit_code": code, "host_uid": int(owner_uid)}, output)
        os.chmod(receipt, 0o644)
        os.chown(receipt, int(owner_uid), int(owner_gid))
raise SystemExit(code)
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execution_exit(workload_code: int | None, profiler_code: int) -> int:
    """A recorded dataset never converts a crashed workload into success.

    Native daemon cleanup deliberately kills its child and ignores the wrapper
    return code. Foreground benchmarks use check=True and must observe this failure.
    Recording receipts report the profiler status separately for daemon decoding.
    """
    if workload_code:
        return 128 - workload_code if workload_code < 0 else workload_code
    return 128 - profiler_code if profiler_code < 0 else profiler_code


def native_cleanup(workload: Path, code: int | None) -> bool:
    return code == -signal.SIGKILL and any(
        workload.as_posix().endswith("/" + path)
        for path in (
            "score/someipd/someipd",
            "score/gatewayd/gatewayd",
            "tests/benchmarks/echo_server",
        )
    )


def provision(root: Path, image: str) -> None:
    from storage import ACCOUNT_HOME

    perf = Path("/usr/lib/linux-tools") / os.uname().release / "perf"
    perf = perf.resolve(strict=True)
    mounts = [{"source": str(perf), "destination": "/opt/score-perf", "sha256": digest(perf)}]
    for line in subprocess.check_output(["ldd", str(perf)], text=True).splitlines():
        match = re.search(r"=> (/\S+)", line)
        if not match:
            continue
        original = Path(match[1])
        if original.name.split(".")[0] in {"libc", "libm", "libstdc++", "libgcc_s"}:
            continue
        library = original.resolve(strict=True)
        mounts.append(
            {
                "source": str(library),
                "destination": "/usr/lib/x86_64-linux-gnu/" + original.name,
                "sha256": digest(library),
            }
        )
    value = {
        "image": image,
        "mounts": mounts,
        "kernel": os.uname().release,
        "sysctl_changed": False,
        "capabilities": ["PERFMON", "DAC_OVERRIDE", "SYS_PTRACE", "CHOWN", "IPC_LOCK"],
        "output_owner_uid": os.getuid(),
        "output_owner_gid": os.getgid(),
        "security_options": ["seccomp=unconfined", "apparmor=unconfined"],
        "scope": str(root),
        "storage_owner_home": str(ACCOUNT_HOME),
    }
    binding = root / "build-workspace-binding.json"
    value["build_root"] = json.loads(binding.read_text())["root"] if binding.exists() else str(root)
    (root / "perf-bridge.json").write_text(json.dumps(value, indent=2) + "\n")
    (root / "perf-invocations").mkdir(exist_ok=True)
    directory = root / "perf-bin"
    directory.mkdir(exist_ok=True)
    entrypoint = directory / "perf"
    entrypoint.write_text(
        "#!"
        + sys.executable
        + "\nimport sys\nfrom pathlib import Path\n"
        + "sys.path.insert(0, "
        + repr(str(root))
        + ")\n"
        + "from perf_bridge import execute\n"
        + "raise SystemExit(execute(Path("
        + repr(str(root))
        + "), sys.argv[1:]))\n"
    )
    entrypoint.chmod(0o700)


def docker_args(root: Path, config: dict) -> list[str]:
    for mount in config["mounts"]:
        if digest(Path(mount["source"])) != mount["sha256"]:
            raise ValueError("Perf bridge tool identity changed")
    command = [
        "/usr/bin/docker",
        "run",
        "--pull",
        "never",
        "--network",
        "none",
        "--pid",
        "host",
        "--cap-drop",
        "ALL",
        "--cap-add",
        "PERFMON",
        "--cap-add",
        "DAC_OVERRIDE",
        "--cap-add",
        "SYS_PTRACE",
        "--cap-add",
        "CHOWN",
        "--cap-add",
        "IPC_LOCK",
        "--security-opt",
        "seccomp=unconfined",
        "--security-opt",
        "apparmor=unconfined",
        "--label",
        "score.perf.root=" + str(root),
        "--mount",
        "type=bind,src=" + str(root) + ",dst=" + str(root),
    ]
    if config.get("build_root", str(root)) != str(root):
        command += [
            "--mount",
            "type=bind,src=" + config["build_root"] + ",dst=" + config["build_root"],
        ]
    for mount in config["mounts"]:
        command += [
            "--mount",
            "type=bind,src=" + mount["source"] + ",dst=" + mount["destination"] + ",readonly",
        ]
    return command


def execute(root: Path, args: list[str]) -> int:
    from storage import validate_run_root

    config = json.loads((root / "perf-bridge.json").read_text())
    validate_run_root(root, account_home=Path(config["storage_owner_home"]))
    if config["scope"] != str(root):
        raise ValueError("Perf bridge root differs")
    stem = root / "perf-invocations" / str(time.time_ns())
    stem.parent.mkdir(exist_ok=True)
    cidfile = stem.with_suffix(".cid")
    command = docker_args(root, config) + ["--cidfile", str(cidfile)]
    workload = None
    control_path, control_fd = "none", None
    namespace, start, workload_pid = "none", "none", "none"
    if args and args[0] == "record":
        split = args.index("--")
        workload_args = args[split + 1 :]
        build_root = Path(config.get("build_root", str(root)))
        if not workload_args or not any(
            Path(workload_args[0]).resolve().is_relative_to(p) for p in (root, build_root)
        ):
            raise ValueError("Perf workload escapes owned run")
        output = Path(args[args.index("-o") + 1]).resolve()
        if not any(output.is_relative_to(p) for p in (root, build_root)):
            raise ValueError("Perf output escapes owned run")
        control_path = str(stem.with_suffix(".control"))
        os.mkfifo(control_path, 0o600)
        control_fd = os.open(control_path, os.O_RDWR | os.O_NONBLOCK)
        workload = subprocess.Popen(workload_args)
        namespace = str(os.stat("/proc/self/ns/pid").st_ino)
        workload_pid = str(workload.pid)
        start = Path("/proc/" + workload_pid + "/stat").read_text().rsplit(")", 1)[1].split()[19]
        args = args[:split] + ["--pid", str(workload.pid)]
    elif args and args[0] == "script":
        dataset = Path(args[args.index("-i") + 1]).resolve(strict=True)
        build_root = Path(config.get("build_root", str(root)))
        if not any(dataset.is_relative_to(p) for p in (root, build_root)):
            raise ValueError("Perf script input escapes owned run")
        receipt = json.loads(Path(str(dataset) + ".receipt.json").read_text())
        if any(
            receipt.get(key) != value
            for key, value in {
                "sha256": digest(dataset),
                "perf_exit_code": 0,
                "host_uid": config["output_owner_uid"],
            }.items()
        ) or (
            receipt.get("workload_exit_code") != 0
            and not (
                receipt.get("workload_exit_code") == -signal.SIGKILL
                and receipt.get("native_daemon_cleanup") is True
            )
        ):
            raise ValueError("Perf script input differs from successful native recording")
        # The scoped helper's root UID differs from the measured build user's UID.
        # Accept this checked recording only; preserve actual perf script failures.
        args = [*args, "-f"]
    else:
        raise ValueError("Only measured record/script operations are allowed")
    command += [
        "--entrypoint",
        "/usr/local/bin/python3",
        config["image"],
        "-c",
        PID_RESOLVER,
        namespace,
        start,
        workload_pid,
        str(config["output_owner_uid"]),
        str(config["output_owner_gid"]),
        control_path,
        *args,
    ]
    profiler = None
    try:
        docker_environment = dict(os.environ, DOCKER_CONFIG=str(stem.parent))
        profiler = subprocess.Popen(command, env=docker_environment)
        if workload is not None:

            def terminate(_sig, _frame):
                if workload.poll() is None:
                    workload.terminate()

            signal.signal(signal.SIGTERM, terminate)
            signal.signal(signal.SIGINT, terminate)
            workload.wait()
            # The real perf control command flushes and exits normally. Signals
            # propagate signal exits even when the captured data is complete.
            if control_fd is not None:
                os.write(control_fd, b"stop\n")
        code = profiler.wait(timeout=20)
        if cidfile.exists():
            identifier = cidfile.read_text().strip()
            wait = subprocess.run(
                ["/usr/bin/docker", "wait", identifier],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if wait.returncode == 0 and wait.stdout.strip().isdigit():
                code = int(wait.stdout.strip())
        final_code = execution_exit(workload.returncode if workload is not None else None, code)
        if workload is not None:
            receipt_path = Path(str(output) + ".receipt.json")
            if receipt_path.exists():
                receipt = json.loads(receipt_path.read_text())
                receipt.update(
                    {
                        "workload_exit_code": workload.returncode,
                        "wrapper_exit_code": final_code,
                        "native_daemon_cleanup": native_cleanup(
                            Path(workload_args[0]), workload.returncode
                        ),
                    }
                )
                receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        return final_code
    finally:
        if control_fd is not None:
            os.close(control_fd)
            Path(control_path).unlink(missing_ok=True)
        if workload is not None and workload.poll() is None:
            workload.kill()
            workload.wait(timeout=10)
        if cidfile.exists():
            subprocess.run(
                ["/usr/bin/docker", "rm", "-f", cidfile.read_text().strip()],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
        if profiler is not None and profiler.poll() is None:
            profiler.kill()
            profiler.wait(timeout=10)
