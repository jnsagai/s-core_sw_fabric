"""Typed planning records; target engineering authority remains external."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict

ScopeKind = Literal["feature", "component", "module", "platform"]
CoverageState = Literal["selected", "outside_scope", "unresolved"]
Applicability = Literal["required", "unresolved"]
Disposition = Literal[
    "create", "update", "reuse", "tailored_out", "external_obligation", "unresolved"
]


class Finding(TypedDict):
    code: str
    location: str
    message: str
    required_action: str
    instance_id: str | None
    native_ref: dict[str, Any] | None


class CoverageEntry(TypedDict):
    native_ref: dict[str, Any]
    scope: dict[str, str]
    state: CoverageState
    rule_ids: list[str]
    rationale: str
    instance_ids: list[str]
    finding_codes: list[str]


class WorkProductInstance(TypedDict):
    instance_id: str
    identity: dict[str, str]
    binding: dict[str, Any]
    purpose: str
    requesting_scopes: list[str]
    origin_rule_ids: list[str]
    applicability: Applicability
    requested_disposition: Disposition
    effective_disposition: Disposition
    rationale: str
    artifact_bindings: list[dict[str, Any]]
    decision_refs: list[str]
    required_reviews: list[dict[str, Any]]
    template_refs: list[dict[str, Any]]
    dependency_ids: list[str]
    finding_codes: list[str]


@dataclass(frozen=True)
class PlanningInputs:
    intake_path: Path
    intake: dict[str, Any]
    catalogue_path: Path
    catalogue_transport_sha256: str
    catalogue_digest: str
    profile: dict[str, Any]
    mapping: dict[str, Any]
    inventory: dict[str, Any]
    decisions: dict[str, Any]
    semantic_digests: dict[str, str]
    input_paths: tuple[Path, ...]
    reference_roots: tuple[Path, ...]
    output_root: Path
