"""Exact version-1 runtime envelopes and guarded local publication."""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import (
    bounded_limits,
    bounded_list,
    exact,
    instant,
    nonempty,
    sha,
    stable_id,
    unique_strings,
    verify_digest,
    version,
)
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError

MAX_CONTROL_BYTES = 64 * 1024 * 1024
MAX_EVENT_COUNT = 100_000
MAX_BLOBS = 10_000
MAX_BLOB_BYTES = 64 * 1024 * 1024
MAX_EXPORTED_BYTES = 128 * 1024 * 1024

REF_FIELDS = {"path", "sha256", "semantic_digest"}
BASELINE_FIELDS = {
    "source_digest",
    "process_digest",
    "policy_digest",
    "tool_digest",
    "subject_digest",
    "evidence_digests",
}
INTENT_FIELDS = {
    "intent_id",
    "package_ref",
    "runtime_profile_ref",
    "baseline",
    "start_args",
    "limits",
    "digest",
}
BINDING_FIELDS = {
    "intent_id",
    "intent_digest",
    "source_package_digest",
    "wire_digest",
    "runtime_commit",
    "version_id",
    "run_id",
    "creation_state",
    "start_state",
    "baseline_digest",
    "native_observation",
    "resume_attempts",
    "reason_codes",
    "digest",
}
EXPORT_FIELDS = {
    "source_package",
    "wire_projection",
    "runtime",
    "binding",
    "run_summary",
    "status",
    "events",
    "checkpoints",
    "stages",
    "questions",
    "blobs",
    "assurance_references",
    "completeness",
    "limitations",
    "digest",
}
BLOB_ORIGINS = {"fabric_source", "runtime_observation", "authenticated_005_reference"}
REFERENCE_ORIGINS = {"runtime_observation", "authenticated_005_reference"}
CREATION_STATES = {
    "prepared",
    "create_in_flight",
    "run_known",
    "reconciliation_required",
}
START_STATES = {
    "not_requested",
    "start_in_flight",
    "started",
    "reconciliation_required",
}


def bounded_diagnostic(error: InputError) -> dict[str, str]:
    """Return a stable-sized public diagnostic without echoing raw record content."""
    code = str(error.code)[:128]
    raw_pointer = str(error.pointer)
    pointer = next(
        (
            f"/{name}"
            for name in ("runtime_intent", "runtime_binding", "runtime_export")
            if raw_pointer.startswith(f"/{name}")
        ),
        "",
    )
    return {
        "code": code,
        "pointer": pointer,
        "message": f"Runtime input rejected ({code}).",
    }


def _record(
    value: Any, kind: str, fields: set[str], pointer: str, *, maximum: int = MAX_CONTROL_BYTES
) -> dict[str, Any]:
    record = version(value, kind, fields, pointer)
    if len(canonical(record)) > maximum:
        raise InputError("LIMIT_EXCEEDED", f"Record exceeds byte limit at {pointer}", pointer)
    verify_digest(record, pointer)
    return record


def _reference(value: Any, pointer: str) -> dict[str, Any]:
    record = exact(value, REF_FIELDS, pointer)
    nonempty(record["path"], pointer + "/path")
    for name in ("sha256", "semantic_digest"):
        sha(record[name], pointer + "/" + name)
    return record


def validate_baseline(value: Any, pointer: str = "/baseline") -> dict[str, Any]:
    record = exact(value, BASELINE_FIELDS, pointer)
    for name in BASELINE_FIELDS - {"evidence_digests"}:
        sha(record[name], pointer + "/" + name)
    evidence = bounded_list(record["evidence_digests"], 10_000, pointer + "/evidence_digests")
    for index, item in enumerate(evidence):
        sha(item, f"{pointer}/evidence_digests/{index}")
    if evidence != sorted(set(evidence)):
        raise InputError("DUPLICATE_ID", "Evidence digests must be unique and sorted", pointer)
    return record


