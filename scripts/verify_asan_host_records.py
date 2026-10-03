"""Check retained ASan measurements without qualifying their origin or accepting engineering."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from score_sw_fabric.assurance.models import verify_digest
from score_sw_fabric.quality.sanitizers import leak_runtime_gaps


def verify(directory: Path, *, integration: bool = False) -> None:
    records = {}
    for name, outcome in (
        ("capabilities", "completed"),
        ("seeded", "findings"),
        ("corrected", "completed"),
    ):
        record = verify_digest(json.loads((directory / f"{name}.json").read_bytes()), "/" + name)
        expected_kind = (
            "quality_asan_capability_inventory"
            if name == "capabilities"
            else "quality_asan_analysis_run"
        )
        if (
            record["kind"] != expected_kind
            or record["origin"] != "local_unprotected_execution"
            or record["schema_version"] != 1
            or record["outcome"] != outcome
            or record["assurance_eligibility"] != "not_eligible"
            or record["engineering_readiness"] != "not_evaluated"
        ):
            raise ValueError("Unexpected measurement outcome or engineering authority")
        if record["capability"]["state"] != "available":
            raise ValueError("ASan capability is not available")
        names = ["version", "compile:capability.cpp", "link", "runtime"]
        if name != "capabilities":
            names = ["probe:" + phase for phase in names] + ["compile:check.cpp", "link", "runtime"]
        if [phase["name"] for phase in record["phases"]] != names:
            raise ValueError("Required native phases are missing or differ")
        captures = list(record["artifacts"])
        for phase in record["phases"]:
            expected_exit = 55 if name == "seeded" and phase["name"] == "runtime" else 0
            if (
                phase["error"]
                or phase["timed_out"]
                or type(phase["exit_code"]) is not int
                or phase["exit_code"] != expected_exit
                or leak_runtime_gaps(
                    base64.b64decode(phase["stderr"]["base64"], validate=True), "asan"
                )
            ):
                raise ValueError("Native phase did not complete")
            captures.extend([phase["stdout"], phase["stderr"]])
        for capture in captures:
            data = base64.b64decode(capture["base64"], validate=True)
            if (
                capture["truncated"]
                or capture["bytes"] != len(data)
                or capture["sha256"] != hashlib.sha256(data).hexdigest()
            ):
                raise ValueError("Native capture is truncated or its bytes differ")
        records[name] = record
    seeded, corrected = records["seeded"], records["corrected"]
    capability = records["capabilities"]
    for record in (seeded, corrected):
        if (
            record["profile"] != capability["profile"]
            or record["toolchain"] != capability["toolchain"]
        ):
            raise ValueError("Selected profile or toolchain differs")
        for key in ("path", "sha256", "adapter"):
            if record["configuration"][key] != capability["configuration"][key]:
                raise ValueError("Selected configuration differs")
        for key, value in capability["configuration"]["effective"].items():
            if (
                key not in {"generated_binary", "rendered_runtime"}
                and record["configuration"]["effective"].get(key) != value
            ):
                raise ValueError("Selected native runtime settings differ")
    if (
        not any(d["native_id"] == "heap-buffer-overflow" for d in seeded["diagnostics"])
        or corrected["diagnostics"]
    ):
        raise ValueError("Seeded defect or fresh correction is not measured")
    for record in (seeded, corrected):
        if (
            record["extraction"]["adequacy"] != "adequate"
            or record["extraction"]["expected_units"] != ["check.cpp"]
            or record["processed_units"] != ["check.cpp"]
            or record["source_integrity"] != "unchanged"
        ):
            raise ValueError("Source integrity or native scope is incomplete")
    if seeded["baseline"]["source_digest"] == corrected["baseline"]["source_digest"]:
        raise ValueError("Corrected source is not a new baseline")
    if integration:
        original = (directory / "integration.xml").read_bytes()
        if len(original) > 1048576:
            raise ValueError("Integration report exceeds retention bound")
        suites = ET.fromstring(original).findall("testsuite")
        if len(suites) != 1 or any(
            suites[0].get(key) != expected
            for key, expected in (
                ("tests", "3"),
                ("errors", "0"),
                ("failures", "0"),
                ("skipped", "0"),
            )
        ):
            raise ValueError("The three required ASan integration tests have not passed")
    print(
        "Original sealed ASan capability, defect and fresh correction verified; "
        "no engineering acceptance"
    )


if __name__ == "__main__":
    if len(sys.argv) not in {2, 3} or (len(sys.argv) == 3 and sys.argv[2] != "--integration"):
        raise SystemExit("Usage: verify_asan_host_records.py EVIDENCE_DIRECTORY [--integration]")
    verify(Path(sys.argv[1]), integration=len(sys.argv) == 3)
