"""Classify immutable observations separately from their engineering result."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import (
    MAX_EVIDENCE,
    MAX_REFERENCES,
    ORIGINS,
    bounded_limits,
    bounded_list,
    digest,
    domain,
    exact,
    instant,
    nonempty,
    scope,
    sha,
    unique_strings,
    verify_digest,
    version,
)
from score_sw_fabric.assurance.origins import validate_profile, verify_receipt
from score_sw_fabric.assurance.reader import resolve_file
from score_sw_fabric.process_source.reader import InputError

EVIDENCE_FIELDS = {
    "evidence_id",
    "origin_class",
    "assurance_domain",
    "subject_digest",
    "scope",
    "obligation_ids",
    "inputs",
    "process_baseline",
    "tool",
    "execution_policy_digest",
    "profile_digests",
    "collector_id",
    "started_at",
    "finished_at",
    "termination",
    "raw_outputs",
    "measurements",
    "result",
    "limits",
    "exclusions",
    "receipt_ref",
    "import_chain",
    "limitations",
    "digest",
}
TERMINATIONS = {"completed", "failed", "timeout", "crash", "infrastructure_error"}
RESULTS = {"pass", "fail", "unknown"}
RAW_FIELDS = {"path", "sha256", "bytes"}


def _raw_reasons(record: dict[str, Any], root: Path) -> list[str]:
    refs = bounded_list(record["raw_outputs"], MAX_REFERENCES, "/evidence/raw_outputs")
    if not refs:
        return ["RAW_OUTPUT_MISSING"]
    reasons: list[str] = []
    seen: set[str] = set()
    for index, ref in enumerate(refs):
        item = exact(ref, RAW_FIELDS, f"/evidence/raw_outputs/{index}")
        name = nonempty(item["path"], f"/evidence/raw_outputs/{index}/path")
        if name in seen:
            raise InputError("DUPLICATE_ID", f"Duplicate raw output path {name}")
        seen.add(name)
        expected = sha(item["sha256"], f"/evidence/raw_outputs/{index}/sha256")
        if type(item["bytes"]) is not int or item["bytes"] < 0:
            raise InputError("FIELD_TYPE", "Raw output byte count must be nonnegative integer")
        try:
            source = resolve_file(root, name, f"/evidence/raw_outputs/{index}/path")
            if source.stat().st_size != item["bytes"]:
                reasons.append("RAW_OUTPUT_MISMATCH")
                continue
            with source.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != expected:
                reasons.append("RAW_OUTPUT_MISMATCH")
        except InputError as exc:
            if exc.code == "INPUT_UNAVAILABLE":
                reasons.append("RAW_OUTPUT_MISSING")
            else:
                raise
        except OSError:
            reasons.append("RAW_OUTPUT_MISSING")
    return reasons


def _import_reasons(
    record: dict[str, Any],
    profile: dict[str, Any],
    *,
    requested_domain: str,
    requested_scope: dict[str, str],
    as_of: datetime,
) -> list[str]:
    rules = [
        rule
        for rule in profile["import_rules"]
        if rule.get("evidence_id") == record["evidence_id"]
        and requested_scope["id"] in rule.get("scope_ids", [])
    ]
    if len(rules) != 1 or len(record["import_chain"]) != 1:
        return ["IMPORT_RULE_MISSING"]
    rule = exact(
        rules[0],
        {
            "evidence_id",
            "scope_ids",
            "original_issuer_id",
            "original_policy_digest",
            "transformation_id",
            "max_age_seconds",
        },
        "/trust_profile/import_rules",
    )
    link = exact(
        record["import_chain"][0],
        {
            "original_record",
            "original_receipt",
            "original_receipt_digest",
            "original_issuer_id",
            "original_subject_digest",
            "original_result",
            "transformation",
        },
        "/evidence/import_chain/0",
    )
    original = version(
        link["original_record"],
        "assurance_evidence",
        EVIDENCE_FIELDS,
        "/evidence/import_chain/0/original_record",
    )
    verify_digest(original, "/evidence/import_chain/0/original_record")
    original_receipt = link["original_receipt"]
    if not isinstance(original_receipt, dict):
        raise InputError("FIELD_TYPE", "Original import receipt must be a record")
    transform = exact(
        link["transformation"],
        {"id", "input_digest", "output_basis_digest", "digest"},
        "/evidence/import_chain/0/transformation",
    )
    verify_digest(transform, "/evidence/import_chain/0/transformation")
    reasons: list[str] = []
    if original["origin_class"] != "protected_observed" or original["import_chain"]:
        reasons.append("IMPORT_CHAIN_UNVERIFIED")
    if (
        link["original_receipt_digest"] != original_receipt.get("receipt_digest")
        or link["original_issuer_id"] != original_receipt.get("issuer_id")
        or link["original_issuer_id"] != rule["original_issuer_id"]
        or link["original_subject_digest"] != original["subject_digest"]
        or link["original_result"] != original["result"]
        or original["execution_policy_digest"] != rule["original_policy_digest"]
    ):
        reasons.append("IMPORT_CHAIN_UNVERIFIED")
    for field in (
        "subject_digest",
        "scope",
        "obligation_ids",
        "inputs",
        "process_baseline",
        "tool",
        "profile_digests",
        "started_at",
        "finished_at",
        "termination",
        "raw_outputs",
        "measurements",
        "result",
        "limits",
        "exclusions",
    ):
        if original[field] != record[field]:
            reasons.append("IMPORT_CHAIN_UNVERIFIED")
            break
    basis = {key: value for key, value in record.items() if key not in {"import_chain", "digest"}}
    if (
        transform["id"] != rule["transformation_id"]
        or transform["input_digest"] != original["digest"]
        or transform["output_basis_digest"] != digest(basis, exclude="__none__")
    ):
        reasons.append("IMPORT_CHAIN_UNVERIFIED")
    if type(rule["max_age_seconds"]) is not int or rule["max_age_seconds"] < 0:
        raise InputError("FIELD_TYPE", "Invalid import age rule")
    if (
        as_of - instant(original["finished_at"], "/import/original_finished_at")
    ).total_seconds() > rule["max_age_seconds"]:
        reasons.append("RESULT_STALE")
    origin_reasons = verify_receipt(
        original,
        original_receipt,
        profile,
        payload_kind="assurance_evidence",
        requested_domain=requested_domain,
        requested_scope=requested_scope,
        as_of=as_of,
    )
    if origin_reasons:
        reasons.extend(origin_reasons)
        reasons.append("IMPORT_CHAIN_UNVERIFIED")
    return sorted(set(reasons))


def classify_evidence(
    value: Any,
    receipt: Any,
    subject: dict[str, Any],
    policy: dict[str, Any],
    profile: dict[str, Any],
    *,
    requested_domain: str,
    requested_scope: dict[str, str],
    as_of: datetime,
    raw_root: Path,
    seen_sequences: set[tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    record = version(value, "assurance_evidence", EVIDENCE_FIELDS, "/evidence")
    verify_digest(record, "/evidence")
    verify_digest(subject, "/subject")
    verify_digest(policy, "/policy")
    validate_profile(profile)
    selected_domain = domain(requested_domain, "/assurance_domain")
    scope(requested_scope, "/scope")
    nonempty(record["evidence_id"], "/evidence/evidence_id", max_length=256)
    if record["origin_class"] not in ORIGINS:
        raise InputError("FIELD_UNKNOWN", "Unknown evidence origin class")
    if record["termination"] not in TERMINATIONS or record["result"] not in RESULTS:
        raise InputError("FIELD_UNKNOWN", "Unknown termination or result")
    sha(record["subject_digest"], "/evidence/subject_digest")
    sha(record["execution_policy_digest"], "/evidence/execution_policy_digest")
    if record["receipt_ref"] is not None:
        sha(record["receipt_ref"], "/evidence/receipt_ref")
    obligation_ids = unique_strings(
        record["obligation_ids"], MAX_EVIDENCE, "/evidence/obligation_ids"
    )
    bounded_list(record["inputs"], MAX_REFERENCES, "/evidence/inputs")
    bounded_list(record["import_chain"], MAX_REFERENCES, "/evidence/import_chain")
    bounded_list(record["exclusions"], MAX_REFERENCES, "/evidence/exclusions")
    bounded_list(record["limitations"], MAX_REFERENCES, "/evidence/limitations")
    limits = bounded_limits(record["limits"], {"duration_seconds": 2**31 - 1}, "/evidence/limits")
    started = instant(record["started_at"], "/evidence/started_at")
    finished = instant(record["finished_at"], "/evidence/finished_at")
    reasons: list[str] = []
    if (finished - started).total_seconds() > limits["duration_seconds"]:
        reasons.append("LIMIT_EXCEEDED")
    if not started <= finished <= as_of:
        reasons.append("TIME_BASIS_UNTRUSTED")
    if (
        record["assurance_domain"] != selected_domain
        or subject["assurance_domain"] != selected_domain
    ):
        reasons.append("DOMAIN_MISMATCH")
    if record["subject_digest"] != subject["digest"]:
        reasons.append("SUBJECT_MISMATCH")
    if record["scope"] != requested_scope or subject["scope"] != requested_scope:
        reasons.append("SCOPE_MISMATCH")
    if not obligation_ids or not set(obligation_ids).issubset(subject["expected_obligation_ids"]):
        reasons.append("OBLIGATION_SET_INCOMPLETE")
    expected_inputs = {
        "plan": subject["plan"]["digest"],
        "candidate": subject["artifact_candidate"]["digest"],
    }
    if {item.get("id"): item.get("digest") for item in record["inputs"]} != expected_inputs:
        reasons.append("SUBJECT_MISMATCH")
    if record["process_baseline"] != subject["process_baseline"]:
        reasons.append("PROCESS_MISMATCH")
    if record["profile_digests"] != subject["profiles"]:
        reasons.append("PROFILE_MISMATCH")
    if record["execution_policy_digest"] != policy["digest"]:
        reasons.append("POLICY_MISMATCH")
    allowed = [
        item
        for item in policy["allowed_evidence"]
        if item.get("evidence_id") == record["evidence_id"]
    ]
    if len(allowed) != 1:
        reasons.append("EVIDENCE_UNTRUSTED")
    else:
        if record["tool"] != allowed[0]["tool"]:
            reasons.append("TOOL_MISMATCH")
        if record["collector_id"] != allowed[0]["collector_id"]:
            reasons.append("COLLECTOR_UNTRUSTED")
        if (as_of - finished).total_seconds() > allowed[0]["max_age_seconds"]:
            reasons.append("RESULT_STALE")
    if record["termination"] != "completed":
        reasons.append("RESULT_TIMEOUT" if record["termination"] == "timeout" else "RESULT_UNKNOWN")
    if not isinstance(record["measurements"], dict) or set(record["measurements"]) != set(
        obligation_ids
    ):
        reasons.append("RESULT_UNKNOWN")
    if record["result"] == "unknown":
        reasons.append("RESULT_UNKNOWN")
    if isinstance(record["measurements"], dict) and set(record["measurements"]) == set(
        obligation_ids
    ):
        measurements = list(record["measurements"].values())
        if any(type(value) is not bool for value in measurements):
            reasons.append("RESULT_UNKNOWN")
        elif record["result"] == "pass" and not all(measurements):
            reasons.append("RESULT_CONFLICT")
        elif record["result"] == "fail" and all(measurements):
            reasons.append("RESULT_CONFLICT")
    reasons.extend(_raw_reasons(record, raw_root))
    if record["origin_class"] in {"fixture_replay", "agent_assertion"}:
        reasons.append("EVIDENCE_UNTRUSTED")
    if record["origin_class"] == "imported_verified":
        reasons.extend(
            _import_reasons(
                record,
                profile,
                requested_domain=selected_domain,
                requested_scope=requested_scope,
                as_of=as_of,
            )
        )
    if not isinstance(receipt, dict):
        reasons.append("ORIGIN_UNVERIFIED")
    else:
        reasons.extend(
            verify_receipt(
                record,
                receipt,
                profile,
                payload_kind="assurance_evidence",
                requested_domain=selected_domain,
                requested_scope=requested_scope,
                as_of=as_of,
                seen_sequences=seen_sequences,
            )
        )
    return {
        "evidence_id": record["evidence_id"],
        "evidence_digest": record["digest"],
        "assurance_domain": selected_domain,
        "origin_class": record["origin_class"],
        "obligation_ids": obligation_ids,
        "eligible": not reasons,
        "result": record["result"] if record["termination"] == "completed" else "unknown",
        "reason_codes": sorted(set(reasons)),
        "limitations": record["limitations"],
    }
