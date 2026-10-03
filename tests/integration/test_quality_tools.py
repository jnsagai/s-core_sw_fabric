"""Genuine local Clang-Tidy execution; no synthetic report replaces this evidence."""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.quality.capabilities import capabilities
from score_sw_fabric.quality.runner import run
from tests.quality_support import ROOT, request


def test_actual_capabilities_and_defect_correction(tmp_path: Path) -> None:
    code, inventory, _, _ = capabilities(request(tmp_path, "capabilities"))
    assert code == 0 and inventory["capability"]["state"] == "available"
    assert "clang-analyzer-core.NullDereference" in inventory["capability"]["checks"]
    assert inventory["capability"]["effective_config"]
    source = tmp_path / "component/check.cpp"
    before = source.read_bytes()
    code, seeded, _, _ = run(request(tmp_path))
    assert code == 1 and source.read_bytes() == before
    assert "clang-analyzer-core.NullDereference" in {d["native_id"] for d in seeded["diagnostics"]}
    assert seeded["extraction"]["adequacy"] == "adequate"
    assert seeded["origin"] == "local_unprotected_execution"
    assert seeded["assurance_eligibility"] == "not_eligible"
    raw = next(a for a in seeded["artifacts"] if a["format"] == "clang-tidy-yaml")
    assert b"clang-analyzer-core.NullDereference" in base64.b64decode(raw["base64"])
    shutil.copy2(ROOT / "tests/fixtures/quality/corrected/check.cpp", source)
    code, corrected, _, _ = run(request(tmp_path))
    assert code == 0 and corrected["outcome"] == "completed"
    assert "clang-analyzer-core.NullDereference" not in {
        d["native_id"] for d in corrected["diagnostics"]
    }
    assert seeded["baseline"]["source_digest"] != corrected["baseline"]["source_digest"]
    assert seeded["baseline"]["full_digest"] != corrected["baseline"]["full_digest"]
    assert corrected["engineering_readiness"] == "not_evaluated"
    assert "RULE_MAPPING_UNKNOWN" in corrected["gaps"]


def test_unknown_and_empty_expected_sets_never_clean(tmp_path: Path) -> None:
    shutil.copy2(ROOT / "tests/fixtures/quality/corrected/check.cpp", tmp_path / "check.cpp")
    request(tmp_path)
    shutil.copy2(tmp_path / "check.cpp", tmp_path / "component/check.cpp")
    for expected in (None, []):
        code, record, _, _ = run(request(tmp_path, expected_units=expected))
        assert code == 1
        assert record["extraction"]["adequacy"] != "adequate"


def test_cli_publication_and_bounded_native_output(tmp_path: Path) -> None:
    path = request(tmp_path)
    out = tmp_path / "out/run.json"
    assert main(["quality", "run", "--request", str(path), "--out", str(out), "--json"]) == 1
    result = json.loads(out.read_text())
    assert result["diagnostics"] and result["source_integrity"] == "unchanged"
    # Small capture truncates dump-config; execution must not continue to a clean claim.
    code, record, _, _ = run(request(tmp_path, output_limit_bytes=1024))
    assert code == 1 and record["outcome"] == "incomplete"
    assert "OUTPUT_TRUNCATED" in record["gaps"]


def test_partial_scope_compile_error_and_suppression_are_not_clean(tmp_path: Path) -> None:
    request(tmp_path)
    source = tmp_path / "component/check.cpp"
    other = tmp_path / "component/other.cpp"
    other.write_text("int additional() { return 0; }\n")
    from tests.quality_support import ref

    refs = [dict(ref(source), path="check.cpp"), dict(ref(other), path="other.cpp")]
    code, record, _, _ = run(
        request(tmp_path, files=refs, expected_units=["check.cpp", "other.cpp"])
    )
    assert code == 1 and "EXTRACTION_PARTIAL" in record["gaps"]
    source.write_text("int main() { return undeclared; }\n")
    code, record, _, _ = run(request(tmp_path))
    assert code == 1 and record["extraction"]["adequacy"] == "incomplete"
    assert "PHASE_FAILED" in record["gaps"]
    source.write_text("int main() { return 0; } // NOLINT\n")
    code, record, _, _ = run(request(tmp_path))
    assert code == 1 and "UNAPPROVED_SUPPRESSION" in record["gaps"]


@pytest.mark.parametrize(
    "directive",
    [
        '#include "value.h"',
        '#/**/include "value.h"',
        '#inc\\\nlude "value.h"',
        '#include /* continued\ncomment */ "value.h"',
        '%:include "value.h"',
    ],
)
def test_selected_header_is_copied_and_diagnosed(tmp_path: Path, directive: str) -> None:
    from tests.quality_support import ref

    request(tmp_path)
    source = tmp_path / "component/check.cpp"
    header = tmp_path / "component/value.h"
    header.write_text("inline int value() { int* pointer = nullptr; return *pointer; }\n")
    source.write_text(directive + "\nint main() { return value(); }\n")
    originals = {path: path.read_bytes() for path in (source, header)}
    refs = [dict(ref(source), path="check.cpp"), dict(ref(header), path="value.h")]
    code, record, _, _ = run(request(tmp_path, files=refs))
    assert code == 1 and record["extraction"]["adequacy"] == "adequate"
    d = next(
        d for d in record["diagnostics"] if d["native_id"] == "clang-analyzer-core.NullDereference"
    )
    assert any(loc["path"] == "value.h" for loc in d["locations"])
    assert record["source_integrity"] == "unchanged"
    assert all(path.read_bytes() == data for path, data in originals.items())
