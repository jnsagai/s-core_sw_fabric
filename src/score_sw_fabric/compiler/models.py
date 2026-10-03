"""Strict compiler records and limits; runtime authority remains external."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NotRequired, TypedDict

ActionType = Literal[
    "agent",
    "prompt",
    "command",
    "deterministic_check",
    "human",
    "conditional",
    "parallel",
    "parallel_fan_in",
]
NativeType = Literal[
    "start",
    "exit",
    "agent",
    "prompt",
    "command",
    "human",
    "conditional",
    "parallel",
    "parallel.fan_in",
]


class Origin(TypedDict):
    kind: Literal["upstream_process", "reviewed_project_configuration", "authorized_human_decision"]
    source_ref: dict[str, Any]
    pointer: str
    decision_ref: str | None
    rationale: str


class ExecutionNode(TypedDict):
    id: str
    key: dict[str, Any]
    ref: str
    action_type: str
    native_type: str
    purpose: str
    label: str
    instance_ids: list[str]
    role: str
    allowed_inputs: list[str]
    allowed_paths: list[str]
    expected_outputs: list[str]
    data_destinations: list[str]
    write_scope: list[str]
    tool_profile: str
    model_capability: str
    budget: dict[str, int]
    completion_predicate: str
    evidence_expectation: str
    fallible_outcomes: list[str]
    prohibited_authority: list[str]
    support_files: list[str]
    command_file: NotRequired[str]
    origins: list[Origin]


class ExecutionEdge(TypedDict):
    id: str
    key: dict[str, Any]
    source: str
    target: str
    edge_type: str
    outcome: str | None
    condition: str | None
    loop_id: str | None
    origins: list[Origin]


class ValidationFinding(TypedDict):
    code: str
    phase: str
    message: str
    subjects: list[str]
    path: list[str]
    required_action: str


@dataclass(frozen=True)
class CompilerInputs:
    request_path: Path
    request: dict[str, Any]
    plan: dict[str, Any]
    mapping: dict[str, Any]
    compiler_profile: dict[str, Any]
    validator_profile: dict[str, Any]
    semantic_digests: dict[str, str]
    input_paths: tuple[Path, ...]
    output_root: Path
    protected_roots: tuple[Path, ...]


class CompilerSemanticError(Exception):
    """Well-formed inputs violate deterministic compiler semantics (CLI exit 1)."""

    def __init__(
        self,
        code: str,
        message: str,
        pointer: str = "",
        findings: list[ValidationFinding] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.pointer = pointer
        self.action = "Correct the reviewed source mapping and compile again."
        self.source_ref: dict[str, Any] | None = None
        self.native_id: str | None = None
        self.findings = findings or []
