"""Assurance CLI publishes complete subject outputs and preserves prior results."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from score_sw_fabric.cli import main

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "tests/fixtures/assurance/passing-scope/subject-request.yaml"


def test_subject_cli_seals_fixture_domain_result(capsys) -> None:  # type: ignore[no-untyped-def]
    out = ROOT / "tests/fixtures/assurance/passing-scope/out/subject.json"
    assert (
        main(["assurance", "subject", "--request", str(REQUEST), "--out", str(out), "--json"]) == 0
    )
    response = json.loads(capsys.readouterr().out)
    assert response["assurance_domain"] == "fixture_contract"
    subject = json.loads(out.read_text())
    assert subject["digest"] == response["digest"]
    assert subject["expected_obligation_ids"] == ["obligation-a", "obligation-b"]


def test_malformed_input_preserves_existing_output(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    out = ROOT / "tests/fixtures/assurance/passing-scope/out/sentinel.json"
    out.write_bytes(b"sentinel")
    bad = tmp_path / "bad.yaml"
    bad.write_text("schema_version: true\n")
    try:
        assert (
            main(["assurance", "subject", "--request", str(bad), "--out", str(out), "--json"]) == 2
        )
        assert out.read_bytes() == b"sentinel"
        assert "code" in json.loads(capsys.readouterr().err)
    finally:
        out.unlink()


def test_evidence_cli_fixture_result_is_explicitly_fixture_only(capsys) -> None:  # type: ignore[no-untyped-def]
    request = ROOT / "tests/fixtures/assurance/passing-scope/evidence-request.yaml"
    out = ROOT / "tests/fixtures/assurance/passing-scope/out/evidence-result.json"
    assert (
        main(["assurance", "evidence", "--request", str(request), "--out", str(out), "--json"]) == 0
    )
    response = json.loads(capsys.readouterr().out)
    assert response["assurance_domain"] == "fixture_contract"
    assert response["outcome"] == "eligible"
    report = json.loads(out.read_text())
    assert report["eligibility"][0]["eligible"] is True


def test_decision_cli_requires_authenticated_fixture_authority(capsys) -> None:  # type: ignore[no-untyped-def]
    request = ROOT / "tests/fixtures/assurance/passing-scope/decision-request.yaml"
    out = ROOT / "tests/fixtures/assurance/passing-scope/out/decision-result.json"
    assert (
        main(["assurance", "decision", "--request", str(request), "--out", str(out), "--json"]) == 0
    )
    response = json.loads(capsys.readouterr().out)
    assert response["assurance_domain"] == "fixture_contract"
    assert response["outcome"] == "eligible"
    assert json.loads(out.read_text())["eligibility"][0]["approves"] is True


@pytest.mark.parametrize(
    ("signature", "exit_code", "reason"),
    [("not-base64", 2, "SIGNATURE_FORMAT"), ("A" * 86 + "==", 1, "SIGNATURE_INVALID")],
)
def test_public_decision_receipt_errors_are_bounded_and_complete(
    signature: str,
    exit_code: int,
    reason: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import hashlib

    from score_sw_fabric.assurance.models import digest
    from score_sw_fabric.catalog.export import canonical
    from score_sw_fabric.process_source.reader import read_json, read_yaml

    folder = ROOT / "tests/fixtures/assurance/passing-scope"
    with TemporaryDirectory(prefix=".assurance-decision-", dir=ROOT) as directory:
        scratch = Path(directory)
        receipt = read_json(folder / "decision-receipt.json")
        receipt["signature"] = signature
        receipt["receipt_digest"] = digest(receipt, exclude="receipt_digest")
        payload = canonical(receipt)
        (scratch / "receipt.json").write_bytes(payload)
        request = read_yaml(folder / "decision-request.yaml")
        request["inputs"]["receipts"] = [
            {
                "path": "receipt.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "semantic_digest": receipt["receipt_digest"],
            }
        ]
        request["output_root"] = f"{scratch.name}/out"
        request_path = scratch / "request.json"
        request_path.write_text(json.dumps(request))
        out = scratch / "out/decision-result.json"
        out.parent.mkdir()
        out.write_bytes(b"prior complete result")
        assert (
            main(
                [
                    "assurance",
                    "decision",
                    "--request",
                    str(request_path),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == exit_code
        )
        output = capsys.readouterr()
        if exit_code == 2:
            diagnostic = json.loads(output.err)
            assert diagnostic["code"] == reason
            assert len(diagnostic["message"]) <= 4096
            assert out.read_bytes() == b"prior complete result"
        else:
            summary = json.loads(output.out)
            assert summary["assurance_domain"] == "fixture_contract"
            assert summary["outcome"] == "ineligible"
            assert reason in summary["reasons"]
            assert read_json(out)["eligibility"][0]["eligible"] is False


@pytest.mark.parametrize("argument", ["--private-key", "--approve", "--actor-password"])
def test_decision_command_exposes_no_signing_or_approval_argument(argument: str) -> None:
    request = ROOT / "tests/fixtures/assurance/passing-scope/decision-request.yaml"
    with pytest.raises(SystemExit) as error:
        main(
            [
                "assurance",
                "decision",
                "--request",
                str(request),
                "--out",
                "unused.json",
                argument,
                "secret",
            ]
        )
    assert error.value.code == 2


def test_assurance_has_no_approval_submission_command() -> None:
    with pytest.raises(SystemExit) as error:
        main(["assurance", "approve"])
    assert error.value.code == 2


def test_gate_cli_passes_only_fixture_scope_and_blocks_missing_review(capsys) -> None:  # type: ignore[no-untyped-def]
    passing = ROOT / "tests/fixtures/assurance/passing-scope"
    blocked = ROOT / "tests/fixtures/assurance/blocked-scope"
    out = passing / "out/assessment.json"
    assert (
        main(
            [
                "assurance",
                "gate",
                "--request",
                str(passing / "gate-request.yaml"),
                "--out",
                str(out),
                "--json",
            ]
        )
        == 0
    )
    response = json.loads(capsys.readouterr().out)
    assert response["outcome"] == "pass" and response["assurance_domain"] == "fixture_contract"
    assert json.loads(out.read_text())["gate_results"][0]["outcome"] == "pass"
    out = blocked / "out/assessment.json"
    assert (
        main(
            [
                "assurance",
                "gate",
                "--request",
                str(blocked / "gate-request.yaml"),
                "--out",
                str(out),
                "--json",
            ]
        )
        == 1
    )
    response = json.loads(capsys.readouterr().out)
    assert response["outcome"] == "blocked"


def test_verify_cli_reproduces_pass_and_blocked_assessments(capsys) -> None:  # type: ignore[no-untyped-def]
    context = ROOT / "tests/fixtures/assurance/fixture-trust/context.json"
    for scope, historical in [("passing-scope", "pass"), ("blocked-scope", "blocked")]:
        assessment = ROOT / f"tests/fixtures/assurance/{scope}/out/assessment.json"
        assert (
            main(
                [
                    "assurance",
                    "verify",
                    "--assessment",
                    str(assessment),
                    "--trust-context",
                    str(context),
                    "--json",
                ]
            )
            == 0
        )
        response = json.loads(capsys.readouterr().out)
        assert response["reproduced"] is True
        assert response["outcome"] == historical
