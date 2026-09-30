"""Trusted result classification requires exact signed origin and raw bytes."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.evidence import EVIDENCE_FIELDS, classify_evidence
from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml
from tests.assurance_support import fixture_receipt

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "tests/fixtures/assurance/passing-scope"
NOW = datetime(2026, 9, 29, 10, tzinfo=UTC)


def _inputs() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    return (
        read_json(BASE / "evidence.json"),
        read_json(BASE / "evidence-receipt.json"),
        read_json(BASE / "out/subject.json"),
        read_json(BASE / "policy.json"),
        read_yaml(ROOT / "profiles/assurance-fixture-v1.yaml"),
    )


def _check(
    *,
    evidence: dict[str, Any] | None = None,
    receipt: dict[str, Any] | None = None,
    domain: str = "fixture_contract",
    raw_root: Path | None = None,
) -> dict[str, Any]:
    original, signed, subject, policy, profile = _inputs()
    return classify_evidence(
        original if evidence is None else evidence,
        signed if receipt is None else receipt,
        subject,
        policy,
        profile,
        requested_domain=domain,
        requested_scope=subject["scope"],
        as_of=NOW,
        raw_root=BASE / "raw" if raw_root is None else raw_root,
    )


def test_fixture_protected_observation_is_fixture_eligible() -> None:
    result = _check()
    assert result["eligible"] is True
    assert result["assurance_domain"] == "fixture_contract"
    assert result["result"] == "pass"


def test_production_domain_rejects_fixture_receipt() -> None:
    assert _check(domain="production")["eligible"] is False


def test_agent_assertion_is_not_trusted() -> None:
    evidence, _, _, _, _ = _inputs()
    evidence["origin_class"] = "agent_assertion"
    changed = seal(evidence)
    assert "EVIDENCE_UNTRUSTED" in _check(evidence=changed)["reason_codes"]


def test_timeout_and_missing_measurement_are_unknown() -> None:
    evidence, _, _, _, _ = _inputs()
    evidence["termination"] = "timeout"
    evidence["measurements"] = {}
    changed = seal(evidence)
    result = _check(
        evidence=changed, receipt=fixture_receipt(changed, payload_kind="assurance_evidence")
    )
    assert result["eligible"] is False
    assert result["result"] == "unknown"
    assert "RESULT_TIMEOUT" in result["reason_codes"]


def test_wrong_tool_or_policy_is_ineligible_even_with_valid_signature() -> None:
    evidence, _, _, _, _ = _inputs()
    evidence["tool"] = {**evidence["tool"], "version": "2"}
    changed = seal(evidence)
    result = _check(
        evidence=changed, receipt=fixture_receipt(changed, payload_kind="assurance_evidence")
    )
    assert "TOOL_MISMATCH" in result["reason_codes"]


def test_signed_wrong_executable_digest_is_ineligible() -> None:
    evidence = _inputs()[0]
    evidence["tool"]["executable_digest"] = "0" * 64
    changed = seal(evidence)
    result = _check(
        evidence=changed,
        receipt=fixture_receipt(changed, payload_kind="assurance_evidence"),
    )
    assert result["eligible"] is False
    assert "TOOL_MISMATCH" in result["reason_codes"]


def test_missing_raw_bytes_are_ineligible(tmp_path: Path) -> None:
    result = _check(raw_root=tmp_path)
    assert result["eligible"] is False
    assert "RAW_OUTPUT_MISSING" in result["reason_codes"]


def test_truncated_raw_output_is_ineligible(tmp_path: Path) -> None:
    (tmp_path / "observed.json").write_bytes((BASE / "raw/observed.json").read_bytes()[:-1])
    result = _check(raw_root=tmp_path)
    assert result["eligible"] is False
    assert result["reason_codes"] == ["RAW_OUTPUT_MISMATCH"]


def test_missing_measurement_extraction_is_not_a_clean_result() -> None:
    evidence = _inputs()[0]
    evidence["measurements"] = {}
    changed = seal(evidence)
    receipt = fixture_receipt(changed, payload_kind="assurance_evidence")
    result = _check(evidence=changed, receipt=receipt)
    assert result["eligible"] is False
    assert "RESULT_UNKNOWN" in result["reason_codes"]


def test_unsigned_payload_change_is_ineligible() -> None:
    evidence, _, _, _, _ = _inputs()
    changed = deepcopy(evidence)
    changed["result"] = "fail"
    changed = seal(changed)
    assert "SUBJECT_MISMATCH" in _check(evidence=changed)["reason_codes"]


def test_measurement_result_conflict_is_ineligible_even_when_signed() -> None:
    evidence, _, _, _, _ = _inputs()
    evidence["measurements"] = {"obligation-a": False}
    changed = seal(evidence)
    receipt = fixture_receipt(changed, payload_kind="assurance_evidence")
    assert "RESULT_CONFLICT" in _check(evidence=changed, receipt=receipt)["reason_codes"]


def test_import_requires_reviewed_rule_and_original_attestation() -> None:
    evidence, _, _, _, _ = _inputs()
    evidence["origin_class"] = "imported_verified"
    evidence["import_chain"] = [{"original_issuer": "untrusted", "transformation": "copy"}]
    changed = seal(evidence)
    receipt = fixture_receipt(changed, payload_kind="assurance_evidence")
    assert "IMPORT_RULE_MISSING" in _check(evidence=changed, receipt=receipt)["reason_codes"]


def test_policy_authorized_import_preserves_original_signed_result() -> None:
    folder = ROOT / "tests/fixtures/assurance/imported-scope"
    _, _, subject, _, _ = _inputs()
    result = classify_evidence(
        read_json(folder / "evidence.json"),
        read_json(folder / "evidence-receipt.json"),
        subject,
        read_json(folder / "policy.json"),
        read_json(folder / "trust-profile.json"),
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        as_of=NOW,
        raw_root=BASE / "raw",
    )
    assert result["eligible"] is True
    assert result["origin_class"] == "imported_verified"


def test_import_cannot_drop_original_receipt_or_change_result() -> None:
    folder = ROOT / "tests/fixtures/assurance/imported-scope"
    _, _, subject, _, _ = _inputs()
    imported = read_json(folder / "evidence.json")
    imported["import_chain"][0]["original_receipt_digest"] = "0" * 64
    imported = seal(imported)
    receipt = fixture_receipt(
        imported, payload_kind="assurance_evidence", nonce="fixture-import-sequence-1"
    )
    result = classify_evidence(
        imported,
        receipt,
        subject,
        read_json(folder / "policy.json"),
        read_json(folder / "trust-profile.json"),
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        as_of=NOW,
        raw_root=BASE / "raw",
    )
    assert result["eligible"] is False
    assert "IMPORT_CHAIN_UNVERIFIED" in result["reason_codes"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("original_result", "fail"),
        ("original_subject_digest", "0" * 64),
        ("original_issuer_id", "unapproved-issuer"),
    ],
)
def test_import_preservation_fields_cannot_be_rewritten(field: str, value: str) -> None:
    folder = ROOT / "tests/fixtures/assurance/imported-scope"
    _, _, subject, _, _ = _inputs()
    imported = read_json(folder / "evidence.json")
    imported["import_chain"][0][field] = value
    imported = seal(imported)
    receipt = fixture_receipt(
        imported, payload_kind="assurance_evidence", nonce="fixture-import-sequence-1"
    )
    result = classify_evidence(
        imported,
        receipt,
        subject,
        read_json(folder / "policy.json"),
        read_json(folder / "trust-profile.json"),
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        as_of=NOW,
        raw_root=BASE / "raw",
    )
    assert result["eligible"] is False
    assert "IMPORT_CHAIN_UNVERIFIED" in result["reason_codes"]


def test_import_rule_age_ceiling_blocks_old_original() -> None:
    folder = ROOT / "tests/fixtures/assurance/imported-scope"
    _, _, subject, _, _ = _inputs()
    profile = read_json(folder / "trust-profile.json")
    profile["import_rules"][0]["max_age_seconds"] = 1
    profile = seal(profile)
    result = classify_evidence(
        read_json(folder / "evidence.json"),
        read_json(folder / "evidence-receipt.json"),
        subject,
        read_json(folder / "policy.json"),
        profile,
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        as_of=NOW,
        raw_root=BASE / "raw",
    )
    assert "RESULT_STALE" in result["reason_codes"]


@pytest.mark.parametrize(
    "change,code",
    [
        ("candidate_input", "SUBJECT_MISMATCH"),
        ("process_baseline", "PROCESS_MISMATCH"),
        ("profile_digest", "PROFILE_MISMATCH"),
        ("policy_digest", "POLICY_MISMATCH"),
        ("collector_id", "COLLECTOR_UNTRUSTED"),
        ("scope", "SCOPE_MISMATCH"),
        ("raw_hash", "RAW_OUTPUT_MISMATCH"),
        ("crash", "RESULT_UNKNOWN"),
        ("fixture_replay", "EVIDENCE_UNTRUSTED"),
    ],
)
def test_signed_observation_still_requires_exact_bindings(change: str, code: str) -> None:
    evidence, _, _, _, _ = _inputs()
    if change == "candidate_input":
        evidence["inputs"][0]["digest"] = "0" * 64
    elif change == "process_baseline":
        evidence["process_baseline"] = {"changed": True}
    elif change == "profile_digest":
        evidence["profile_digests"]["artifact"] = "0" * 64
    elif change == "policy_digest":
        evidence["execution_policy_digest"] = "0" * 64
    elif change == "collector_id":
        evidence["collector_id"] = "wrong-collector"
    elif change == "scope":
        evidence["scope"]["id"] = "other-component"
    elif change == "raw_hash":
        evidence["raw_outputs"][0]["sha256"] = "0" * 64
    elif change == "crash":
        evidence["termination"] = "crash"
        evidence["result"] = "unknown"
    else:
        evidence["origin_class"] = "fixture_replay"
    changed = seal(evidence)
    receipt = fixture_receipt(changed, payload_kind="assurance_evidence")
    assert code in _check(evidence=changed, receipt=receipt)["reason_codes"]


@pytest.mark.parametrize("field", sorted(EVIDENCE_FIELDS))
def test_every_missing_evidence_field_is_rejected(field: str) -> None:
    evidence = _inputs()[0]
    evidence.pop(field)
    with pytest.raises(InputError) as error:
        _check(evidence=evidence)
    assert error.value.code == "FIELD_UNKNOWN"
    assert error.value.pointer == "/evidence"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("subject_digest", "wrong", "HASH_FORMAT"),
        ("started_at", "not-a-time", "TIME_FORMAT"),
        ("origin_class", "pretend_protected", "FIELD_UNKNOWN"),
        ("termination", "ignored", "FIELD_UNKNOWN"),
        ("result", "maybe", "FIELD_UNKNOWN"),
    ],
)
def test_resigned_evidence_one_field_format_matrix(field: str, value: object, code: str) -> None:
    evidence = _inputs()[0]
    evidence[field] = value
    with pytest.raises(InputError) as error:
        _check(evidence=seal(evidence))
    assert error.value.code == code


def test_public_replayed_receipts_are_order_independent_and_all_ineligible(
    capsys: pytest.CaptureFixture[str],
) -> None:
    import hashlib
    import json
    from tempfile import TemporaryDirectory

    from score_sw_fabric.catalog.export import canonical
    from score_sw_fabric.cli import main

    original = read_json(BASE / "evidence.json")
    second = deepcopy(original)
    second["evidence_id"] = "another-evidence-005"
    second = seal(second)
    records = [original, second]
    receipts = [
        read_json(BASE / "evidence-receipt.json"),
        fixture_receipt(second, payload_kind="assurance_evidence", nonce="fixture-sequence-1"),
    ]
    with TemporaryDirectory(prefix=".assurance-evidence-order-", dir=ROOT) as directory:
        scratch = Path(directory)
        request = read_yaml(BASE / "evidence-request.yaml")
        for field, values in (("evidence", records), ("receipts", receipts)):
            refs = []
            for index, record in enumerate(values):
                content = canonical(record)
                name = f"{field}-{index}.json"
                (scratch / name).write_bytes(content)
                refs.append(
                    {
                        "path": name,
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "semantic_digest": record[
                            "receipt_digest" if field == "receipts" else "digest"
                        ],
                    }
                )
            request["inputs"][field] = refs
        request["output_root"] = f"{scratch.name}/out"
        path = scratch / "request.json"
        out = scratch / "out/evidence-result.json"
        results = []
        for reverse in (False, True):
            for field in ("evidence", "receipts"):
                request["inputs"][field] = sorted(
                    request["inputs"][field], key=lambda item: item["path"], reverse=reverse
                )
            path.write_text(json.dumps(request))
            assert (
                main(
                    [
                        "assurance",
                        "evidence",
                        "--request",
                        str(path),
                        "--out",
                        str(out),
                        "--json",
                    ]
                )
                == 1
            )
            capsys.readouterr()
            results.append(out.read_bytes())
        assert results[0] == results[1]
        eligibility = read_json(out)["eligibility"]
        assert [item["evidence_id"] for item in eligibility] == [
            "another-evidence-005",
            "fixture-evidence-005",
        ]
        assert all("RECEIPT_REPLAY" in item["reason_codes"] for item in eligibility)
