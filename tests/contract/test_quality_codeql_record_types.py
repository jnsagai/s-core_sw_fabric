"""Malformed retained inspection metadata must refuse without native host reads."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.codeql_dispositions import validate_inspection


@pytest.fixture(scope="module")
def inspected() -> dict[str, Any]:
    fixture = Path("tests/fixtures/quality/codeql/legacy-disposition-packet.json")
    packet = json.loads(fixture.read_bytes())
    return packet["dispositions"][0]["review"]["inspection"]


PATHS = [
    ("profile", "analyzers", 0, "role"),
    ("profile", "analyzers", 0, "state"),
    ("profile", "sanitizers", 0, "state"),
    ("prerequisites",),
    ("prerequisites", 0, "id"),
    ("prerequisites", 0, "state"),
    ("prerequisites", 0, "reasons"),
    ("capability", "installation_state"),
    ("capability", "declared_cli_version"),
    ("capability", "suite_exclusions"),
    ("configuration", "effective", "id"),
    ("configuration", "effective", "status"),
    ("configuration", "effective", "source_root"),
    ("configuration", "effective", "source_lock"),
    ("configuration", "effective", "source_lock", "path"),
    ("configuration", "effective", "source_lock", "sha256"),
    ("configuration", "effective", "scan_config"),
    ("configuration", "effective", "report_patch"),
    ("configuration", "effective", "native_sources"),
    ("configuration", "effective", "native_sources", 0, "commit"),
    ("configuration", "effective", "native_sources", 0, "notice"),
    ("configuration", "effective", "suite"),
    ("source_inspection", "repository"),
    ("source_inspection", "commit"),
    ("source_inspection", "lock"),
    ("source_inspection", "origin"),
    ("source_inspection", "matched_locked_sources"),
    ("source_inspection", "source_build", "state"),
    ("source_inspection", "reporting", "manual_python_version"),
    ("source_inspection", "reporting", "requirements"),
    ("source_inspection", "reporting", "requirements", 0, "bytes"),
    ("source_inspection", "reporting", "eligibility_state"),
    ("pack_inspection", "root"),
    ("pack_inspection", "included_source_state"),
    ("pack_inspection", "included_source_count"),
    ("phases", 0, "name"),
    ("phases", 0, "elapsed_seconds"),
    ("phases", 0, "timed_out"),
    ("inspector",),
    ("inspector", "path"),
    ("inspector", "sha256"),
    ("inspector", "qualification"),
    ("limitations",),
    ("source_integrity",),
    ("toolchain", "tool", "version"),
]


@pytest.mark.parametrize(
    "path,value",
    [(path, value) for path in PATHS for value in (None, {})]
    + [
        (path, [])
        for path in PATHS
        if path[-1]
        not in {
            "prerequisites",
            "reasons",
            "suite_exclusions",
            "requirements",
            "limitations",
        }
    ],
)
def test_malformed_retained_types_refuse_without_host_reads(
    inspected: dict[str, Any],
    path: tuple[Any, ...],
    value: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = copy.deepcopy(inspected)
    node = changed
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(InputError):
        with monkeypatch.context() as guard:
            guard.setattr(Path, "open", lambda *a, **k: pytest.fail("offline host read"))
            guard.setattr(Path, "stat", lambda *a, **k: pytest.fail("offline host probe"))
            validate_inspection(seal(changed))


@pytest.mark.parametrize(
    "target",
    ["source_tree", "locked_tree", "build_tree", "relation", "build_commit", "missing_observation"],
)
def test_retained_tree_summaries_cannot_contradict_original_observations(
    inspected: dict[str, Any], target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    changed = copy.deepcopy(inspected)
    source = changed["source_inspection"]
    if target == "source_tree":
        source["tree"] = "0" * 40
    elif target in {"locked_tree", "build_tree"}:
        source["source_build"][target] = "0" * 40
    elif target == "relation":
        source["source_build"]["state"] = "source_trees_different"
    elif target == "build_commit":
        source["source_build"]["declared_build_commit"] = "0" * 40
    else:
        changed["phases"] = [p for p in changed["phases"] if p["name"] != "source:tree"]
    with pytest.raises(InputError):
        with monkeypatch.context() as guard:
            guard.setattr(Path, "open", lambda *a, **k: pytest.fail("offline host read"))
            guard.setattr(Path, "stat", lambda *a, **k: pytest.fail("offline host probe"))
            validate_inspection(seal(changed))
