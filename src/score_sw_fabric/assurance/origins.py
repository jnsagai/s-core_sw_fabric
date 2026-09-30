"""Verify externally issued receipts without exposing a signing capability."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Any

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from score_sw_fabric.assurance.models import (
    MAX_CONTROL_BYTES,
    MAX_DECISIONS,
    MAX_DEPTH,
    MAX_EVIDENCE,
    MAX_FINDINGS,
    MAX_PACKAGE_BYTES,
    MAX_PREDICATES,
    MAX_REFERENCES,
    bounded_limits,
    bounded_list,
    digest,
    domain,
    exact,
    instant,
    nonempty,
    scope,
    sha,
    verify_digest,
    version,
)
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError

RECEIPT_FIELDS = {
    "assurance_domain",
    "payload_kind",
    "payload_digest",
    "issuer_id",
    "key_id",
    "algorithm",
    "issued_at",
    "nonce_or_sequence",
    "signature",
    "receipt_digest",
}
PROFILE_FIELDS = {
    "id",
    "assurance_domain",
    "authority_source",
    "issuer_keys",
    "identity_providers",
    "role_assignments",
    "independence_rules",
    "import_rules",
    "revocations",
    "time_authorities",
    "limits",
    "status",
    "digest",
}
RECEIPT_KINDS = {
    "assurance_evidence",
    "assurance_decision",
    "assurance_trust_profile",
    "assurance_time",
}
PREFIX = b"SCORE-SW-FABRIC-ASSURANCE-RECEIPT-V1\x00"


def signing_bytes(receipt: dict[str, Any]) -> bytes:
    body = {
        key: value for key, value in receipt.items() if key not in {"signature", "receipt_digest"}
    }
    return PREFIX + canonical(body)


def _decode(value: Any, pointer: str, length: int) -> bytes:
    if not isinstance(value, str):
        raise InputError("SIGNATURE_FORMAT", f"Expected base64 at {pointer}", pointer)
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise InputError("SIGNATURE_FORMAT", f"Invalid base64 at {pointer}", pointer) from exc
    if len(decoded) != length:
        raise InputError("SIGNATURE_FORMAT", f"Expected {length} bytes at {pointer}", pointer)
    return decoded


def _bounded_strings(value: Any, pointer: str, *, required: bool = True) -> list[str]:
    items = bounded_list(value, MAX_REFERENCES, pointer)
    if required and not items:
        raise InputError("FIELD_TYPE", f"Expected non-empty list at {pointer}", pointer)
    for index, item in enumerate(items):
        nonempty(item, f"{pointer}/{index}", max_length=256)
    if len(items) != len(set(items)):
        raise InputError("DUPLICATE_ID", f"Duplicate list entry at {pointer}", pointer)
    return items


def validate_profile(value: Any) -> dict[str, Any]:
    profile = version(value, "assurance_trust_profile", PROFILE_FIELDS, "/trust_profile")
    verify_digest(profile, "/trust_profile")
    selected_domain = domain(profile["assurance_domain"], "/trust_profile/assurance_domain")
    if profile["status"] not in {"fixture_only", "pending_production_review", "reviewed"}:
        raise InputError("FIELD_UNKNOWN", "Unknown trust profile status")
    if selected_domain == "fixture_contract" and profile["status"] != "fixture_only":
        raise InputError("DOMAIN_MISMATCH", "Fixture profile must be fixture_only")
    bounded_list(profile["issuer_keys"], MAX_REFERENCES, "/trust_profile/issuer_keys")
    bounded_list(profile["role_assignments"], MAX_DECISIONS, "/trust_profile/role_assignments")
    for field in (
        "identity_providers",
        "independence_rules",
        "import_rules",
        "revocations",
        "time_authorities",
    ):
        bounded_list(profile[field], MAX_REFERENCES, f"/trust_profile/{field}")
    bounded_limits(
        profile["limits"],
        {
            "control_bytes": MAX_CONTROL_BYTES,
            "package_bytes": MAX_PACKAGE_BYTES,
            "predicates": MAX_PREDICATES,
            "evidence": MAX_EVIDENCE,
            "decisions": MAX_DECISIONS,
            "references": MAX_REFERENCES,
            "findings": MAX_FINDINGS,
            "depth": MAX_DEPTH,
        },
        "/trust_profile/limits",
    )
    authority = exact(
        profile["authority_source"],
        {"kind", "rationale", "source_ref"},
        "/trust_profile/authority_source",
    )
    for name in ("kind", "rationale", "source_ref"):
        nonempty(authority[name], f"/trust_profile/authority_source/{name}", max_length=256)
    if selected_domain == "fixture_contract" and authority["kind"] != "fixture_contract":
        raise InputError("TAILORING_UNVERIFIED", "Fixture trust profile lacks fixture authority")
    seen: set[str] = set()
    for index, key in enumerate(profile["issuer_keys"]):
        pointer = f"/trust_profile/issuer_keys/{index}"
        fields = {
            "key_id",
            "issuer_id",
            "public_key_base64",
            "receipt_kinds",
            "scope_ids",
            "valid_from",
            "valid_until",
        }
        item = exact(key, fields, pointer)
        identifier = nonempty(item["key_id"], pointer + "/key_id", max_length=256)
        if identifier in seen:
            raise InputError("DUPLICATE_ID", f"Duplicate key ID {identifier}")
        seen.add(identifier)
        _decode(item["public_key_base64"], pointer + "/public_key_base64", 32)
        instant(item["valid_from"], pointer + "/valid_from")
        instant(item["valid_until"], pointer + "/valid_until")
        receipt_kinds = bounded_list(item["receipt_kinds"], 4, pointer + "/receipt_kinds")
        if (
            not receipt_kinds
            or any(not isinstance(kind, str) for kind in receipt_kinds)
            or not set(receipt_kinds).issubset(RECEIPT_KINDS)
        ):
            raise InputError("FIELD_UNKNOWN", "Invalid receipt kind permission")
        if len(receipt_kinds) != len(set(receipt_kinds)):
            raise InputError("DUPLICATE_ID", "Duplicate receipt kind permission")
        _bounded_strings(item["scope_ids"], pointer + "/scope_ids")
        if instant(item["valid_from"], pointer + "/valid_from") > instant(
            item["valid_until"], pointer + "/valid_until"
        ):
            raise InputError("TIME_FORMAT", "Issuer key validity is reversed", pointer)
    provider_ids: set[str] = set()
    for index, raw in enumerate(profile["identity_providers"]):
        pointer = f"/trust_profile/identity_providers/{index}"
        item = exact(raw, {"assurance", "authentication_method", "id", "issuer_id"}, pointer)
        identifier = nonempty(item["id"], pointer + "/id", max_length=256)
        if identifier in provider_ids:
            raise InputError("DUPLICATE_ID", f"Duplicate identity provider {identifier}")
        provider_ids.add(identifier)
        for name in ("authentication_method", "issuer_id"):
            nonempty(item[name], pointer + "/" + name, max_length=256)
        if not isinstance(item["assurance"], str) or item["assurance"] not in {
            "fixture_only",
            "protected",
        }:
            raise InputError("FIELD_UNKNOWN", "Unknown identity provider assurance")
    for index, raw in enumerate(profile["role_assignments"]):
        pointer = f"/trust_profile/role_assignments/{index}"
        item = exact(
            raw,
            {"actor_id", "authority_ref", "role", "scope_ids", "valid_from", "valid_until"},
            pointer,
        )
        for name in ("actor_id", "authority_ref", "role"):
            nonempty(item[name], pointer + "/" + name, max_length=256)
        _bounded_strings(item["scope_ids"], pointer + "/scope_ids")
        if instant(item["valid_from"], pointer + "/valid_from") > instant(
            item["valid_until"], pointer + "/valid_until"
        ):
            raise InputError("TIME_FORMAT", "Role assignment validity is reversed", pointer)
    rule_ids: set[str] = set()
    for index, raw in enumerate(profile["independence_rules"]):
        pointer = f"/trust_profile/independence_rules/{index}"
        item = exact(raw, {"disallowed_actor_ids", "id", "required"}, pointer)
        identifier = nonempty(item["id"], pointer + "/id", max_length=256)
        if identifier in rule_ids:
            raise InputError("DUPLICATE_ID", f"Duplicate independence rule {identifier}")
        rule_ids.add(identifier)
        _bounded_strings(
            item["disallowed_actor_ids"], pointer + "/disallowed_actor_ids", required=False
        )
        if type(item["required"]) is not bool:
            raise InputError("FIELD_TYPE", "Independence required flag must be boolean", pointer)
    for index, raw in enumerate(profile["import_rules"]):
        pointer = f"/trust_profile/import_rules/{index}"
        item = exact(
            raw,
            {
                "evidence_id",
                "scope_ids",
                "original_issuer_id",
                "original_policy_digest",
                "transformation_id",
                "max_age_seconds",
            },
            pointer,
        )
        for name in ("evidence_id", "original_issuer_id", "transformation_id"):
            nonempty(item[name], pointer + "/" + name, max_length=256)
        _bounded_strings(item["scope_ids"], pointer + "/scope_ids")
        sha(item["original_policy_digest"], pointer + "/original_policy_digest")
        age = item["max_age_seconds"]
        if type(age) is not int or age < 0 or age > 2**31 - 1:
            raise InputError("LIMIT_EXCEEDED", "Invalid import age limit", pointer)
    for index, raw in enumerate(profile["revocations"]):
        pointer = f"/trust_profile/revocations/{index}"
        item = exact(raw, {"key_id", "effective_at"}, pointer)
        nonempty(item["key_id"], pointer + "/key_id", max_length=256)
        instant(item["effective_at"], pointer + "/effective_at")
    for index, raw in enumerate(profile["time_authorities"]):
        pointer = f"/trust_profile/time_authorities/{index}"
        item = exact(raw, {"issuer_id", "key_id", "scope_ids"}, pointer)
        for name in ("issuer_id", "key_id"):
            nonempty(item[name], pointer + "/" + name, max_length=256)
        _bounded_strings(item["scope_ids"], pointer + "/scope_ids")
    return profile


def verify_receipt(
    payload: dict[str, Any],
    receipt: Any,
    profile: dict[str, Any],
    *,
    payload_kind: str,
    requested_domain: str,
    requested_scope: dict[str, str],
    as_of: datetime,
    seen_sequences: set[tuple[str, str, str]] | None = None,
) -> list[str]:
    """Return policy/crypto rejection codes; malformed envelopes raise InputError."""
    record = version(receipt, "signed_receipt", RECEIPT_FIELDS, "/receipt")
    verify_digest(record, "/receipt", field="receipt_digest")
    selected_domain = domain(requested_domain, "/assurance_domain")
    scope(requested_scope, "/scope")
    if record["payload_kind"] not in RECEIPT_KINDS or record["algorithm"] != "Ed25519":
        raise InputError("FIELD_UNKNOWN", "Unsupported receipt kind or algorithm")
    sha(record["payload_digest"], "/receipt/payload_digest")
    issued = instant(record["issued_at"], "/receipt/issued_at")
    nonempty(record["nonce_or_sequence"], "/receipt/nonce_or_sequence", max_length=256)
    signature = _decode(record["signature"], "/receipt/signature", 64)
    reasons: list[str] = []
    if record["payload_digest"] != digest(payload, exclude="__none__"):
        reasons.append("SUBJECT_MISMATCH")
    if record["payload_kind"] != payload_kind:
        reasons.append("KIND_MISMATCH")
    if (
        record["assurance_domain"] != selected_domain
        or profile["assurance_domain"] != selected_domain
    ):
        reasons.append("DOMAIN_MISMATCH")
    if selected_domain == "production":
        reasons.append("PRODUCTION_ORIGIN_UNAVAILABLE")
    if issued > as_of:
        reasons.append("TIME_BASIS_UNTRUSTED")
    keys = [item for item in profile["issuer_keys"] if item["key_id"] == record["key_id"]]
    if len(keys) != 1 or keys[0]["issuer_id"] != record["issuer_id"]:
        reasons.append("ISSUER_UNTRUSTED")
        return sorted(set(reasons))
    key = keys[0]
    if payload_kind not in key["receipt_kinds"] or requested_scope["id"] not in key["scope_ids"]:
        reasons.append("ISSUER_UNTRUSTED")
    valid_from = instant(key["valid_from"], "/key/valid_from")
    valid_until = instant(key["valid_until"], "/key/valid_until")
    if not valid_from <= issued <= valid_until or not valid_from <= as_of <= valid_until:
        reasons.append("ISSUER_UNTRUSTED")
    if any(
        item.get("key_id") == record["key_id"]
        and instant(item.get("effective_at"), "/revocation/effective_at") <= as_of
        for item in profile["revocations"]
    ):
        reasons.append("ISSUER_UNTRUSTED")
    public = _decode(key["public_key_base64"], "/key/public_key_base64", 32)
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(signature, signing_bytes(record))
    except (InvalidSignature, UnsupportedAlgorithm, ValueError):
        reasons.append("SIGNATURE_INVALID")
    if seen_sequences is not None and "SIGNATURE_INVALID" not in reasons:
        sequence = (record["issuer_id"], record["key_id"], record["nonce_or_sequence"])
        if sequence in seen_sequences:
            reasons.append("RECEIPT_REPLAY")
        else:
            seen_sequences.add(sequence)
    return sorted(set(reasons))


def replayed_payloads(receipts: list[dict[str, Any]]) -> set[str]:
    """Identify every payload sharing an issuer/key/sequence within one closed bundle."""
    sequences: dict[tuple[str, str, str], set[str]] = {}
    for index, record in enumerate(receipts):
        pointer = f"/receipts/{index}"
        issuer = nonempty(record.get("issuer_id"), pointer + "/issuer_id", max_length=256)
        key = nonempty(record.get("key_id"), pointer + "/key_id", max_length=256)
        sequence = nonempty(
            record.get("nonce_or_sequence"), pointer + "/nonce_or_sequence", max_length=256
        )
        payload = sha(record.get("payload_digest"), pointer + "/payload_digest")
        sequences.setdefault((issuer, key, sequence), set()).add(payload)
    return {payload for payloads in sequences.values() if len(payloads) > 1 for payload in payloads}
