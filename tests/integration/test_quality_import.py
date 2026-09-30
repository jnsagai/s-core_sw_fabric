"""Import genuine local native outputs, without promoting their origin or authority."""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.quality import complementary, runner
from tests.quality_import_support import from_local_run
from tests.quality_support import ROOT, complementary_request, ref, request


@pytest.mark.parametrize("adapter", ["clang-tidy", "cppcheck", "asan", "ubsan"])
def test_genuine_outputs_seed_fix_and_portable_import(adapter: str, tmp_path: Path) -> None:
    selected = (
        request(tmp_path) if adapter == "clang-tidy" else complementary_request(tmp_path, adapter)
    )
    source = tmp_path / "component"
    before = (source / "check.cpp").read_bytes()
    result = (
        runner.run(selected) if adapter == "clang-tidy" else complementary.run(selected, adapter)
    )
    assert result[0] == 1 and result[1]["outcome"] == "findings"
    imported = from_local_run(tmp_path, adapter, result[1], source)
    out = tmp_path / "imported.json"
    with patch(
        "score_sw_fabric.quality.models.execute", side_effect=AssertionError("tool executed")
    ):
        assert (
            main(["quality", "import", "--request", str(imported), "--out", str(out), "--json"])
            == 1
        )
    record = json.loads(out.read_text())
    assert record["outcome"] == "findings" and record["extraction"]["adequacy"] == "adequate"
    assert (
        record["origin"] == "imported_unverified"
        and record["assurance_eligibility"] == "not_eligible"
    )
    assert (source / "check.cpp").read_bytes() == before
    assert {f["native_id"] for f in record["findings"]} == {
        d["native_id"] for d in result[1]["diagnostics"]
    }
    original = next(a for a in record["artifacts"] if a["id"] == "original-analysis-run")
    assert json.loads(base64.b64decode(original["raw"]["base64"])) == result[1]
    clean = ROOT / (
        "tests/fixtures/quality/corrected/check.cpp"
        if adapter in {"clang-tidy", "cppcheck"}
        else "tests/fixtures/quality/sanitizers/corrected/check.cpp"
    )
    shutil.copy2(clean, source / "check.cpp")
    r = json.loads(selected.read_text())
    r["files"] = [dict(ref(source / "check.cpp"), path="check.cpp")]
    selected.write_text(json.dumps(r))
    result = (
        runner.run(selected) if adapter == "clang-tidy" else complementary.run(selected, adapter)
    )
    assert result[0] == 0
    imported = from_local_run(tmp_path, adapter, result[1], source)
    with patch(
        "score_sw_fabric.quality.models.execute", side_effect=AssertionError("tool executed")
    ):
        assert main(["quality", "import", "--request", str(imported), "--out", str(out)]) == 0
    corrected = json.loads(out.read_text())
    assert corrected["findings"] == [] and corrected["engineering_readiness"] == "not_evaluated"
    assert corrected["baseline"]["source_digest"] != record["baseline"]["source_digest"]
