"""Strict shared identities and bounded records for assurance version 1."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any, Literal, NotRequired, TypedDict

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError

SHA_CHARS = frozenset("0123456789abcdef")
STABLE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,255}$")
DOMAINS = frozenset({"fixture_contract", "production"})
ORIGINS = frozenset(
    {"protected_observed", "imported_verified", "fixture_replay", "agent_assertion"}
)
OUTCOMES = frozenset({"pass", "fail", "blocked", "not_evaluated", "not_applicable", "stale"})
PREDICATE_STATES = frozenset(
    {"satisfied", "failed", "blocked", "not_evaluated", "not_applicable", "stale"}
)
MAX_CONTROL_BYTES = 64 * 1024 * 1024
MAX_PACKAGE_BYTES = MAX_CONTROL_BYTES
MAX_PREDICATES = 100_000
MAX_EVIDENCE = 100_000
MAX_DECISIONS = 10_000
MAX_REFERENCES = 10_000
MAX_FINDINGS = 20_000
MAX_DEPTH = 32


GateOutcome = Literal["pass", "fail", "blocked", "not_evaluated", "not_applicable", "stale"]
EvidenceOrigin = Literal[
    "protected_observed", "imported_verified", "fixture_replay", "agent_assertion"
]
AssuranceDomain = Literal["fixture_contract", "production"]


class ScopeRecord(TypedDict):
    kind: str
    id: str
    purpose: str


class ReasonRecord(TypedDict):
    code: str
    subject_ref: str
    required_action: str


class SubjectManifest(TypedDict):
    schema_version: Literal[1]
    kind: Literal["assurance_subject"]
    assurance_domain: AssuranceDomain
    scope: ScopeRecord
    plan: dict[str, Any]
    artifact_candidate: dict[str, Any]
    artifact_report: dict[str, Any] | None
    source_baselines: list[dict[str, Any]]
    process_baseline: dict[str, Any]
    toolchain: dict[str, Any]
    profiles: dict[str, Any]
    policy_bindings: dict[str, Any]
    expected_obligation_ids: list[str]
    file_closure: list[dict[str, Any]]
    limitations: list[str]
    digest: str


class TrustProfile(TypedDict):
    schema_version: Literal[1]
    kind: Literal["assurance_trust_profile"]
    id: str
    assurance_domain: AssuranceDomain
    authority_source: dict[str, Any]
    issuer_keys: list[dict[str, Any]]
    identity_providers: list[dict[str, Any]]
    role_assignments: list[dict[str, Any]]
    independence_rules: list[dict[str, Any]]
    import_rules: list[dict[str, Any]]
    revocations: list[dict[str, Any]]
    time_authorities: list[dict[str, Any]]
    limits: dict[str, int]
    status: str
    digest: str


class SignedReceipt(TypedDict):
    schema_version: Literal[1]
    kind: Literal["signed_receipt"]
    assurance_domain: AssuranceDomain
    payload_kind: str
    payload_digest: str
    issuer_id: str
    key_id: str
    algorithm: Literal["Ed25519"]
    issued_at: str
    nonce_or_sequence: str
    signature: str
    receipt_digest: str


class EvidenceRecord(TypedDict):
    schema_version: Literal[1]
    kind: Literal["assurance_evidence"]
    evidence_id: str
    origin_class: EvidenceOrigin
    assurance_domain: AssuranceDomain
    subject_digest: str
    scope: ScopeRecord
    obligation_ids: list[str]
    inputs: list[dict[str, str]]
    process_baseline: dict[str, Any]
    tool: dict[str, str]
    execution_policy_digest: str
    profile_digests: dict[str, Any]
    collector_id: str
    started_at: str
    finished_at: str
    termination: str
    raw_outputs: list[dict[str, Any]]
    measurements: dict[str, bool]
    result: Literal["pass", "fail", "unknown"]
    limits: dict[str, int]
    exclusions: list[str]
    receipt_ref: str | None
    import_chain: list[dict[str, Any]]
    limitations: list[str]
    digest: str


class HumanDecision(TypedDict):
    schema_version: Literal[1]
    kind: Literal["assurance_decision"]
    decision_id: str
    assurance_domain: AssuranceDomain
    actor_id: str
    role: str
    authority_ref: str
    identity_provider: str
    authentication_method: str
    independence: dict[str, Any]
    subject_digest: str
    scope: ScopeRecord
    obligation_ids: list[str]
    gate_ids: list[str]
    policy_digest: str
    outcome: str
    rationale: str
    conditions: list[str]
    issued_at: str
    valid_from: str
    valid_until: str
    supersedes: str | None
    receipt_ref: str | None
    digest: str
    baseline_change: NotRequired[dict[str, Any]]


class GatePolicy(TypedDict):
    schema_version: Literal[1]
    kind: Literal["assurance_gate_policy"]
    id: str
    assurance_domain: AssuranceDomain
    authority_source: dict[str, Any]
    applicable_scopes: list[ScopeRecord]
    subject_requirements: dict[str, Any]
    expected_set_rule: dict[str, str]
    predicates: list[dict[str, Any]]
    required_roles: list[str]
    independence_rules: list[str]
    allowed_evidence: list[dict[str, Any]]
    freshness_rules: dict[str, Any]
    not_applicable_rules: dict[str, Any]
    outcome_routes: dict[str, str]
    limits: dict[str, int]
    status: str
    digest: str


class GateResult(TypedDict):
    schema_version: Literal[1]
    kind: Literal["assurance_gate_result"]
    gate_id: str
    assurance_domain: AssuranceDomain
    scope: ScopeRecord
    subject_digest: str
    policy_digest: str
    trust_profile_digest: str
    evaluator_identity: str
    as_of: str
    time_basis_ref: str
    outcome: GateOutcome
    evaluation_mode: str
    expected_predicate_ids: list[str]
    predicate_results: list[dict[str, Any]]
    evidence_digests: list[str]
    decision_digests: list[str]
    unmet_predicate_ids: list[str]
    unmet_obligation_ids: list[str]
    reason_codes: list[str]
    required_actions: list[str]
    next_route: str
    limitations: list[str]
    digest: str
    freshness: NotRequired[dict[str, Any]]


class PortableAssessment(TypedDict):
    schema_version: Literal[1]
    kind: Literal["assurance_assessment"]
    subject: dict[str, Any]
    policy_refs: list[dict[str, Any]]
    trust_context_refs: list[dict[str, Any]]
    evidence_records: list[EvidenceRecord]
    decision_records: list[HumanDecision]
    receipts: list[SignedReceipt]
    gate_results: list[GateResult]
    raw_output_refs: list[dict[str, Any]]
    history_refs: list[dict[str, Any]]
    readable_report: dict[str, Any]
    limitations: list[str]
    digest: str


class AssuranceSemanticError(Exception):
    """Well-formed input whose assurance predicate is not satisfied."""

    def __init__(self, code: str, message: str, pointer: str = "", action: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.pointer = pointer
        self.action = action or "Resolve the named assurance predicate and reassess."


def exact(value: Any, fields: set[str], pointer: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        keys = set(value) if isinstance(value, dict) else set()
        raise InputError(
            "FIELD_UNKNOWN",
            f"{pointer}: unexpected={sorted(keys - fields)}, missing={sorted(fields - keys)}",
            pointer,
        )
    return value


def version(value: Any, kind: str, fields: set[str], pointer: str) -> dict[str, Any]:
    record = exact(value, fields | {"schema_version", "kind"}, pointer)
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise InputError("VERSION_UNSUPPORTED", f"Unsupported version at {pointer}", pointer)
    if record["kind"] != kind:
        raise InputError("KIND_MISMATCH", f"Expected {kind} at {pointer}", pointer)
    return record


def sha(value: Any, pointer: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or set(value) - SHA_CHARS:
        raise InputError("HASH_FORMAT", f"Invalid SHA-256 at {pointer}", pointer)
    return value


def stable_id(value: Any, pointer: str) -> str:
    if not isinstance(value, str) or STABLE_ID.fullmatch(value) is None:
        raise InputError("ID_FORMAT", f"Expected stable ID at {pointer}", pointer)
    return value


def nonempty(value: Any, pointer: str, *, max_length: int = 4096) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise InputError("FIELD_TYPE", f"Expected bounded non-empty string at {pointer}", pointer)
    return value


def bounded_limits(value: Any, ceilings: dict[str, int], pointer: str) -> dict[str, int]:
    limits = exact(value, set(ceilings), pointer)
    for name, ceiling in ceilings.items():
        selected = limits[name]
        if type(selected) is not int or selected < 0 or selected > ceiling:
            raise InputError("LIMIT_EXCEEDED", f"Invalid {name} limit at {pointer}", pointer)
    return limits


def bounded_list(value: Any, limit: int, pointer: str) -> list[Any]:
    if not isinstance(value, list) or len(value) > limit:
        raise InputError("LIMIT_EXCEEDED", f"Array limit exceeded at {pointer}", pointer)
    return value


def unique_strings(value: Any, limit: int, pointer: str) -> list[str]:
    values = bounded_list(value, limit, pointer)
    if any(not isinstance(item, str) or STABLE_ID.fullmatch(item) is None for item in values):
        raise InputError("ID_FORMAT", f"Expected stable IDs at {pointer}", pointer)
    if len(values) != len(set(values)):
        raise InputError("DUPLICATE_ID", f"Expected unique IDs at {pointer}", pointer)
    return sorted(values)


def domain(value: Any, pointer: str) -> str:
    if not isinstance(value, str) or value not in DOMAINS:
        raise InputError("DOMAIN_MISMATCH", f"Unsupported assurance domain at {pointer}", pointer)
    return value


def instant(value: Any, pointer: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise InputError("TIME_FORMAT", f"Expected UTC timestamp at {pointer}", pointer)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise InputError("TIME_FORMAT", f"Invalid timestamp at {pointer}", pointer) from exc
    if parsed.tzinfo != UTC:
        raise InputError("TIME_FORMAT", f"Expected UTC timestamp at {pointer}", pointer)
    return parsed


def digest(value: Any, *, exclude: str = "digest") -> str:
    if isinstance(value, dict):
        body = {key: item for key, item in value.items() if key != exclude}
    else:
        body = value
    return hashlib.sha256(canonical(body)).hexdigest()


def seal(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["digest"] = digest(result)
    return result


def verify_digest(value: Any, pointer: str, *, field: str = "digest") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError("FIELD_TYPE", f"Expected object at {pointer}", pointer)
    expected = sha(value.get(field), pointer + "/" + field)
    if digest(value, exclude=field) != expected:
        raise InputError("SEMANTIC_DIGEST", f"Digest mismatch at {pointer}", pointer)
    return value


def scope(value: Any, pointer: str) -> dict[str, str]:
    record = exact(value, {"kind", "id", "purpose"}, pointer)
    for key in ("kind", "id"):
        stable_id(record[key], pointer + "/" + key)
    nonempty(record["purpose"], pointer + "/purpose", max_length=256)
    return record


def reason(code: str, subject_ref: str, action: str) -> dict[str, str]:
    return {"code": code, "subject_ref": subject_ref, "required_action": action}
