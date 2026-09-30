"""Native design and source traceability checks."""

from __future__ import annotations

from pathlib import Path

from score_sw_fabric.verification.design import design
from tests.verification_support import files, fixture, request


def test_design_pass_and_faults(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    status, result, _, _ = design(request(tmp_path, "design"))
    assert status == 0
    assert result["outcome"] == "complete"
    assert len(result["units"]) == 2
    assert all(item["implemented_by"] for item in result["requirements"])

    doc = root / "docs/detailed_design.rst"
    doc.write_text(
        doc.read_text().replace("Static Diagrams for Unit Interactions", "Other diagram")
    )
    status, result, _, _ = design(request(tmp_path, "design"))
    assert status == 1
    assert "DESIGN_SECTION_MISSING" in {item["code"] for item in result["findings"]}

    source = root / "src/telemetry_guard.cpp"
    source.write_text(
        source.read_text().replace(
            "comp_req__telemetry_guard__stale_detection", "comp_req__unknown"
        )
    )
    status, result, _, _ = design(
        request(
            tmp_path,
            "design",
            sources=files(root, ["src/telemetry_guard.h", "src/telemetry_guard.cpp"]),
        )
    )
    assert status == 1
    assert "TAG_UNRESOLVED" in {item["code"] for item in result["findings"]}