def validate_intent(value: Any) -> dict[str, Any]:
    record = _record(value, "runtime_intent", INTENT_FIELDS, "/runtime_intent")
    stable_id(record["intent_id"], "/runtime_intent/intent_id")
    _reference(record["package_ref"], "/runtime_intent/package_ref")
    _reference(record["runtime_profile_ref"], "/runtime_intent/runtime_profile_ref")
    validate_baseline(record["baseline"], "/runtime_intent/baseline")
    args = exact(record["start_args"], {"target_id", "labels"}, "/runtime_intent/start_args")
    stable_id(args["target_id"], "/runtime_intent/start_args/target_id")
    labels = args["labels"]
    if not isinstance(labels, dict) or len(labels) > 32:
        raise InputError(
            "LIMIT_EXCEEDED", "Too many runtime labels", "/runtime_intent/start_args/labels"
        )
    for key, item in labels.items():
        nonempty(key, "/runtime_intent/start_args/labels/key", max_length=64)
        nonempty(item, f"/runtime_intent/start_args/labels/{key}", max_length=256)
    limits = bounded_limits(
        record["limits"],
        {
            "timeout_seconds": 3600,
            "event_pages": 10_000,
            "output_bytes": MAX_BLOB_BYTES,
            "attempts": 100,
        },
        "/runtime_intent/limits",
    )
    if any(value == 0 for value in limits.values()):
        raise InputError(
            "LIMIT_EXCEEDED", "Runtime limits must be positive", "/runtime_intent/limits"
        )
    return record


def validate_binding(value: Any) -> dict[str, Any]:
    record = _record(value, "runtime_binding", BINDING_FIELDS, "/runtime_binding")
    stable_id(record["intent_id"], "/runtime_binding/intent_id")
    for name in ("intent_digest", "source_package_digest", "wire_digest", "baseline_digest"):
        sha(record[name], f"/runtime_binding/{name}")
    commit = record["runtime_commit"]
    if not isinstance(commit, str) or len(commit) != 40 or set(commit) - set("0123456789abcdef"):
        raise InputError(
            "HASH_FORMAT", "Expected full runtime commit", "/runtime_binding/runtime_commit"
        )
    for name in ("version_id", "run_id"):
        if record[name] is not None:
            nonempty(record[name], f"/runtime_binding/{name}", max_length=256)
    creation = record["creation_state"]
    start = record["start_state"]
    if creation not in CREATION_STATES or start not in START_STATES:
        raise InputError("FIELD_UNKNOWN", "Unknown runtime intent state", "/runtime_binding")
    if (creation == "run_known") != (record["run_id"] is not None):
        raise InputError(
            "FIELD_TYPE", "Run ID and creation state disagree", "/runtime_binding/run_id"
        )
    if start in {"start_in_flight", "started"} and record["run_id"] is None:
        raise InputError(
            "FIELD_TYPE", "Start state requires a known run ID", "/runtime_binding/start_state"
        )
    observed = record["native_observation"]
    if observed is not None:
        observation = exact(
            observed, {"observed_at", "response_digest"}, "/runtime_binding/native_observation"
        )
        instant(observation["observed_at"], "/runtime_binding/native_observation/observed_at")
        sha(observation["response_digest"], "/runtime_binding/native_observation/response_digest")
    attempts = record["resume_attempts"]
    if type(attempts) is not int or attempts < 0 or attempts > 100:
        raise InputError(
            "LIMIT_EXCEEDED", "Resume attempts are invalid", "/runtime_binding/resume_attempts"
        )
    reasons = unique_strings(record["reason_codes"], 1000, "/runtime_binding/reason_codes")
    if reasons != record["reason_codes"]:
        raise InputError(
            "FIELD_TYPE", "Runtime reasons must be sorted", "/runtime_binding/reason_codes"
        )
    return record


