"""Host handoff record checks use preserved historical bytes, never current capability proof."""

import base64
import json
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.quality.models import Budget
from scripts.verify_asan_host_records import verify


def historical_records(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[2] / "specs/010-misra-quality-and-deviations/evidence"
    for target, source in (
        ("capabilities", "asan-capabilities"),
        ("seeded", "asan-seeded-run"),
        ("corrected", "asan-corrected-run"),
    ):
        (tmp_path / f"{target}.json").write_bytes((root / f"{source}.json").read_bytes())
    return tmp_path


def test_preserved_historical_asan_records_are_consistent(tmp_path: Path) -> None:
    verify(historical_records(tmp_path))


@pytest.mark.parametrize(
    "mutation",
    [
        "exit",
        "missing_runtime",
        "leak_failure",
        "origin",
        "kind",
        "configuration",
        "truncated",
        "raw_bytes",
    ],
)
def test_invalid_host_record_still_refuses_when_resealed(tmp_path: Path, mutation: str) -> None:
    directory = historical_records(tmp_path)
    path = directory / "corrected.json"
    record = json.loads(path.read_bytes())
    if mutation == "exit":
        record["phases"][-1]["exit_code"] = 1
    elif mutation == "missing_runtime":
        record["phases"].pop()
    elif mutation == "leak_failure":
        original = base64.b64decode(record["phases"][-1]["stderr"]["base64"])
        record["phases"][-1]["stderr"] = Budget(1048576).capture(
            original + b"\nLeakSanitizer has encountered a fatal error.\n"
        )
    elif mutation == "origin":
        record["origin"] = "fixture"
    elif mutation == "kind":
        record["kind"] = "quality_ubsan_analysis_run"
    elif mutation == "configuration":
        record["configuration"]["sha256"] = "0" * 64
    elif mutation == "truncated":
        record["phases"][-1]["stderr"]["truncated"] = True
    else:
        record["phases"][-1]["stderr"]["sha256"] = "0" * 64
    path.write_text(json.dumps(seal(record)))
    with pytest.raises(ValueError):
        verify(directory)


@pytest.mark.parametrize(
    "attributes",
    [
        'tests="2" errors="0" failures="0" skipped="0"',
        'tests="3" errors="0" failures="1" skipped="0"',
        'tests="3" errors="0" failures="0" skipped="1"',
    ],
)
def test_resume_requires_all_three_integration_passes(tmp_path: Path, attributes: str) -> None:
    directory = historical_records(tmp_path)
    (directory / "integration.xml").write_text(
        f"<testsuites><testsuite {attributes}/></testsuites>"
    )
    with pytest.raises(ValueError):
        verify(directory, integration=True)
