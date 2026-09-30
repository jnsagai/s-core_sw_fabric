"""Run Clang-Tidy on verified disposable bytes; preserve native results and scope gaps."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.capabilities import probe
from score_sw_fabric.quality.models import (
    Accumulator,
    Budget,
    baseline,
    environment,
    execute,
    identity_state,
    load_inputs,
    raw_bytes,
)
from score_sw_fabric.quality.native_outputs import diagnostics
from score_sw_fabric.runtime.models import output_path


def run(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    selected = load_inputs(request_path, "run")
    if out is not None:
        output_path(out, [request_path, *selected.inputs], selected.protected)
    r = selected.request
    budget = Budget(r["output_limit_bytes"])
    with tempfile.TemporaryDirectory(prefix="score-quality-") as temporary:
        work = Path(temporary)
        record = probe(selected, work, budget)
        record["kind"] = "quality_analysis_run"
        record.update(
            baseline=baseline(selected),
            processed_units=[],
            diagnostics=[],
            source_integrity="unchanged",
        )
        source = work / "source"
        for name, data in selected.data.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        failures = list(selected.gaps)
        if record["outcome"] == "completed":
            for index, unit in enumerate(r["translation_units"]):
                fixes = work / f"diagnostics-{index}.yaml"
                argv = [
                    selected.toolchain["tool"]["path"],
                    f"--config-file={work / 'native-clang-tidy.yaml'}",
                    "--header-filter=^" + re.escape(str(source)) + "/",
                    f"--export-fixes={fixes}",
                    str(source / unit),
                    "--",
                    "-std=c++17",
                    *[f"-I{source / d}" for d in r["include_dirs"]],
                    *[f"-D{d}" for d in r["defines"]],
                ]
                phase = execute(
                    f"analyze:{unit}",
                    argv,
                    work,
                    r["timeout_seconds"],
                    budget,
                    environment(work, selected.toolchain),
                )
                record["phases"].append(phase)
                truncated = any(phase[k]["truncated"] for k in ("stdout", "stderr"))
                ds = []
                if fixes.is_file():
                    acc = Accumulator(budget, "clang-tidy-yaml")
                    with fixes.open("rb") as stream:
                        while chunk := stream.read(65536):
                            acc.add(chunk)
                    artifact = {
                        "id": f"diagnostics-{index}",
                        "translation_unit": unit,
                        **acc.record(),
                    }
                    record["artifacts"].append(artifact)
                    truncated = truncated or artifact["truncated"]
                    if not artifact["truncated"]:
                        try:
                            ds = diagnostics(
                                raw_bytes(artifact), artifact["id"], source, selected.data
                            )
                        except InputError as exc:
                            failures.append(exc.code)
                elif phase["exit_code"] != 0:
                    failures.append("REPORT_MISSING")
                elif any(
                    re.search(rb"\b(?:warning|error):", raw_bytes(phase[k]))
                    for k in ("stdout", "stderr")
                ):
                    failures.append("REPORT_MISSING")
                record["diagnostics"].extend(ds)
                if len(record["diagnostics"]) > 10000:
                    record["diagnostics"] = record["diagnostics"][:10000]
                    failures.append("FINDING_LIMIT_EXCEEDED")
                # Clang-Tidy may omit export-fixes on a clean TU; retain native stdout.
                compiler_errors = any(
                    d["native_id"].startswith("clang-diagnostic-error") for d in ds
                )
                if truncated:
                    failures.append("OUTPUT_TRUNCATED")
                if phase["timed_out"] or phase["error"] or compiler_errors:
                    failures.append("PHASE_FAILED")
                elif phase["exit_code"] not in (0, 1) or (phase["exit_code"] == 1 and not ds):
                    failures.append("PHASE_FAILED")
                elif not truncated:
                    record["processed_units"].append(unit)
                if truncated or phase["timed_out"] or budget.remaining == 0:
                    break
        else:
            failures.append("CAPABILITY_UNAVAILABLE")
        # No --fix; separately check both disposable files and original selected source bytes.
        for name, data in selected.data.items():
            try:
                intact = (source / name).read_bytes() == data and (
                    Path(r["root"]) / name
                ).read_bytes() == data
            except OSError:
                intact = False
            if not intact:
                record["source_integrity"] = "changed"
                failures.append("BASELINE_DRIFT")
        if not identity_state(selected.toolchain):
            failures.append("CAPABILITY_UNAVAILABLE")
        expected, processed = r["expected_units"], record["processed_units"]
        if expected is None:
            adequacy = "unknown"
            failures.append("EXTRACTION_UNKNOWN")
            missing, unexpected = [], processed
        else:
            missing, unexpected = (
                sorted(set(expected) - set(processed)),
                sorted(set(processed) - set(expected)),
            )
            if not expected or not processed:
                failures.append("EXTRACTION_EMPTY")
            if missing or unexpected:
                failures.append("EXTRACTION_PARTIAL")
            adequacy = "incomplete" if failures else "adequate"
        record["extraction"] = {
            "expected_state": "unknown" if expected is None else "declared",
            "expected_units": expected,
            "processed_units": processed,
            "missing_units": missing,
            "unexpected_units": unexpected,
            "adequacy": adequacy,
            "limitations": [
                "Selected C++ translation units only; host system headers/ABI unqualified",
                "No CodeQL extraction or compliance coverage is inferred",
            ],
        }
        record["gaps"] = sorted(set(record["gaps"] + failures))
        if failures:
            record["outcome"] = (
                "incomplete" if record["outcome"] != "unavailable" else "unavailable"
            )
        else:
            record["outcome"] = "findings" if record["diagnostics"] else "completed"
    return (
        0 if record["outcome"] == "completed" else 1,
        seal(record),
        selected.inputs,
        selected.protected,
    )
