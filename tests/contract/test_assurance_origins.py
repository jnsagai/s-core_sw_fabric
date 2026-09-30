"""The fixture key exercises verification only; it confers no production authority."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import digest, seal
from score_sw_fabric.assurance.origins import (
    PROFILE_FIELDS,
    RECEIPT_FIELDS,
    validate_profile,
    verify_receipt,
)
from score_sw_fabric.process_source.reader import InputError, read_yaml
from tests.assurance_support import fixture_receipt, read_json

ROOT = Path(__file__).resolve().parents[2]
SCOPE = {"kind": "component", "id": "component-005", "purpose": "fixture verification"}
NOW = datetime(2026, 9, 29, 10, tzinfo=UTC)


def _profile() -> dict[str, Any]:
    return validate_profile(read_yaml(ROOT / "profiles/assurance-fixture-v1.yaml"))


def _check(
    payload: dict[str, Any],
    receipt: dict[str, Any],
    profile: dict[str, Any] | None = None,
    domain: str = "fixture_contract",
) -> list[str]:
    return verify_receipt(
        payload,
        receipt,
        _profile() if profile is None else profile,
        payload_kind="assurance_evidence",
        requested_domain=domain,
        requested_scope=SCOPE,
        as_of=NOW,
    )


def test_published_vector_verifies_in_fixture_domain_only() -> None:
    vector = read_json(ROOT / "tests/fixtures/assurance/fixture-trust/vector.json")
    assert _check(vector["payload"], vector["receipt"]) == []
    assert "PRODUCTION_ORIGIN_UNAVAILABLE" in _check(
        vector["payload"], vector["receipt"], domain="production"
    )
    assert "DOMAIN_MISMATCH" in _check(vector["payload"], vector["receipt"], domain="production")


def test_equal_hash_without_valid_signature_cannot_authenticate() -> None:
    payload = {"kind": "assurance_evidence", "schema_version": 1, "result": "pass"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    wrong = deepcopy(receipt)
    wrong["signature"] = "A" * 86 + "=="
    wrong["receipt_digest"] = digest(wrong, exclude="receipt_digest")
    assert "SIGNATURE_INVALID" in _check(payload, wrong)
    assert "SUBJECT_MISMATCH" in _check({**payload, "result": "fail"}, receipt)


@pytest.mark.parametrize(
    "field,value",
    [("algorithm", "RSA"), ("payload_kind", "assurance_time"), ("assurance_domain", "production")],
)
def test_wrong_signed_fields_are_rejected(field: str, value: str) -> None:
    payload = {"kind": "assurance_evidence"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    receipt[field] = value
    receipt["receipt_digest"] = digest(receipt, exclude="receipt_digest")
    if field == "algorithm":
        with pytest.raises(InputError):
            _check(payload, receipt)
    else:
        assert _check(payload, receipt)


def test_revoked_key_is_ineligible() -> None:
    payload = {"kind": "assurance_evidence"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    profile = deepcopy(_profile())
    profile["revocations"] = [{"key_id": "fixture-key-005", "effective_at": "2026-09-29T09:01:00Z"}]
    profile["digest"] = digest(profile)
    assert "ISSUER_UNTRUSTED" in _check(payload, receipt, validate_profile(profile))


@pytest.mark.parametrize("encoded", ["not base64", "AA==", "A" * 88])
def test_malformed_signature_is_input_error(encoded: str) -> None:
    payload = {"kind": "assurance_evidence"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    receipt["signature"] = encoded
    receipt["receipt_digest"] = digest(receipt, exclude="receipt_digest")
    with pytest.raises(InputError):
        _check(payload, receipt)


def test_profile_change_breaks_self_digest() -> None:
    profile = deepcopy(_profile())
    profile["issuer_keys"][0]["public_key_base64"] = "A" * 43 + "="
    with pytest.raises(InputError, match="Digest mismatch"):
        validate_profile(profile)


def test_replayed_sequence_is_ineligible_within_one_verification_bundle() -> None:
    payload = {"kind": "assurance_evidence"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    seen: set[tuple[str, str, str]] = set()
    assert (
        verify_receipt(
            payload,
            receipt,
            _profile(),
            payload_kind="assurance_evidence",
            requested_domain="fixture_contract",
            requested_scope=SCOPE,
            as_of=NOW,
            seen_sequences=seen,
        )
        == []
    )
    assert "RECEIPT_REPLAY" in verify_receipt(
        payload,
        receipt,
        _profile(),
        payload_kind="assurance_evidence",
        requested_domain="fixture_contract",
        requested_scope=SCOPE,
        as_of=NOW,
        seen_sequences=seen,
    )


def test_expired_key_cannot_be_used_for_current_assessment() -> None:
    payload = {"kind": "assurance_evidence"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    profile = deepcopy(_profile())
    profile["issuer_keys"][0]["valid_until"] = "2026-09-29T09:30:00Z"
    profile["digest"] = digest(profile)
    assert "ISSUER_UNTRUSTED" in _check(payload, receipt, validate_profile(profile))


def test_wrong_trusted_key_rejects_otherwise_valid_receipt() -> None:
    payload = {"kind": "assurance_evidence"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    profile = deepcopy(_profile())
    profile["issuer_keys"][0]["public_key_base64"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    profile["digest"] = digest(profile)
    assert "SIGNATURE_INVALID" in _check(payload, receipt, validate_profile(profile))


def test_malformed_public_key_is_input_error() -> None:
    profile = deepcopy(_profile())
    profile["issuer_keys"][0]["public_key_base64"] = "not-base64"
    profile["digest"] = digest(profile)
    with pytest.raises(InputError):
        validate_profile(profile)


def test_unapproved_issuer_cannot_self_authorize_with_fixture_key() -> None:
    import base64

    from score_sw_fabric.assurance.origins import signing_bytes
    from tests.assurance_support import FIXTURE_PRIVATE_KEY

    payload = {"kind": "assurance_evidence"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    receipt["issuer_id"] = "unapproved-issuer"
    receipt["signature"] = base64.b64encode(
        FIXTURE_PRIVATE_KEY.sign(signing_bytes(receipt))
    ).decode()
    receipt["receipt_digest"] = digest(receipt, exclude="receipt_digest")
    assert "ISSUER_UNTRUSTED" in _check(payload, receipt)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("schema_version", 2, "VERSION_UNSUPPORTED"),
        ("kind", "assurance_decision", "KIND_MISMATCH"),
        ("algorithm", "RSA", "FIELD_UNKNOWN"),
        ("signature", "not-base64", "SIGNATURE_FORMAT"),
        ("payload_digest", "short", "HASH_FORMAT"),
        ("issued_at", "2026-09-29", "TIME_FORMAT"),
        ("nonce_or_sequence", "", "FIELD_TYPE"),
    ],
)
def test_receipt_one_field_malformed_matrix(field: str, value: object, code: str) -> None:
    payload = {"kind": "assurance_evidence"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    receipt[field] = value
    receipt["receipt_digest"] = digest(receipt, exclude="receipt_digest")
    with pytest.raises(InputError) as error:
        _check(payload, receipt)
    assert error.value.code == code


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("issuer_keys", "LIMIT_EXCEEDED"),
        ("identity_providers", "LIMIT_EXCEEDED"),
        ("role_assignments", "LIMIT_EXCEEDED"),
        ("independence_rules", "LIMIT_EXCEEDED"),
        ("import_rules", "LIMIT_EXCEEDED"),
        ("revocations", "LIMIT_EXCEEDED"),
        ("time_authorities", "LIMIT_EXCEEDED"),
    ],
)
def test_profile_list_limit_is_field_specific(
    field: str, code: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.assurance import origins

    profile = deepcopy(_profile())
    monkeypatch.setattr(origins, "MAX_REFERENCES", 1)
    monkeypatch.setattr(origins, "MAX_DECISIONS", 1)
    profile["limits"]["references"] = 1
    profile["limits"]["decisions"] = 1
    at_limit = deepcopy(profile)
    at_limit[field] = at_limit[field][:1]
    if field == "import_rules":
        at_limit[field] = read_json(
            ROOT / "tests/fixtures/assurance/imported-scope/trust-profile.json"
        )["import_rules"]
    elif field == "revocations":
        at_limit[field] = [{"key_id": "fixture-key-005", "effective_at": "2027-01-01T00:00:00Z"}]
    validate_profile(seal(at_limit))
    profile[field] = [{"extra": index} for index in range(2)]
    with pytest.raises(InputError) as error:
        validate_profile(seal(profile))
    assert error.value.code == code
    assert error.value.pointer == f"/trust_profile/{field}"


@pytest.mark.parametrize("field", sorted(PROFILE_FIELDS))
def test_every_missing_trust_profile_field_is_rejected(field: str) -> None:
    profile = _profile()
    profile.pop(field)
    with pytest.raises(InputError) as error:
        validate_profile(profile)
    assert error.value.code == "FIELD_UNKNOWN"
    assert error.value.pointer == "/trust_profile"


@pytest.mark.parametrize("field", sorted(RECEIPT_FIELDS))
def test_every_missing_receipt_field_is_rejected(field: str) -> None:
    payload = {"kind": "assurance_evidence"}
    receipt = fixture_receipt(payload, payload_kind="assurance_evidence")
    receipt.pop(field)
    with pytest.raises(InputError) as error:
        _check(payload, receipt)
    assert error.value.code == "FIELD_UNKNOWN"
    assert error.value.pointer == "/receipt"


@pytest.mark.parametrize(
    ("field", "change", "code"),
    [
        ("authority_source", "agent_claim", "TAILORING_UNVERIFIED"),
        ("issuer_keys", "too_many_receipt_kinds", "LIMIT_EXCEEDED"),
        ("identity_providers", "missing_authentication", "FIELD_UNKNOWN"),
        ("role_assignments", "string_scopes", "LIMIT_EXCEEDED"),
        ("role_assignments", "reverse_validity", "TIME_FORMAT"),
        ("independence_rules", "non_boolean_required", "FIELD_TYPE"),
        ("import_rules", "missing_policy_digest", "FIELD_UNKNOWN"),
        ("revocations", "bad_effective_at", "TIME_FORMAT"),
        ("time_authorities", "missing_key", "FIELD_UNKNOWN"),
    ],
)
def test_nested_trust_profile_is_validated_before_use(field: str, change: str, code: str) -> None:
    profile = _profile()
    if change == "agent_claim":
        profile["authority_source"]["kind"] = "agent_assertion"
    elif change == "too_many_receipt_kinds":
        profile["issuer_keys"][0]["receipt_kinds"] = ["assurance_evidence"] * 5
    elif change == "missing_authentication":
        profile["identity_providers"][0].pop("authentication_method")
    elif change == "string_scopes":
        profile["role_assignments"][0]["scope_ids"] = "component-005"
    elif change == "reverse_validity":
        profile["role_assignments"][0]["valid_from"] = "2028-01-01T00:00:00Z"
    elif change == "non_boolean_required":
        profile["independence_rules"][0]["required"] = 1
    elif change == "missing_policy_digest":
        profile["import_rules"] = [{"evidence_id": "fixture-evidence-005"}]
    elif change == "bad_effective_at":
        profile["revocations"] = [{"key_id": "fixture-key-005", "effective_at": "yesterday"}]
    else:
        profile["time_authorities"][0].pop("key_id")
    with pytest.raises(InputError) as error:
        validate_profile(seal(profile))
    assert error.value.code == code
