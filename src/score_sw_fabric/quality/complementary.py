"""Explicit local adapter selection around the shared bounded quality foundation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import cppcheck, sanitizers
from score_sw_fabric.quality.capabilities import base_record
from score_sw_fabric.quality.models import (
    Budget,
    Inputs,
    baseline,
    environment,
    execute,
    identity_state,
    load_inputs,
    raw_bytes,
    recheck_controls,
)
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.storage import temporary_directory


def initial(selected: Inputs, kind: str) -> dict[str, Any]:
    record = base_record(selected, kind)
    record["gaps"] = [
        g for g in record["gaps"] if g != f"CAPABILITY_NOT_SELECTED:{selected.adapter}"
    ]
    if selected.adapter != "clang-tidy":
        record["gaps"].append("CAPABILITY_NOT_SELECTED:clang-tidy")
    record["configuration"] = {
        **selected.request["config"],
        "adapter": selected.adapter,
        "effective": deepcopy(selected.settings),
    }
    return record


def probe(selected: Inputs, work: Path, budget: Budget) -> dict[str, Any]:
    record = initial(selected, f"quality_{selected.adapter}_capability_inventory")
    if not identity_state(selected.toolchain):
        record["capability"]["state"] = "unavailable"
        record["gaps"].append("CAPABILITY_UNAVAILABLE")
        return record
    phase = execute(
        "version",
        [selected.toolchain["tool"]["path"], "--version"],
        work,
        selected.request["timeout_seconds"],
        budget,
        environment(work, selected.toolchain),
    )
    record["phases"].append(phase)
    lines = raw_bytes(phase["stdout"]).decode("utf-8", "replace").splitlines()
    if phase["exit_code"] != 0 or phase["timed_out"] or phase["error"]:
        record["gaps"].append("PHASE_FAILED")
        record["outcome"] = "incomplete"
        return record
    if any(phase[k]["truncated"] for k in ("stdout", "stderr")):
        record["gaps"].append("OUTPUT_TRUNCATED")
        record["outcome"] = "incomplete"
        return record
    if not lines or lines[0].strip() != selected.toolchain["tool"]["version"]:
        raise InputError("TOOL_IDENTITY_MISMATCH", "Tool version differs from selection")
    source = work / "source"
    source.mkdir()
    data = {"capability.cpp": b"auto main() -> int { return 0; }\n"}
    (source / "capability.cpp").write_bytes(data["capability.cpp"])
    function = cppcheck.analyze if selected.adapter == "cppcheck" else sanitizers.build_and_execute
    phases, artifacts, findings, processed, gaps = function(
        selected, work, budget, ["capability.cpp"], data
    )
    record["phases"].extend(phases)
    record["artifacts"].extend(artifacts)
    if findings or processed != ["capability.cpp"]:
        gaps.append("CAPABILITY_PROBE_FAILED")
    if not identity_state(selected.toolchain):
        gaps.append("CAPABILITY_UNAVAILABLE")
    record["gaps"].extend(gaps)
    record["outcome"] = "incomplete" if gaps else "completed"
    record["capability"] = {
        "state": "unsupported" if gaps else "available",
        "checks": selected.settings["enable"]
        if selected.adapter == "cppcheck"
        else [selected.settings["feature"]],
        "effective_config": deepcopy(selected.settings),
    }
    record["configuration"]["effective"] = deepcopy(selected.settings)
    return record


def capabilities(
    request_path: Path, adapter: str, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    if adapter not in {"cppcheck", "asan", "ubsan"}:
        raise InputError("ADAPTER_UNSUPPORTED", "Select a supported complementary adapter")
    selected = load_inputs(request_path, "capabilities", adapter)
    if out is not None:
        output_path(out, [request_path, *selected.inputs], selected.protected)
    with temporary_directory(prefix="score-quality-") as temporary:
        record = probe(selected, Path(temporary), Budget(selected.request["output_limit_bytes"]))
    recheck_controls(selected)
    record["gaps"] = sorted(set(record["gaps"]))
    return (
        0 if record["outcome"] == "completed" else 1,
        seal(record),
        selected.inputs,
        selected.protected,
    )


def run(
    request_path: Path, adapter: str, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    if adapter not in {"cppcheck", "asan", "ubsan"}:
        raise InputError("ADAPTER_UNSUPPORTED", "Select a supported complementary adapter")
    selected = load_inputs(request_path, "run", adapter)
    if out is not None:
        output_path(out, [request_path, *selected.inputs], selected.protected)
    budget = Budget(selected.request["output_limit_bytes"])
    with temporary_directory(prefix="score-quality-") as temporary:
        work = Path(temporary)
        # Capability probe outputs remain separate from the requested component run.
        probe_work = work / "probe"
        probe_work.mkdir()
        capability = probe(selected, probe_work, budget)
        for key in ("generated_binary", "rendered_runtime"):
            selected.settings.pop(key, None)
        record = initial(selected, f"quality_{adapter}_analysis_run")
        record.update(
            capability=capability["capability"],
            baseline=baseline(selected),
            source_integrity="unchanged",
            diagnostics=[],
            processed_units=[],
            phases=[{**p, "name": "probe:" + p["name"]} for p in capability["phases"]],
            artifacts=[{**a, "id": "probe-" + a["id"]} for a in capability["artifacts"]],
        )
        gaps = list(selected.gaps)
        record["gaps"].extend(capability["gaps"])
        source = work / "source"
        source.mkdir()
        for name, data in selected.data.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if capability["outcome"] == "completed":
            fn = cppcheck.analyze if adapter == "cppcheck" else sanitizers.build_and_execute
            phases, artifacts, findings, processed, failures = fn(
                selected, work, budget, selected.request["translation_units"], selected.data
            )
            record["phases"].extend(phases)
            record["artifacts"].extend(artifacts)
            record["diagnostics"] = findings
            record["processed_units"] = processed
            gaps.extend(failures)
        else:
            gaps.append("CAPABILITY_UNAVAILABLE")
        record["configuration"]["effective"] = deepcopy(selected.settings)
        for name, data in selected.data.items():
            try:
                intact = (source / name).read_bytes() == data and (
                    Path(selected.request["root"]) / name
                ).read_bytes() == data
            except OSError:
                intact = False
            if not intact:
                record["source_integrity"] = "changed"
                gaps.append("BASELINE_DRIFT")
        if not identity_state(selected.toolchain):
            gaps.append("CAPABILITY_UNAVAILABLE")
        expected = selected.request["expected_units"]
        processed = record["processed_units"]
        if expected is None:
            gaps.append("EXTRACTION_UNKNOWN")
            missing = []
            unexpected = processed
            adequacy = "unknown"
        else:
            missing = sorted(set(expected) - set(processed))
            unexpected = sorted(set(processed) - set(expected))
            if not expected or not processed:
                gaps.append("EXTRACTION_EMPTY")
            if missing or unexpected:
                gaps.append("EXTRACTION_PARTIAL")
            adequacy = "incomplete" if gaps else "adequate"
        record["extraction"] = {
            "expected_state": "unknown" if expected is None else "declared",
            "expected_units": expected,
            "processed_units": processed,
            "missing_units": missing,
            "unexpected_units": unexpected,
            "adequacy": adequacy,
            "limitations": [
                "Local selected-unit execution; no MISRA/CodeQL/qualified system-header closure"
            ],
        }
        record["gaps"] = sorted(set(record["gaps"] + gaps))
        record["outcome"] = (
            "incomplete" if gaps else "findings" if record["diagnostics"] else "completed"
        )
        if capability["outcome"] == "unavailable":
            record["outcome"] = "unavailable"
    recheck_controls(selected)
    return (
        0 if record["outcome"] == "completed" else 1,
        seal(record),
        selected.inputs,
        selected.protected,
    )
