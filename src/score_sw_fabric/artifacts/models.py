"""Strict records and fixed boundaries for native artifact operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict

from score_sw_fabric.process_source.reader import InputError

ArtifactOperation = Literal["index", "candidate", "trace"]
TraceValidation = Literal["not_requested", "passed", "blocked"]

CAPABILITY_NAMES = (
    "registration",
    "execution",
    "evidence",
    "acceptance",
    "engineering_readiness",
    "release",
)

DEFAULT_LIMITS: dict[str, int] = {
    "control_bytes": 64 * 1024 * 1024,
    "package_bytes": 64 * 1024 * 1024,
    "target_bytes": 64 * 1024 * 1024,
    "files": 10_000,
    "text_file_bytes": 2 * 1024 * 1024,
    "entities": 100_000,
    "obligations": 100_000,
    "relations": 500_000,
    "edits": 10_000,
    "findings": 20_000,
    "native_output_bytes": 8 * 1024 * 1024,
    "native_timeout_seconds": 1_800,
}


def enforce_limit(
    limits: dict[str, int],
    name: str,
    observed: int,
    code: str,
    message: str,
    *,
    semantic: bool = False,
) -> None:
    """Enforce an inclusive declared maximum with a stable error class and code."""

    if type(observed) is not int or observed < 0:
        raise InputError("LIMIT_VALUE", f"Invalid observed value for {name}")
    maximum = limits.get(name)
    if type(maximum) is not int or maximum < 1:
        raise InputError("ARTIFACT_LIMITS", f"Invalid or missing limit {name}")
    if observed <= maximum:
        return
    if semantic:
        raise ArtifactSemanticError(code, message)
    raise InputError(code, message)


class Finding(TypedDict):
    code: str
    message: str
    subjects: list[str]
    source: dict[str, Any] | None
    required_action: str


def unevaluated_capabilities() -> dict[str, str]:
    return {name: "not_evaluated" for name in CAPABILITY_NAMES}


def finding(
    code: str,
    message: str,
    *subjects: str,
    source: dict[str, Any] | None = None,
    action: str = "Correct the native source or reviewed profile and rerun.",
) -> Finding:
    return {
        "code": code,
        "message": message,
        "subjects": list(subjects),
        "source": source,
        "required_action": action,
    }


class ArtifactSemanticError(Exception):
    """Well-formed native content failed semantic validation (CLI exit 1)."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        findings: list[Finding] | None = None,
        pointer: str = "",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.pointer = pointer
        self.findings = findings or []
        self.action = "Correct the native artifact or reviewed policy and rerun."
        self.source_ref: dict[str, Any] | None = None
        self.native_id: str | None = None


@dataclass(frozen=True)
class ArtifactInputs:
    request_path: Path
    request: dict[str, Any]
    operation: ArtifactOperation
    snapshot: dict[str, Any]
    artifact_profile: dict[str, Any]
    trace_profile: dict[str, Any] | None
    plan: dict[str, Any] | None
    workflow_package: dict[str, Any] | None
    semantic_digests: dict[str, str]
    input_paths: tuple[Path, ...]
    snapshot_root: Path
    output_root: Path
    protected_roots: tuple[Path, ...]
    local_paths: dict[str, Any]
