"""Separate GCC ASan/UBSan builds and runtime diagnostics on disposable selected inputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from score_sw_fabric.quality.models import (
    Budget,
    Inputs,
    environment,
    execute,
    file_digest,
    raw_bytes,
)


def leak_runtime_gaps(stderr: bytes, adapter: str) -> list[str]:
    """Native fatal errors invalidate scope even alongside an AddressSanitizer finding."""
    if adapter != "asan" or b"LeakSanitizer has encountered a fatal error" not in stderr:
        return []
    gaps = ["LEAK_SANITIZER_RUNTIME_FAILED", "SANITIZER_RUNTIME_INCOMPLETE"]
    if b"LeakSanitizer does not work under ptrace" in stderr:
        gaps.append("LEAK_SANITIZER_PTRACE_UNSUPPORTED")
    return gaps


def prepare(selected: Inputs, work: Path) -> dict[str, str]:
    config = selected.settings
    directory = work / "sanitizers/suppressions"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (selected.adapter + ".supp")).write_bytes(selected.assets["native_suppressions"])
    options = config["runtime_template"].replace("%ROOT%", str(work) + "/")
    config["rendered_runtime"] = {config["runtime_name"]: options}
    return {**environment(work, selected.toolchain), config["runtime_name"]: options}


def diagnostic_records(
    phase: dict[str, Any], adapter: str, source: Path, files: dict[str, bytes]
) -> list[dict[str, Any]]:
    text = raw_bytes(phase["stderr"]).decode("utf-8", "replace")
    if adapter == "asan":
        match = re.search(r"ERROR: AddressSanitizer: ([A-Za-z0-9_-]+)", text)
    else:
        match = re.search(r"runtime error: (.*)", text)
    if not match:
        return []
    message = match[1]
    identifier = (
        message
        if adapter == "asan"
        else (
            "signed integer overflow" if message.startswith("signed integer overflow:") else message
        )
    )
    locations = []
    for raw, line, column in re.findall(r"([^\s:]+\.(?:cpp|cc|cxx|h|hpp)):(\d+)(?::(\d+))?", text):
        path = Path(raw)
        path = path if path.is_absolute() else source / path
        if path.is_relative_to(source):
            relative = str(path.relative_to(source))
            if relative in files and 1 <= int(line) <= len(files[relative].splitlines()):
                locations.append(
                    {
                        "path": relative,
                        "line": int(line),
                        "column": int(column or 0),
                        "native_path": raw,
                    }
                )
    return [
        {
            "native_id": identifier,
            "native_level": "runtime_error",
            "artifact_id": "runtime-stderr",
            "result_index": 0,
            "locations": locations,
            "native_record": {"runtime": adapter, "message": message},
        }
    ]


def build_and_execute(
    selected: Inputs, work: Path, budget: Budget, units: list[str], data: dict[str, bytes]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str], list[str]]:
    phases = []
    artifacts: list[dict[str, Any]] = []
    objects = []
    gaps = []
    if selected.settings["suppression_rules"]:
        return [], [], [], [], ["UNAPPROVED_SUPPRESSION"]
    env = prepare(selected, work)
    source = work / "source"
    binary = work / "instrumented-program"
    compiler = selected.toolchain["tool"]["path"]
    for index, unit in enumerate(units):
        obj = work / f"object-{index}.o"
        argv = [
            compiler,
            "-std=c++17",
            *selected.settings["compile_flags"],
            *["-I" + str(source / d) for d in selected.request.get("include_dirs", [])],
            *["-D" + d for d in selected.request.get("defines", [])],
            "-c",
            str(source / unit),
            "-o",
            str(obj),
        ]
        phase = execute(
            "compile:" + unit, argv, work, selected.request["timeout_seconds"], budget, env
        )
        phases.append(phase)
        if any(phase[k]["truncated"] for k in ("stdout", "stderr")):
            gaps.append("OUTPUT_TRUNCATED")
        if phase["exit_code"] != 0 or phase["timed_out"] or phase["error"]:
            gaps.append("PHASE_FAILED")
        if gaps:
            return phases, artifacts, [], [], gaps
        if not obj.is_file():
            return phases, artifacts, [], [], ["BUILD_ARTIFACT_MISSING"]
        objects.append(obj)
    phase = execute(
        "link",
        [compiler, *map(str, objects), *selected.settings["link_flags"], "-o", str(binary)],
        work,
        selected.request["timeout_seconds"],
        budget,
        env,
    )
    phases.append(phase)
    if any(phase[k]["truncated"] for k in ("stdout", "stderr")):
        gaps.append("OUTPUT_TRUNCATED")
    if phase["exit_code"] != 0 or phase["timed_out"] or phase["error"]:
        gaps.append("PHASE_FAILED")
    if gaps:
        return phases, artifacts, [], [], gaps
    if not binary.is_file():
        return phases, artifacts, [], [], ["BUILD_ARTIFACT_MISSING"]
    selected.settings["generated_binary"] = {
        "sha256": file_digest(binary),
        "bytes": binary.stat().st_size,
    }
    phase = execute(
        "runtime", [str(binary)], work, selected.request["timeout_seconds"], budget, env
    )
    phases.append(phase)
    artifacts.append(
        {
            **phase["stderr"],
            "id": "runtime-stderr",
            "format": selected.adapter + "-text",
            "translation_unit": None,
        }
    )
    findings = diagnostic_records(phase, selected.adapter, source, data)
    gaps.extend(leak_runtime_gaps(raw_bytes(phase["stderr"]), selected.adapter))
    if any(phase[k]["truncated"] for k in ("stdout", "stderr")):
        gaps.append("OUTPUT_TRUNCATED")
    if phase["timed_out"] or phase["error"]:
        gaps.append("PHASE_FAILED")
    if not ((phase["exit_code"] == 55 and findings) or (phase["exit_code"] == 0 and not findings)):
        gaps.append("SANITIZER_RUNTIME_INCOMPLETE")
    return phases, artifacts, findings, units if not gaps else [], gaps
