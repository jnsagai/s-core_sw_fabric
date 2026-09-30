"""Request builders for 008 safety contract tests over the telemetry-guard fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from tests.agent_support import ROOT, digest, ref, write_json, write_yaml

FIXTURES = ROOT / "tests/fixtures/safety/telemetry_guard"
PROFILE = ROOT / "profiles/s-core-safety-analysis-v1.yaml"
FMEA_FILES = [
    ("requirements.rst", "requirements"),
    ("architecture.rst", "architecture"),
    ("fmea.rst", "analysis"),
]
DFA_FILES = [
    ("requirements.rst", "requirements"),
    ("architecture.rst", "architecture"),
    ("dfa.rst", "analysis"),
]


def copy_version(tmp: Path, version: str, name: str | None = None) -> Path:
    target = tmp / (name or version)
    shutil.copytree(FIXTURES / version, target)
    return target


def file_set(root: Path, names: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "root": str(root),
        "files": [
            {"path": path, "sha256": digest(root / path), "role": role} for path, role in names
        ],
    }


def check_request(
    tmp: Path,
    current: Path,
    *,
    analysis: str = "fmea",
    names: list[tuple[str, str]] | None = None,
    baseline: Path | None = None,
    agent_checks: list[dict[str, Any]] | None = None,
    allocation: str | None = None,
    iteration: int = 1,
    roles: dict[str, Any] | None = None,
    name: str = "check.yaml",
) -> Path:
    selected = names or (FMEA_FILES if analysis == "fmea" else DFA_FILES)
    path = tmp / "control" / name
    write_yaml(
        path,
        {
            "schema_version": 1,
            "kind": "safety_check_request",
            "profile": ref(PROFILE),
            "component": "telemetry_guard",
            "analysis": analysis,
            "current": file_set(current, selected),
            "baseline": None
            if baseline is None
            else file_set(baseline, [item for item in selected if (baseline / item[0]).exists()]),
            "agent_checks": [
                write_json(tmp / "control" / f"agent-check-{index}.json", item)
                for index, item in enumerate(agent_checks or [])
            ],
            "platform_allocation": allocation,
            "iteration": iteration,
            "roles": roles,
            "protected_roots": [str(ROOT)],
        },
    )
    return path


def report(tmp: Path, current: Path, **kwargs: Any) -> dict[str, Any]:
    from score_sw_fabric.safety.analysis import check

    _, record, _, _ = check(check_request(tmp, current, **kwargs))
    return record


def codes(record: dict[str, Any]) -> set[str]:
    return {item["code"] for item in record["findings"]}


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new))
