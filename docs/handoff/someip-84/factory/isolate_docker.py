"""Fail-closed Fabro sandbox_ready hook for one disposable Docker run."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def docker(*args: str) -> str:
    result = subprocess.run(
        ["/usr/bin/docker", *args], capture_output=True, text=True, timeout=10, check=True
    )
    return result.stdout.strip()


def fail(reason: str) -> int:
    print(json.dumps({"decision": "block", "reason": "SOMEIP_ISOLATION_" + reason}))
    return 2


def main() -> int:
    expected_image = sys.argv[1] if len(sys.argv) in {3, 4} else ""
    source = Path(sys.argv[2]) if len(sys.argv) in {3, 4} else Path("/")
    if not expected_image.startswith("sha256:") or source.name != "target":
        return fail("INPUT")
    if not (source / ".llm_tmp/context/issue-snapshot.json").is_file():
        return fail("SOURCE_CONTEXT")
    if not (source / "score/socom/impl/service_identifier.cpp").is_file():
        return fail("INPUT")
    try:
        expected_run = None
        filters = []
        if len(sys.argv) == 4:
            binding = Path(sys.argv[3])
            if binding != source.parent / "native-run-id":
                return fail("RUN_BINDING_PATH")
            expected_run = binding.read_text().strip()
            if not re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", expected_run):
                return fail("RUN_BINDING")
            filters = ["--filter", "label=petri.run=" + expected_run]
        matches = docker(
            "ps",
            "--filter",
            "label=sh.sandbox-driver.managed=true",
            "--filter",
            "ancestor=score-someip84-agent:20261001",
            *filters,
            "--format",
            "{{.ID}}",
        ).splitlines()
        if len(matches) != 1:
            return fail(f"CONTAINER_COUNT_{len(matches)}")
        container = matches[0]
        record = json.loads(docker("inspect", container))[0]
        if record["Image"] != expected_image:
            return fail("IMAGE")
        labels = record["Config"]["Labels"]
        native_run = labels.get("petri.run", "")
        workspace = labels.get("petri.workspace", "")
        if not re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", native_run):
            return fail("RUN_LABEL")
        if expected_run is not None and native_run != expected_run:
            return fail("RUN_OWNERSHIP")
        if not workspace.startswith(native_run + "/"):
            return fail("WORKSPACE_LABEL")
        mounts = record["Mounts"]
        if len(mounts) != 1 or mounts[0]["Type"] != "volume":
            return fail("MOUNTS")
        if mounts[0]["Destination"] != "/workspace":
            return fail("WORKSPACE")
        for network in list(record["NetworkSettings"]["Networks"]):
            docker("network", "disconnect", "-f", network, container)
        record = json.loads(docker("inspect", container))[0]
        if record["NetworkSettings"]["Networks"]:
            return fail("NETWORK")
        docker("cp", str(source) + "/.", container + ":/workspace/")
        docker(
            "exec",
            container,
            "test",
            "-f",
            "/workspace/.llm_tmp/context/issue-snapshot.json",
        )
        docker(
            "exec",
            container,
            "test",
            "-f",
            "/workspace/score/socom/impl/service_identifier.cpp",
        )
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError):
        return fail("ERROR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
