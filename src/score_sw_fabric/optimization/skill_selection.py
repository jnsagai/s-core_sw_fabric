"""Digest-bound procedural registry and explicit runtime disclosure; no decision authority."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from score_sw_fabric.optimization.common import (
    OptimizationError,
    canonical,
    checked,
    raw_file,
    record,
    safe_file,
)


def registry(root: Path, definitions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not definitions or len(definitions) > 32:
        raise OptimizationError("SKILL_REGISTRY_LIMIT")
    entries = []
    for identifier, definition in sorted(definitions.items()):
        if not identifier.startswith("score-") or "/" in identifier:
            raise OptimizationError("SKILL_ID")
        if set(definition) != {"version", "files"} or "SKILL.md" not in definition["files"]:
            raise OptimizationError("SKILL_DEFINITION")
        files = {}
        for name in sorted(definition["files"]):
            data, raw = raw_file(root, identifier + "/" + name)
            if len(data) > (12000 if name == "SKILL.md" else 32000):
                raise OptimizationError("SKILL_SIZE_LIMIT")
            files[name] = raw
        entries.append(
            {
                "id": identifier,
                "version": definition["version"],
                "files": files,
                "digest": hashlib.sha256(canonical(files)).hexdigest(),
            }
        )
    return record("skill_registry", entries=entries, authority="procedure_only")


def select(
    registered: dict[str, Any], activity: str, mapping: dict[str, list[str]], baseline: str
) -> dict[str, Any]:
    checked(registered, "skill_registry")
    if activity not in mapping or not mapping[activity]:
        raise OptimizationError("SKILL_MAPPING_UNKNOWN")
    by_id = {i["id"]: i for i in registered["entries"]}
    identifiers = sorted(set(mapping[activity]))
    if len(identifiers) > 4 or any(i not in by_id for i in identifiers):
        raise OptimizationError("SKILL_UNAVAILABLE")
    return record(
        "skill_selection",
        activity=activity,
        baseline=baseline,
        registry_digest=registered["digest"],
        mapping_digest=hashlib.sha256(canonical(mapping)).hexdigest(),
        required=[
            {"id": i, "version": by_id[i]["version"], "digest": by_id[i]["digest"]}
            for i in identifiers
        ],
        available_on_demand=[],
        forbidden=sorted(set(by_id) - set(identifiers)),
    )


def render(
    root: Path,
    registered: dict[str, Any],
    selection: dict[str, Any],
    baseline: str,
    *,
    reference: str | None = None,
) -> dict[str, Any]:
    checked(registered, "skill_registry")
    checked(selection, "skill_selection")
    if selection["baseline"] != baseline or selection["registry_digest"] != registered["digest"]:
        raise OptimizationError("SKILL_BASELINE_DRIFT")
    entries = {i["id"]: i for i in registered["entries"]}
    selected = {i["id"] for i in selection["required"]}
    text = []
    bindings = []
    for item in selection["required"]:
        entry = entries[item["id"]]
        if item["digest"] != entry["digest"] or item["version"] != entry["version"]:
            raise OptimizationError("SKILL_DRIFT")
        # Every declared reference is part of the baseline, even when its text remains lazy.
        for raw in entry["files"].values():
            try:
                raw_file(root, raw["path"], raw["sha256"])
            except OptimizationError as exc:
                raise OptimizationError("SKILL_DRIFT") from exc
        if reference is None:
            text.append(safe_file(root, item["id"] + "/SKILL.md").read_text())
            bindings.append(entry["digest"])
    if reference is not None:
        identifier, separator, name = reference.partition("/")
        if not separator or identifier not in selected or name not in entries[identifier]["files"]:
            raise OptimizationError("SKILL_REFERENCE_FORBIDDEN")
        raw = entries[identifier]["files"][name]
        data, _ = raw_file(root, reference, raw["sha256"])
        text = [data.decode()]
        bindings = [raw["sha256"]]
    rendered = "\n".join(text)
    if len(rendered.encode()) > 24000:
        raise OptimizationError("SKILL_SIZE_LIMIT")
    return record(
        "rendered_skill",
        text=rendered,
        sha256=hashlib.sha256(rendered.encode()).hexdigest(),
        baseline=baseline,
        selection_digest=selection["digest"],
        bindings=bindings,
        runtime_delivery="explicit_rendering",
        authority="procedure_only",
    )
