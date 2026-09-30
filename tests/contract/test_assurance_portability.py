"""A portable assessment must recheck all bound bytes and reproduce its result offline."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.assurance.package import verify_assessment
from score_sw_fabric.process_source.reader import InputError, read_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "tests/fixtures/assurance/passing-scope"
CONTEXT = ROOT / "tests/fixtures/assurance/fixture-trust/context.json"


def _assessment() -> dict[str, Any]:
    return read_json(BASE / "out/assessment.json")


def test_complete_fixture_assessment_reproduces_without_fabro() -> None:
    result = verify_assessment(_assessment(), read_json(CONTEXT))
    assert result["reproduced"] is True
    assert result["outcome"] == "pass"


def test_altered_recorded_gate_outcome_is_detected() -> None:
    assessment = deepcopy(_assessment())
    assessment["gate_results"][0]["outcome"] = "fail"
    assessment["gate_results"][0] = seal(assessment["gate_results"][0])
    assessment = seal(assessment)
    result = verify_assessment(assessment, read_json(CONTEXT))
    assert result["reproduced"] is False


def test_embedded_raw_byte_tamper_is_detected() -> None:
    assessment = deepcopy(_assessment())
    assessment["raw_output_refs"][0]["content_base64"] = "AAAA"
    assessment = seal(assessment)
    result = verify_assessment(assessment, read_json(CONTEXT))
    assert result["reproduced"] is False


def test_missing_independent_trust_context_blocks_verification() -> None:
    result = verify_assessment(_assessment(), {})
    assert result["reproduced"] is False


def test_malformed_embedded_base64_type_is_detected() -> None:
    assessment = deepcopy(_assessment())
    assessment["subject"]["closure"]["plan"]["content_base64"] = 42
    assessment = seal(assessment)
    result = verify_assessment(assessment, read_json(CONTEXT))
    assert result["reproduced"] is False
    assert result["reason_codes"] == ["CLOSURE_MISSING"]


def test_malformed_top_level_collection_returns_input_error() -> None:
    assessment = deepcopy(_assessment())
    assessment["evidence_records"] = "not-an-array"
    assessment = seal(assessment)
    with pytest.raises(InputError, match="Array limit"):
        verify_assessment(assessment, read_json(CONTEXT))


@pytest.mark.parametrize("field", sorted(set(_assessment()) - {"schema_version", "kind"}))
def test_every_missing_portable_assessment_field_is_rejected(field: str) -> None:
    assessment = _assessment()
    assessment.pop(field)
    with pytest.raises(InputError) as error:
        verify_assessment(assessment, read_json(CONTEXT))
    assert error.value.code == "FIELD_UNKNOWN"
    assert error.value.pointer == "/assessment"


@pytest.mark.parametrize(
    ("field", "limit"),
    [
        ("policy_refs", 1),
        ("trust_context_refs", 1),
        ("gate_results", 1),
        ("history_refs", 1),
    ],
)
def test_singleton_package_fields_refuse_second_entry(field: str, limit: int) -> None:
    assessment = _assessment()
    assert len(assessment[field]) <= limit
    assessment[field] = [assessment[field][0] if assessment[field] else {}] * (limit + 1)
    with pytest.raises(InputError) as error:
        verify_assessment(seal(assessment), read_json(CONTEXT))
    assert error.value.code == "LIMIT_EXCEEDED"
    assert error.value.pointer == f"/assessment/{field}"


@pytest.mark.parametrize(
    ("field", "limit"),
    [
        ("evidence_records", 1),
        ("decision_records", 1),
        ("receipts", 2),
        ("raw_output_refs", 1),
        ("limitations", 10_000),
    ],
)
def test_package_array_exact_limit_and_one_over(
    field: str, limit: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.assurance import models

    monkeypatch.setattr(models, "MAX_EVIDENCE", 1)
    monkeypatch.setattr(models, "MAX_DECISIONS", 1)
    original = _assessment()
    if field == "limitations":
        original[field] = original[field] * limit
        assert verify_assessment(seal(original), read_json(CONTEXT))["reproduced"] is False
    else:
        assert len(original[field]) == limit
        assert verify_assessment(original, read_json(CONTEXT))["reproduced"] is True
    over = deepcopy(original)
    over[field].append(deepcopy(over[field][0]))
    with pytest.raises(InputError) as error:
        verify_assessment(seal(over), read_json(CONTEXT))
    assert error.value.code == "LIMIT_EXCEEDED"
    assert error.value.pointer == f"/assessment/{field}"


@pytest.mark.parametrize(
    ("part", "expected"),
    [
        ("receipt_absent", "ASSESSMENT_MISMATCH"),
        ("raw_output_absent", "RAW_OUTPUT_MISMATCH"),
        ("earlier_time", "ASSESSMENT_MISMATCH"),
    ],
)
def test_resealed_incomplete_portable_closure_cannot_reproduce_pass(
    part: str, expected: str
) -> None:
    assessment = deepcopy(_assessment())
    if part == "receipt_absent":
        assessment["receipts"].pop(0)
    elif part == "raw_output_absent":
        assessment["raw_output_refs"].clear()
    else:
        assessment["gate_results"][0]["as_of"] = "2026-09-29T08:00:00Z"
        assessment["gate_results"][0] = seal(assessment["gate_results"][0])
    result = verify_assessment(seal(assessment), read_json(CONTEXT))
    assert result["reproduced"] is False
    assert result["reason_codes"] == [expected]


def test_wrong_independent_root_cannot_reproduce_pass() -> None:
    context = read_json(CONTEXT)
    context["profile"]["issuer_keys"][0]["public_key_base64"] = (
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    )
    context["profile"] = seal(context["profile"])
    context["profile_digest"] = context["profile"]["digest"]
    result = verify_assessment(_assessment(), context)
    assert result["reproduced"] is False
    assert result["reason_codes"] == ["TRUST_CONTEXT_MISMATCH"]


def test_unknown_assessment_version_cannot_reproduce() -> None:
    from score_sw_fabric.process_source.reader import InputError

    assessment = _assessment()
    assessment["schema_version"] = 2
    with pytest.raises(InputError, match="version"):
        verify_assessment(seal(assessment), read_json(CONTEXT))


def test_missing_source_file_is_a_closure_error() -> None:
    assessment = deepcopy(_assessment())
    assessment["subject"]["source_files"].pop(0)
    result = verify_assessment(seal(assessment), read_json(CONTEXT))
    assert result["reproduced"] is False
    assert result["reason_codes"] == ["CLOSURE_MISSING"]


def test_resealed_forged_prior_cannot_authenticate_stale_history() -> None:
    stale = read_json(ROOT / "tests/fixtures/assurance/stale-scope/out/assessment.json")
    forged = stale["history_refs"][0]
    forged["gate_results"][0]["outcome"] = "fail"
    forged["gate_results"][0] = seal(forged["gate_results"][0])
    forged = seal(forged)
    stale["history_refs"] = [forged]
    stale["gate_results"][0]["freshness"]["prior_assessment_digest"] = forged["digest"]
    stale["gate_results"][0]["freshness"] = seal(stale["gate_results"][0]["freshness"])
    stale["gate_results"][0] = seal(stale["gate_results"][0])
    result = verify_assessment(seal(stale), read_json(CONTEXT))
    assert result["reproduced"] is False
    assert result["reason_codes"] == ["HISTORY_MISMATCH"]


def test_public_stale_gate_rejects_forged_prior_before_publication(
    tmp_path: Path, capsys: Any
) -> None:
    import hashlib
    import json

    import yaml

    from score_sw_fabric.catalog.export import canonical
    from score_sw_fabric.cli import main
    from score_sw_fabric.process_source.reader import read_yaml

    prior = _assessment()
    prior["gate_results"][0]["outcome"] = "fail"
    prior["gate_results"][0] = seal(prior["gate_results"][0])
    prior = seal(prior)
    selected = tmp_path / "forged-prior.json"
    selected.write_bytes(canonical(prior))
    request = read_yaml(ROOT / "tests/fixtures/assurance/stale-scope/gate-request.yaml")
    request["inputs"]["prior_assessment"] = {
        "path": selected.name,
        "sha256": hashlib.sha256(selected.read_bytes()).hexdigest(),
        "semantic_digest": prior["digest"],
    }
    selected_request = tmp_path / "request.yaml"
    selected_request.write_text(yaml.safe_dump(request))
    out = ROOT / "tests/fixtures/assurance/stale-scope/out/forged-prior-guard.json"
    try:
        assert not out.exists()
        assert (
            main(
                [
                    "assurance",
                    "gate",
                    "--request",
                    str(selected_request),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 2
        )
        assert json.loads(capsys.readouterr().err)["code"] == "HISTORY_MISMATCH"
        assert not out.exists()
    finally:
        out.unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("next_route", "release"),
        ("unmet_predicate_ids", ["forged-unmet"]),
        (
            "scope",
            {"kind": "component", "id": "other-component", "purpose": "fixture verification"},
        ),
        ("engineering_readiness", "pass"),
        ("release", "pass"),
    ],
)
def test_resealed_readable_report_must_match_replayed_gate(field: str, replacement: Any) -> None:
    assessment = deepcopy(_assessment())
    assessment["readable_report"][field] = replacement
    result = verify_assessment(seal(assessment), read_json(CONTEXT))
    assert result["reproduced"] is False
    assert result["reason_codes"] == ["ASSESSMENT_MISMATCH"]


def test_resealed_limitations_must_match_replayed_gate() -> None:
    assessment = deepcopy(_assessment())
    assessment["limitations"] = ["No limitations; release authorized."]
    result = verify_assessment(seal(assessment), read_json(CONTEXT))
    assert result["reproduced"] is False
    assert result["reason_codes"] == ["ASSESSMENT_MISMATCH"]


def test_portable_closure_order_does_not_change_replayed_result() -> None:
    assessment = deepcopy(_assessment())
    original_gate = deepcopy(assessment["gate_results"][0])
    original_subject = deepcopy(assessment["subject"]["manifest"])
    closure = assessment["subject"]["closure"]
    assessment["subject"]["closure"] = dict(reversed(list(closure.items())))
    assessment["subject"]["source_files"].reverse()
    assessment["receipts"].reverse()
    result = verify_assessment(seal(assessment), read_json(CONTEXT))
    assert result["reproduced"] is True
    assert result["outcome"] == "pass"
    assert assessment["gate_results"][0] == original_gate
    assert assessment["subject"]["manifest"] == original_subject


def test_original_blocked_assessment_reproduces_without_promoting_it() -> None:
    blocked = read_json(ROOT / "tests/fixtures/assurance/blocked-scope/out/assessment.json")
    result = verify_assessment(blocked, read_json(CONTEXT))
    assert result["reproduced"] is True
    assert result["outcome"] == "blocked"


def test_portable_verifier_does_not_invoke_external_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Portable verifier invoked an external runtime")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = verify_assessment(_assessment(), read_json(CONTEXT))
    assert result["reproduced"] is True
    assert result["outcome"] == "pass"


def test_unknown_embedded_gate_version_is_rejected() -> None:
    from score_sw_fabric.process_source.reader import InputError

    assessment = deepcopy(_assessment())
    assessment["gate_results"][0]["schema_version"] = 2
    assessment["gate_results"][0] = seal(assessment["gate_results"][0])
    with pytest.raises(InputError) as raised:
        verify_assessment(seal(assessment), read_json(CONTEXT))
    assert raised.value.code == "VERSION_UNSUPPORTED"


def test_historical_pass_replays_but_later_current_use_remains_stale() -> None:
    folder = ROOT / "tests/fixtures/assurance/no-impact-scope/out"
    prior = read_json(folder / "old-assessment.json")
    current = read_json(folder / "current-assessment.json")
    context = read_json(CONTEXT)
    prior_bytes = (folder / "old-assessment.json").read_bytes()
    prior_result = verify_assessment(prior, context)
    current_result = verify_assessment(current, context)
    assert prior_result["reproduced"] is True and prior_result["outcome"] == "pass"
    assert current_result["reproduced"] is True and current_result["outcome"] == "stale"
    assert current["gate_results"][0]["freshness"]["scope_expansion"] == "whole_gate"
    assert (folder / "old-assessment.json").read_bytes() == prior_bytes


def test_stale_replay_rejects_resealed_unchecked_evidence_receipt() -> None:
    from score_sw_fabric.assurance.models import digest

    current = read_json(
        ROOT / "tests/fixtures/assurance/no-impact-scope/out/current-assessment.json"
    )
    receipt = current["receipts"][0]
    assert receipt["payload_kind"] == "assurance_evidence"
    receipt["signature"] = (
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
    )
    receipt["receipt_digest"] = digest(receipt, exclude="receipt_digest")
    result = verify_assessment(seal(current), read_json(CONTEXT))
    assert result["reproduced"] is False


def test_stale_replay_rejects_missing_unchanged_receipt() -> None:
    current = read_json(
        ROOT / "tests/fixtures/assurance/no-impact-scope/out/current-assessment.json"
    )
    assert current["receipts"][0]["payload_kind"] == "assurance_evidence"
    current["receipts"].pop(0)
    result = verify_assessment(seal(current), read_json(CONTEXT))
    assert result["reproduced"] is False


def test_resealed_orphan_receipt_cannot_reproduce_pass() -> None:
    from score_sw_fabric.assurance.models import digest

    assessment = _assessment()
    orphan = deepcopy(assessment["receipts"][0])
    orphan["payload_digest"] = "f" * 64
    orphan["receipt_digest"] = digest(orphan, exclude="receipt_digest")
    assessment["receipts"].append(orphan)
    result = verify_assessment(seal(assessment), read_json(CONTEXT))
    assert result["reproduced"] is False


def test_stale_replay_rejects_resealed_raw_output_substitution() -> None:
    import base64
    import hashlib

    current = read_json(
        ROOT / "tests/fixtures/assurance/no-impact-scope/out/current-assessment.json"
    )
    forged = b"forged-observation\n"
    raw = current["raw_output_refs"][0]
    raw["content_base64"] = base64.b64encode(forged).decode("ascii")
    raw["bytes"] = len(forged)
    raw["sha256"] = hashlib.sha256(forged).hexdigest()
    result = verify_assessment(seal(current), read_json(CONTEXT))
    assert result["reproduced"] is False


def test_stale_replay_rejects_missing_raw_output() -> None:
    current = read_json(
        ROOT / "tests/fixtures/assurance/no-impact-scope/out/current-assessment.json"
    )
    current["raw_output_refs"].clear()
    result = verify_assessment(seal(current), read_json(CONTEXT))
    assert result["reproduced"] is False


def test_resealed_unreferenced_source_file_cannot_reproduce() -> None:
    import base64
    import hashlib

    assessment = _assessment()
    raw = b"Unreferenced source\n"
    assessment["subject"]["source_files"].append(
        {
            "path": "unreferenced.rst",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "content_base64": base64.b64encode(raw).decode("ascii"),
        }
    )
    result = verify_assessment(seal(assessment), read_json(CONTEXT))
    assert result["reproduced"] is False


@pytest.mark.parametrize("part", ["evidence", "receipt"])
def test_not_started_replay_checks_embedded_record_digests(part: str, tmp_path: Path) -> None:
    import yaml

    from score_sw_fabric.assurance.package import gate_request
    from score_sw_fabric.process_source.reader import InputError, read_yaml

    request = read_yaml(BASE / "gate-request.yaml")
    request["gate_mode"] = "not_started"
    selected_request = tmp_path / "request.yaml"
    selected_request.write_text(yaml.safe_dump(request))
    output = BASE / "out/not-started-closure-guard.json"
    try:
        assessment = gate_request(selected_request, output)
        assert assessment["gate_results"][0]["outcome"] == "not_evaluated"
        assert verify_assessment(assessment, read_json(CONTEXT))["reproduced"] is True
        if part == "evidence":
            assessment["evidence_records"][0]["result"] = "fail"
        else:
            assessment["receipts"][0]["signature"] = (
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
            )
        with pytest.raises(InputError) as raised:
            verify_assessment(seal(assessment), read_json(CONTEXT))
        assert raised.value.code == "SEMANTIC_DIGEST"
    finally:
        output.unlink(missing_ok=True)
