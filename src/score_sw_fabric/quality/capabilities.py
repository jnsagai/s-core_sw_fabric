"""Measured Clang-Tidy capabilities; installation and authority remain separate."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.models import (
    Budget,
    Inputs,
    environment,
    execute,
    identity_state,
    load_inputs,
    raw_bytes,
)
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.runtime.request import parse_yaml


def base_record(selected: Inputs, kind: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": kind,
        "profile": selected.profile,
        "toolchain": selected.toolchain,
        "configuration": {**selected.request["config"], "header_filter_override": "selected_tree"},
        "capability": {"state": "unknown", "checks": [], "effective_config": None},
        "phases": [],
        "artifacts": [],
        "gaps": sorted(
            set(
                selected.profile["required_obligations"]
                + [
                    "RULE_MAPPING_UNKNOWN",
                    "MANUAL_REVIEW_PENDING",
                    "PRODUCTION_AUTHORITY_UNAVAILABLE",
                    "TOOL_CONFIDENCE_UNKNOWN",
                    *[
                        (
                            "CAPABILITY_NOT_SELECTED:"
                            if a["id"] == "cppcheck"
                            else "ADAPTER_UNIMPLEMENTED:"
                        )
                        + a["id"]
                        for a in selected.profile["analyzers"]
                        if a["id"] != "clang-tidy"
                    ],
                    *[f"CAPABILITY_NOT_SELECTED:{a['id']}" for a in selected.profile["sanitizers"]],
                ]
            )
        ),
        "outcome": "unavailable",
        "origin": "local_unprotected_execution",
        "assurance_eligibility": "not_eligible",
        "engineering_readiness": "not_evaluated",
    }


def probe(selected: Inputs, work: Path, budget: Budget) -> dict[str, Any]:
    record = base_record(selected, "quality_capability_inventory")
    if not identity_state(selected.toolchain):
        record["capability"]["state"] = "unavailable"
        record["gaps"].append("CAPABILITY_UNAVAILABLE")
        return record
    binary = selected.toolchain["tool"]["path"]
    config = work / "native-clang-tidy.yaml"
    config.write_bytes(selected.config)
    source = work / "source"
    source.mkdir(exist_ok=True)
    header_filter = "^" + re.escape(str(source)) + "/"
    common = [binary, f"--config-file={config}", f"--header-filter={header_filter}"]
    env = environment(work, selected.toolchain)
    for name, argv in [
        ("version", [binary, "--version"]),
        ("verify-config", [*common, "--verify-config"]),
        ("list-checks", [*common, "--list-checks"]),
        ("dump-config", [*common, "--dump-config"]),
    ]:
        phase = execute(name, argv, work, selected.request["timeout_seconds"], budget, env)
        record["phases"].append(phase)
        if any(phase[k]["truncated"] for k in ("stdout", "stderr")):
            record["gaps"].append("OUTPUT_TRUNCATED")
            record["outcome"] = "incomplete"
            return record
        if phase["exit_code"] != 0 or phase["timed_out"]:
            record["gaps"].append("PHASE_FAILED")
            record["capability"]["state"] = "unsupported"
            record["outcome"] = "incomplete"
            return record
        text = raw_bytes(phase["stdout"]).decode("utf-8", "replace")
        if name == "version" and (
            not text.splitlines()
            or text.splitlines()[0].strip() != selected.toolchain["tool"]["version"]
        ):
            raise InputError("TOOL_IDENTITY_MISMATCH", "Version differs from selected toolchain")
        if name == "list-checks":
            record["capability"]["checks"] = [
                line.strip()
                for line in text.splitlines()
                if line.startswith("    ") and line.strip()
            ]
        if name == "dump-config":
            record["capability"]["effective_config"] = parse_yaml(
                raw_bytes(phase["stdout"]), "/effective_config"
            )
    if not record["capability"]["checks"] or not isinstance(
        record["capability"]["effective_config"], dict
    ):
        record["gaps"].append("CHECK_CONFIGURATION_INCOMPLETE")
        record["outcome"] = "incomplete"
        return record
    if not identity_state(selected.toolchain):
        record["gaps"].append("CAPABILITY_UNAVAILABLE")
        return record
    record["capability"]["state"] = "available"
    record["outcome"] = "completed"
    return record


def capabilities(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    selected = load_inputs(request_path, "capabilities")
    if out is not None:
        output_path(out, [request_path, *selected.inputs], selected.protected)
    with tempfile.TemporaryDirectory(prefix="score-quality-") as temporary:
        record = probe(selected, Path(temporary), Budget(selected.request["output_limit_bytes"]))
    record["gaps"] = sorted(set(record["gaps"]))
    return (
        0 if record["outcome"] == "completed" else 1,
        seal(record),
        selected.inputs,
        selected.protected,
    )
