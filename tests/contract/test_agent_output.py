"""007 role result structure and write-scope change checks (AC007-09/14)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.agents.output import check, validate_result
from score_sw_fabric.process_source.reader import InputError
from tests.agent_support import Scenario, git


def _edit(scenario: Scenario) -> None:
    (scenario.workspace / "src").mkdir(exist_ok=True)
    (scenario.workspace / "src/component.cpp").write_text("int f() { return 1; }\n")


def test_in_scope_declared_change_is_within_bounds_not_accepted(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    bundle_path, bundle = scenario.bundle()
    _edit(scenario)
    scenario.note("decision hint")
    status, record, _, protected = check(scenario.check(bundle_path, scenario.result(bundle)))
    assert status == 0 and record["outcome"] == "within_bounds"
    assert record["self_reported_checks"] == [
        {"name": "unit tests", "result": "pass", "origin": "agent_assertion"}
    ]
    assert record["evidence_refs"][0]["verification"] == "not_verified"
    assert record["engineering_readiness"] == "not_evaluated"
    assert len(record["observation_bindings"]) == 1
    assert scenario.workspace in protected


@pytest.mark.parametrize(
    ("action", "declared", "codes"),
    [
        ("outside", ["src/component.cpp", "docs/req.rst"], {"WRITE_OUT_OF_SCOPE"}),
        ("git", ["src/component.cpp"], {"PROTECTED_PATH"}),
        ("undeclared", ["src/component.cpp"], {"UNDECLARED_CHANGE"}),
        ("none", ["src/component.cpp", "src/missing.cpp"], {"DECLARED_NOT_CHANGED"}),
    ],
)
def test_scope_and_declaration_violations_stop(
    tmp_path: Path, action: str, declared: list[str], codes: set[str]
) -> None:
    scenario = Scenario(tmp_path)
    bundle_path, bundle = scenario.bundle()
    _edit(scenario)
    if action == "outside":
        (scenario.workspace / "docs/req.rst").write_text("rewritten\n")
    elif action == "git":
        (scenario.workspace / ".git/hooks/pre-commit").write_text("#!/bin/sh\n")
    elif action == "undeclared":
        (scenario.workspace / "src/extra.cpp").write_text("x\n")
    status, record, _, _ = check(
        scenario.check(bundle_path, scenario.result(bundle, changed_paths=declared))
    )
    assert status == 1 and record["outcome"] == "stopped"
    found = {item["code"] for item in record["reasons"]}
    assert codes <= found


def test_protected_glob_does_not_capture_similar_names(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    bundle_path, bundle = scenario.bundle()
    _edit(scenario)
    (scenario.workspace / ".gitx").write_text("x")
    status, record, _, _ = check(
        scenario.check(
            bundle_path, scenario.result(bundle, changed_paths=["src/component.cpp", ".gitx"])
        )
    )
    assert status == 1
    assert {"code": "WRITE_OUT_OF_SCOPE", "path": ".gitx"} in record["violations"]


@pytest.mark.parametrize(
    "result",
    [
        "not json",
        {"kind": "agent_result"},
        "extra",
        "path",
        "check",
    ],
)
def test_malformed_results_stop(tmp_path: Path, result: Any) -> None:
    scenario = Scenario(tmp_path)
    bundle_path, bundle = scenario.bundle()
    _edit(scenario)
    if result == "extra":
        result = {**scenario.result(bundle), "approved": True}
    elif result == "path":
        result = scenario.result(bundle, changed_paths=["../outside"])
    elif result == "check":
        result = scenario.result(bundle, self_reported_checks=[{"name": "t", "result": "green"}])
    status, record, _, _ = check(scenario.check(bundle_path, result))
    assert status == 1 and record["structure"] == "malformed"
    assert record["reasons"][0]["code"] == "RESULT_MALFORMED"
    assert record["self_reported_checks"] == []


def test_context_mismatch_and_baseline_change_stop(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    bundle_path, bundle = scenario.bundle()
    _edit(scenario)
    status, record, _, _ = check(
        scenario.check(bundle_path, scenario.result(bundle, context_digest="0" * 64))
    )
    assert status == 1 and record["reasons"][0]["code"] == "CONTEXT_MISMATCH"
    git(scenario.workspace, "add", "src")
    git(scenario.workspace, "commit", "-qm", "agent committed")
    status, record, _, _ = check(scenario.check(bundle_path, scenario.result(bundle)))
    assert status == 1
    assert "BASELINE_CHANGED" in {item["code"] for item in record["reasons"]}


def test_result_validator_is_strict() -> None:
    with pytest.raises(InputError):
        validate_result({"schema_version": 2, "kind": "agent_result"})
