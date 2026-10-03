"""Bounded repository self-audit of 011 coverage and declared policy, not engineering acceptance."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric.optimization.common import json_object, record
from score_sw_fabric.optimization.skill_selection import registry
from score_sw_fabric.optimization.task_classification import CLASSIFICATION_POLICY
from score_sw_fabric.optimization.token_governor import ENVELOPES


def audit(root: Path) -> dict[str, Any]:
    feature = root / "specs/011-change-impact-and-freshness"
    coverage = yaml.safe_load((feature / "coverage.yaml").read_text())
    spec = (feature / "spec.md").read_text()
    tasks = (feature / "tasks.md").read_text()
    requirements = sorted(set(re.findall(r"\*\*(FR-\d{3})", spec)))
    known_tasks = set(re.findall(r"^- \[[ xX]\] (T\d{3})", tasks, re.MULTILINE))
    failures = []
    if set(requirements) != set(coverage):
        failures.append("REQUIREMENT_COVERAGE")
    for requirement, entry in coverage.items():
        if not set(entry["tasks"]) <= known_tasks:
            failures.append(requirement + ":TASK_LINK")
        for path in entry["code"] + entry["tests"]:
            if not (root / path).is_file():
                failures.append(requirement + ":MISSING_ARTIFACT")
        for path, symbols in entry.get("symbols", {}).items():
            tree = ast.parse((root / path).read_text())
            names = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            }
            if set(symbols) - names:
                failures.append(requirement + ":SYMBOL_LINK")
    policy = yaml.safe_load((root / "policies/optimization-v1.yaml").read_text())
    for name, limits in ENVELOPES.items():
        if policy["operational"].get(name) != limits:
            failures.append("POLICY_ENVELOPE_DRIFT")
    if policy["live_calls"] != "disabled":
        failures.append("LIVE_CALL_POLICY")
    if policy.get("classification") != CLASSIFICATION_POLICY:
        failures.append("CLASSIFICATION_POLICY_DRIFT")
    for identifier in ("T032", "T033"):
        if not re.search(r"^- \[ \] " + identifier + r" HUMAN", tasks, re.MULTILINE):
            failures.append("HUMAN_TASK_MARKER")
    skills = yaml.safe_load((root / "profiles/optimization-skills-v1.yaml").read_text())
    registered = registry(root / ".agents/skills", skills["definitions"])
    if len(registered["entries"]) != 8:
        failures.append("SKILL_SET")
    for required in (
        "contracts/optimization.md",
        "schemas/README.md",
        "acceptance.md",
        "quickstart.md",
    ):
        if not (feature / required).exists():
            failures.append("CONTROL_PLANE_MISSING")
    roadmap = (root / "docs/backlog/roadmap.md").read_text()
    if "011-change-impact-and-freshness" not in roadmap:
        failures.append("ROADMAP_LINK")
    qualification = feature / "evidence/qualification/summary.json"
    measured_fixture = (
        json_object(qualification.read_bytes()).get("live_routine_savings_target")
        if qualification.is_file()
        else None
    )
    projection = feature / "evidence/projection-qualification/summary.json"
    measured_projection = (
        json_object(projection.read_bytes()).get("development_fixture_live_savings_target")
        if projection.is_file()
        else None
    )
    return record(
        "optimization_self_audit",
        state="blocked" if failures else "complete",
        requirements_checked=len(requirements),
        tasks_checked=len(known_tasks),
        skill_registry_digest=registered["digest"],
        failures=sorted(set(failures)),
        implementation_tasks_open=re.findall(r"^- \[ \] (T\d{3}) (?!HUMAN)", tasks, re.MULTILINE),
        human_acceptance="pending",
        live_savings="unmeasured",
        development_fixture_live_savings=measured_fixture,
        development_fixture_projection_live_savings=measured_projection,
    )