def validate_export(value: Any) -> dict[str, Any]:
    record = _record(
        value, "runtime_export", EXPORT_FIELDS, "/runtime_export", maximum=MAX_EXPORTED_BYTES
    )
    for name in (
        "source_package",
        "wire_projection",
        "runtime",
        "binding",
        "run_summary",
        "status",
    ):
        if not isinstance(record[name], dict):
            raise InputError("FIELD_TYPE", f"Expected object at /runtime_export/{name}")
    validate_binding(record["binding"])
    for name, maximum in (
        ("events", MAX_EVENT_COUNT),
        ("checkpoints", 10_000),
        ("stages", 10_000),
        ("questions", 10_000),
    ):
        items = bounded_list(record[name], maximum, f"/runtime_export/{name}")
        if any(not isinstance(item, dict) for item in items):
            raise InputError("FIELD_TYPE", f"Expected records at /runtime_export/{name}")
    blobs = bounded_list(record["blobs"], MAX_BLOBS, "/runtime_export/blobs")
    seen: set[str] = set()
    for index, raw in enumerate(blobs):
        pointer = f"/runtime_export/blobs/{index}"
        blob = exact(raw, {"id", "sha256", "bytes", "base64", "origin"}, pointer)
        identifier = stable_id(blob["id"], pointer + "/id")
        if identifier in seen:
            raise InputError("DUPLICATE_ID", "Duplicate runtime blob ID", pointer)
        seen.add(identifier)
        expected = sha(blob["sha256"], pointer + "/sha256")
        length = blob["bytes"]
        if type(length) is not int or length < 0 or length > MAX_BLOB_BYTES:
            raise InputError("LIMIT_EXCEEDED", "Runtime blob length exceeds limit", pointer)
        encoded = blob["base64"]
        if not isinstance(encoded, str) or len(encoded) > (MAX_BLOB_BYTES * 4 // 3 + 4):
            raise InputError("LIMIT_EXCEEDED", "Runtime blob encoding exceeds limit", pointer)
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise InputError("FIELD_TYPE", "Invalid runtime blob base64", pointer) from exc
        if len(decoded) != length or hashlib.sha256(decoded).hexdigest() != expected:
            raise InputError("HASH_MISMATCH", "Runtime blob identity mismatch", pointer)
        if blob["origin"] not in BLOB_ORIGINS:
            raise InputError("FIELD_UNKNOWN", "Unknown runtime blob origin", pointer)
    references = bounded_list(
        record["assurance_references"], 10_000, "/runtime_export/assurance_references"
    )
    for index, raw in enumerate(references):
        pointer = f"/runtime_export/assurance_references/{index}"
        reference = exact(
            raw, {"assessment_digest", "assurance_domain", "outcome", "origin"}, pointer
        )
        sha(reference["assessment_digest"], pointer + "/assessment_digest")
        if reference["assurance_domain"] not in {"fixture_contract", "production", None}:
            raise InputError("DOMAIN_MISMATCH", "Unknown assurance domain", pointer)
        if reference["outcome"] is not None:
            nonempty(reference["outcome"], pointer + "/outcome", max_length=64)
        if reference["origin"] not in REFERENCE_ORIGINS:
            raise InputError("FIELD_UNKNOWN", "Unknown assurance reference origin", pointer)
    if record["completeness"] not in {"complete", "incomplete", "unknown"}:
        raise InputError("FIELD_UNKNOWN", "Unknown export completeness")
    limitations = bounded_list(record["limitations"], 1000, "/runtime_export/limitations")
    for index, item in enumerate(limitations):
        nonempty(item, f"/runtime_export/limitations/{index}", max_length=512)
    if len(canonical(record)) > MAX_EXPORTED_BYTES:
        raise InputError("LIMIT_EXCEEDED", "Runtime export exceeds 128 MiB")
    return record


def output_path(out: Path, inputs: list[Path], protected_roots: list[Path]) -> Path:
    """Reject output aliases and writes into selected input/protected roots."""
    selected = out.absolute()
    if selected.exists() and (selected.is_symlink() or selected.stat().st_nlink != 1):
        raise InputError("OUTPUT_ALIAS", "Runtime output cannot be a link")
    for ancestor in (selected, *selected.parents):
        if ancestor.is_symlink():
            raise InputError("OUTPUT_ALIAS", "Runtime output parent cannot be a symlink")
    target = selected.resolve()
    for raw in inputs:
        source = raw.resolve()
        if target == source or (target.exists() and source.exists() and target.samefile(source)):
            raise InputError("OUTPUT_ALIAS", "Runtime output aliases an input")
    for raw in protected_roots:
        if target.is_relative_to(raw.resolve()):
            raise InputError("OUTPUT_PROTECTED", "Runtime output is inside a protected root")
    return target


def publish(
    out: Path, record: dict[str, Any], *, inputs: list[Path], protected_roots: list[Path]
) -> None:
    """Atomically publish a record outside all selected input and protected paths."""
    payload = canonical(record)
    if len(payload) > MAX_EXPORTED_BYTES:
        raise InputError("LIMIT_EXCEEDED", "Runtime output exceeds 128 MiB")
    out = output_path(out, inputs, protected_roots)
    temporary: str | None = None
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".runtime-", dir=out.parent)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, out)
        temporary = None
    except OSError as exc:
        raise InputError("OUTPUT_IO", str(exc)) from exc
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)
