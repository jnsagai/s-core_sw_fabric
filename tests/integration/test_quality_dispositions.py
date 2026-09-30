"""Real local executions establish observed corrections, never engineering approval."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.quality import complementary, dispositions, imports, runner
from tests.quality_disposition_support import change_draft, change_request, selection, write
from tests.quality_support import ROOT, complementary_request, ref, request


@pytest.mark.parametrize("adapter", ["clang-tidy", "cppcheck", "asan", "ubsan"])
def test_real_correction_and_immutable_stale_history(tmp_path: Path, adapter: str) -> None:
    current = (
        request(tmp_path) if adapter == "clang-tidy" else complementary_request(tmp_path, adapter)
    )
    _, original, _, _ = (
        runner.run(current) if adapter == "clang-tidy" else complementary.run(current, adapter)
    )
    assert original["outcome"] == "findings"
    source = tmp_path / "component/check.cpp"
    seeded_bytes = source.read_bytes()
    path = selection(tmp_path, original, current, adapter)
    pending_path = tmp_path / "pending.json"
    assert main(["quality", "disposition", "--request", str(path), "--out", str(pending_path)]) == 1
    pending_bytes = pending_path.read_bytes()
    assert source.read_bytes() == seeded_bytes
    clean = ROOT / (
        "tests/fixtures/quality/corrected/check.cpp"
        if adapter in {"clang-tidy", "cppcheck"}
        else "tests/fixtures/quality/sanitizers/corrected/check.cpp"
    )
    shutil.copy2(clean, source)
    current_record = json.loads(current.read_text())
    current_record["files"] = [dict(ref(source), path="check.cpp")]
    write(current, current_record)
    change_request(
        path,
        action="check_correction",
        current={"adapter": adapter, "request": ref(current)},
        previous=ref(pending_path),
    )
    corrected_path = tmp_path / "corrected.json"
    assert (
        main(
            [
                "quality",
                "disposition",
                "--request",
                str(path),
                "--out",
                str(corrected_path),
                "--json",
            ]
        )
        == 0
    )
    corrected_bytes = corrected_path.read_bytes()
    observed = json.loads(corrected_bytes)
    assert observed["state"] == "corrected" and observed["revision"] == 2
    assert observed["fresh_run"]["origin"] == "local_unprotected_execution"
    assert observed["fresh_run"]["diagnostics"] == []
    assert observed["fresh_run"]["artifacts"] or observed["fresh_run"]["phases"]
    assert observed["fresh_run"]["extraction"]["adequacy"] == "adequate"
    assert observed["fresh_run"]["baseline"] == observed["current_baseline"]
    assert observed["previous"]["digest"] == json.loads(pending_bytes)["digest"]
    assert source.read_bytes() == clean.read_bytes()
    # A further edit invalidates the previous current baseline; no old clean report is reused.
    source.write_bytes(source.read_bytes() + b"\n// changed after correction observation\n")
    current_record["files"] = [dict(ref(source), path="check.cpp")]
    write(current, current_record)
    change_request(
        path,
        action="draft",
        current={"adapter": adapter, "request": ref(current)},
        previous=ref(corrected_path),
    )
    _, stale, _, _ = dispositions.review(path)
    assert stale["state"] == "stale" and stale["revision"] == 3
    assert "DISPOSITION_STALE" in stale["reasons"] and stale["fresh_run"] is None
    assert corrected_path.read_bytes() == corrected_bytes
    assert pending_path.read_bytes() == pending_bytes
    assert stale["engineering_readiness"] == "not_evaluated"


def test_imported_native_contributors_stay_pending_and_cannot_prove_correction(
    tmp_path: Path,
) -> None:
    _, original, _, _ = imports.import_outputs(ROOT / "examples/quality/native-import.yaml")
    current = request(tmp_path, component=original["baseline"]["component"])
    source = tmp_path / "component/check.cpp"
    source.write_bytes((ROOT / "tests/fixtures/quality/extraction/source/check.cpp").read_bytes())
    current = request(tmp_path, component=original["baseline"]["component"])
    path = selection(tmp_path, original, current)
    change_draft(path, requested_kind="deviation")
    _, proposed, _, _ = dispositions.review(path)
    assert proposed["state"] == "pending_review"
    assert proposed["subject"]["origin_class"] == "fixture"
    assert proposed["subject"]["finding"]["contributors"] == original["findings"][0]["contributors"]
    assert "DEVIATION_POLICY_UNKNOWN" in proposed["reasons"]
    change_draft(path, requested_kind="correction")
    change_request(path, action="check_correction")
    _, blocked, _, _ = dispositions.review(path)
    assert blocked["state"] == "blocked" and blocked["fresh_run"] is None
    assert "IMPORTED_CORRECTION_SCOPE_UNVERIFIED" in blocked["reasons"]
