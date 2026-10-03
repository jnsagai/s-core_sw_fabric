"""Host hooks for the proposed overnight Fabro queue; never an approval collector."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import guard_agent_tools
from measure import digest, verify_tree


def block(reason: str) -> int:
    print(json.dumps({"decision": "block", "reason": reason}))
    return 2


def admissible(policy: dict, context: dict, now: float) -> bool:
    node = policy["nodes"].get(context.get("node_id"))
    if node is None:
        return False
    if context.get("event") == "stage_start":
        return now + node["timeout_seconds"] + 60 < policy["deadline_epoch"]
    return now < policy["deadline_epoch"]


def measure(
    root: Path,
    policy: dict,
    node: dict,
    initiator: str = "Fabro host hook",
) -> None:
    """Snapshot one isolated workspace and run fixed focused GCC/GTest checks."""
    from isolate_docker import docker

    native_run = (root / "native-run-id").read_text().strip()
    if not re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", native_run):
        raise ValueError("Native run binding missing or invalid")
    containers = docker(
        "ps",
        "--filter",
        "label=sh.sandbox-driver.managed=true",
        "--filter",
        "ancestor=" + policy["image_id"],
        "--filter",
        "label=petri.run=" + native_run,
        "--format",
        "{{.ID}}",
    ).splitlines()
    if len(containers) != 1:
        raise ValueError("Measurement requires exactly one matching managed container")
    container = containers[0]
    inspected = json.loads(docker("inspect", container))[0]
    if (
        inspected["Image"] != policy["image_id"]
        or inspected["NetworkSettings"]["Networks"]
        or inspected["Config"]["Labels"].get("petri.run") != native_run
    ):
        raise ValueError("Measurement container identity or network changed")
    out = root / "measurements" / (node["ref"] + "-" + str(time.time_ns()))
    out.mkdir(parents=True)
    source = out / "source"
    source.mkdir()
    docker("cp", container + ":/workspace/.", str(source))
    inputs = json.loads((root / "measurement-inputs.json").read_bytes())
    baseline = Path(inputs["baseline"])
    gtest = Path(inputs["googletest"])
    verify_tree(baseline, json.loads(Path(inputs["source_manifest"]).read_bytes()))
    verify_tree(gtest, json.loads(Path(inputs["googletest_manifest"]).read_bytes()))
    for control in inputs["controls"]:
        if digest(Path(control["path"])) != control["sha256"]:
            raise ValueError("Frozen measurement control changed")

    def identity(path: Path):
        if path.is_symlink():
            return ("symlink", os.readlink(path))
        if path.is_file():
            return ("file", digest(path), path.stat().st_mode & 0o777)
        return None

    original = root / "target"
    paths = {
        str(path.relative_to(tree))
        for tree in (original, source)
        for path in tree.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    changed = []
    for relative in sorted(paths):
        # Fabro owns checkpoint Git metadata; agents cannot write it through
        # the file-tool guard. It is not a target engineering source change.
        if relative.startswith((".llm_tmp/overnight/", ".git/")):
            continue
        if identity(original / relative) != identity(source / relative):
            if "/workspace/" + relative not in policy["source_write_paths"]:
                raise ValueError("Out-of-scope workspace change: " + relative)
            changed.append(relative)
    record = {
        "check_ref": node["ref"],
        "status": "findings",
        "mode": node["mode"],
        "changed_paths": changed,
        "source_hashes": {
            p: identity(source / p)
            for p in sorted(paths)
            if not p.startswith((".llm_tmp/overnight/", ".git/"))
        },
        "origin": "local_unprotected_measurement",
        "initiator": initiator,
        "engineering_acceptance": "pending",
        "full_native_tests": "not_executed",
        "compiler": inputs["compiler"],
        "compiler_sha256": digest(Path(inputs["compiler"])),
    }

    def run(label: str, command: list[str], cwd: Path) -> int:
        with (out / (label + ".stdout")).open("wb") as stdout:
            with (out / (label + ".stderr")).open("wb") as stderr:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=120,
                    check=False,
                )
        (out / (label + ".command.json")).write_text(
            json.dumps(
                {
                    "argv": command,
                    "exit_code": result.returncode,
                },
                indent=2,
            )
            + "\n"
        )
        return result.returncode

    def compile_and_test(label: str, tree: Path, sanitizer: bool = False) -> dict:
        exe = out / label
        command = [
            inputs["compiler"],
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pthread",
            "-I.",
            f"-I{gtest}/googletest/include",
            f"-I{gtest}/googletest",
            "score/socom/impl/service_identifier.cpp",
            "score/socom/impl/string_registry.cpp",
            "score/socom/test/unit/service_identifier_tests.cpp",
            f"{gtest}/googletest/src/gtest-all.cc",
            f"{gtest}/googletest/src/gtest_main.cc",
            "-o",
            str(exe),
        ]
        if sanitizer:
            command.extend(["-fsanitize=undefined", "-fno-sanitize-recover=all"])
        compile_exit = run(label + "-compile", command, tree)
        if compile_exit:
            return {"compile_exit": compile_exit}
        test_exit = run(
            label + "-test", [str(exe), f"--gtest_output=json:{out}/{label}.json"], tree
        )
        result = json.loads((out / (label + ".json")).read_bytes())
        return {
            "compile_exit": 0,
            "test_exit": test_exit,
            "tests": result["tests"],
            "failures": result["failures"],
            "disabled": result["disabled"],
        }

    test = "score/socom/test/unit/service_identifier_tests.cpp"
    if not (source / test).is_file():
        record["reason"] = "Agent regression test missing"
    else:
        before = out / "baseline"
        shutil.copytree(baseline, before, symlinks=True)
        shutil.copyfile(source / test, before / test)
        record["baseline_with_agent_tests"] = compile_and_test("before", before)
        record["candidate"] = compile_and_test("after", source, node["mode"] == "ubsan")
        old, new = record["baseline_with_agent_tests"], record["candidate"]
        if (
            old.get("compile_exit") == 0
            and old.get("test_exit") == 1
            and old.get("failures", 0) > 0
            and new.get("compile_exit") == 0
            and new.get("test_exit") == 0
            and new.get("tests", 0) > 0
            and new.get("failures") == 0
            and new.get("disabled") == 0
        ):
            record["status"] = "completed"
    (out / "measurement.json").write_text(json.dumps(record, indent=2) + "\n")
    feedback = out / "feedback"
    feedback.mkdir()
    (feedback / "check-result").write_text("0\n" if record["status"] == "completed" else "1\n")
    for path in out.iterdir():
        if path.is_file() and path.suffix in {".json", ".stdout", ".stderr"}:
            shutil.copyfile(path, feedback / path.name)
    # Host-measured feedback is read-only to all draft agents.
    docker("exec", container, "mkdir", "-p", "/workspace/.llm_tmp/overnight/validation")
    docker("cp", str(feedback) + "/.", container + ":/workspace/.llm_tmp/overnight/validation/")
    shutil.copyfile(out / "measurement.json", root / "latest-measurement.json")


def main() -> int:
    root = Path(sys.argv[1]).resolve(strict=True)
    policy = json.loads((root / "overnight-policy.json").read_bytes())
    phase = sys.argv[2] if len(sys.argv) > 2 else "guard"
    context = None
    try:
        context = json.load(sys.stdin)
        if not isinstance(context, dict) or not admissible(policy, context, time.time()):
            return block("Overnight deadline or unknown node; no further work admitted")
        node = policy["nodes"][context["node_id"]]
        if context["event"] == "pre_tool_use":
            guard_agent_tools.WRITABLE = set(node["write_paths"])
            return (
                0 if guard_agent_tools.allowed(context) else block("Overnight tool/path boundary")
            )
        if context["event"] != "stage_start":
            return block("Unknown overnight hook event")
        if node.get("repair_for"):
            latest = json.loads((root / "latest-measurement.json").read_bytes())
            if latest.get("check_ref") != node["repair_for"] or latest.get("status") != "findings":
                return block("Rework requires current measured source/test findings")
        if phase == "measure" and node.get("mode"):
            if node["mode"].startswith("obligation:"):
                from collect_obligations import collect

                collect(root, policy, node)
            else:
                measure(root, policy, node)
        elif phase not in {"guard", "measure"}:
            return block("Unknown hook phase")
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        if isinstance(context, dict):
            node = policy["nodes"].get(context.get("node_id"), {})
            if node.get("mode"):
                (root / "latest-measurement.json").write_text(
                    json.dumps(
                        {
                            "check_ref": node["ref"],
                            "status": "unavailable",
                            "reason": type(error).__name__,
                            "engineering_acceptance": "pending",
                        }
                    )
                    + "\n"
                )
        return block("Overnight check unavailable: " + type(error).__name__)


if __name__ == "__main__":
    raise SystemExit(main())
