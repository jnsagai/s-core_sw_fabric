"""Case-level outcomes for the pinned native Linux QEMU integration suite."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

EXCLUSION_SOURCE = "tests/integration_test/score_test_applications.py"
EXCLUSION_SOURCE_SHA256 = "2618441df4395053340e414c4a54bbe659c2f26310b89a4aa387fc2df7777b13"
EXCLUDED_CASE = "test_gateway_ipc_binding_succeeds_on_target"
EXCLUDED_REASON = "gateway_ipc_binding_test is only split into multiple processes on QNX"
CASES = {
    "test_someipd_started_by_test": {"test_start_someipd_and_gatewayd"},
    "test_someipd_startup": {"test_start_someipd"},
    "test_someipd_sends_someip-sd_message": {"test_start_someipd_and_gatewayd"},
    "test_score_test_applications": {
        "test_application_succeeds_on_target[" + application + "]"
        for application in (
            "gateway_ipc_binding_test",
            "null_serializer_test",
            "socom_stress_test",
            "socom_test",
        )
    }
    | {EXCLUDED_CASE},
    "test_gateway_startup": {"test_start_gatewayd"},
    "test_tcpdump": {
        "test_tcpdump_with_ping_from_target_execute",
        "test_tcpdump_with_ping_from_target",
        "test_tcpdump_with_long_running_ping_from_target",
        "test_killing_tcpdump",
        "test_killing_tcpdump_while_ping_is_running",
    },
}


def case_outcomes(out: Path, result: dict, log: str) -> dict:
    record = {"passed": False, "passed_cases": 0, "platform_exclusions": [], "blockers": []}
    if not re.search(r"Executed 6 out of 6 tests: 6 tests pass\.\s*(?:$|\n)", log):
        record["blockers"].append("All six native targets must execute and pass")
    if result.get("integration_platform") != "linux_qemu":
        record["blockers"].append("Unverified integration platform")
    if result.get("source_hashes", {}).get(EXCLUSION_SOURCE) != EXCLUSION_SOURCE_SHA256:
        record["blockers"].append("Native applicability source changed or missing")
    for target, expected in CASES.items():
        try:
            cases = list(ET.parse(out / "native-artifacts" / target / "test.xml").iter("testcase"))
        except (OSError, ET.ParseError) as error:
            record["blockers"].append(target + ": " + str(error))
            continue
        if len(cases) != len(expected) or {c.get("name") for c in cases} != expected:
            record["blockers"].append(target + ": expected case identities/count differ")
        for case in cases:
            skip = case.findall("skipped")
            if case.findall("failure") or case.findall("error"):
                record["blockers"].append(target + ": case failed: " + str(case.get("name")))
            elif skip:
                if (
                    target == "test_score_test_applications"
                    and case.get("name") == EXCLUDED_CASE
                    and len(skip) == 1
                    and skip[0].get("type") == "pytest.skip"
                    and skip[0].get("message") == EXCLUDED_REASON
                ):
                    record["platform_exclusions"].append(
                        {
                            "target": target,
                            "case": EXCLUDED_CASE,
                            "reason": EXCLUDED_REASON,
                            "source": EXCLUSION_SOURCE,
                            "source_sha256": EXCLUSION_SOURCE_SHA256,
                            "platform": "linux_qemu",
                        }
                    )
                else:
                    record["blockers"].append(
                        target + ": applicable case skipped: " + str(case.get("name"))
                    )
            else:
                record["passed_cases"] += 1
    if record["passed_cases"] != 13 or len(record["platform_exclusions"]) != 1:
        record["blockers"].append(
            "Expected 13 executed applicable cases and one native QNX-only exclusion"
        )
    record["passed"] = not record["blockers"]
    return record
