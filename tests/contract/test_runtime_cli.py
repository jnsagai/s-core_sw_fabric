"""Public runtime commands return stable 0/1/2 outcomes and guard every output."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import read_json
from score_sw_fabric.runtime import operations
from score_sw_fabric.runtime.client import CAPABILITIES, FabroClient
from score_sw_fabric.runtime.ledger import IntentLedger
from score_sw_fabric.runtime.request import RuntimeRequest, load_request
from tests.runtime_support import COMMIT, TOKEN, FakeFabro, baseline, write_request

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fabro(monkeypatch: pytest.MonkeyPatch) -> FakeFabro:
    simulated = FakeFabro()

    def selected(request: RuntimeRequest) -> FabroClient:
        # Exercise the real request credential provider against simulated transport.
        return FabroClient(
            request.runtime_profile,
            expected_commit=COMMIT,
            credential_provider=request.credential,
            transport=simulated.transport,
        )

    monkeypatch.setattr(operations, "selected_client", selected)
    return simulated


def _cli(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, dict[str, Any] | None, str]:
    status = main(["runtime", *args, "--json"])
    captured = capsys.readouterr()
    text = captured.out or captured.err
    try:
        payload = json.loads(text.strip().splitlines()[-1]) if text.strip() else None
    except json.JSONDecodeError:
        payload = None
    return status, payload, text


def test_register_run_status_export_verify_journey(
    tmp_path: Path, fabro: FakeFabro, capsys: pytest.CaptureFixture[str]
) -> None:
    request = write_request(tmp_path / "work", fabro)
    out = tmp_path / "out"
    status, payload, _ = _cli(
        capsys, "register", "--request", str(request), "--out", str(out / "v.json")
    )
    assert status == 0 and payload is not None
    assert payload["creation_state"] == "prepared"
    assert payload["engineering_readiness"] == "not_evaluated"
    status, payload, _ = _cli(
        capsys, "run", "--request", str(request), "--out", str(out / "b.json")
    )
    assert status == 0 and payload is not None
    assert payload["start_state"] == "started"
    run_id = payload["run_id"]
    status, payload, _ = _cli(
        capsys, "run", "--request", str(request), "--out", str(out / "b.json")
    )
    assert status == 0 and payload is not None and payload["run_id"] == run_id
    assert fabro.posts("/api/v1/runs") == 1 and fabro.posts("/start") == 1
    status, payload, _ = _cli(
        capsys, "status", "--request", str(request), "--out", str(out / "s.json")
    )
    assert status == 0 and payload is not None
    assert payload["native_status"] == "succeeded"
    snapshot = read_json(out / "s.json")
    assert snapshot["kind"] == "runtime_snapshot"
    assert snapshot["assurance_decisions"] == 0
    status, payload, _ = _cli(
        capsys, "export", "--request", str(request), "--out", str(out / "e.json")
    )
    assert status == 0 and payload is not None and payload["completeness"] == "complete"
    calls = len(fabro.calls)
    status, payload, _ = _cli(capsys, "verify", "--export", str(out / "e.json"))
    assert status == 0 and payload is not None and payload["reproduced"] is True
    assert len(fabro.calls) == calls
    assert TOKEN not in (out / "e.json").read_text()


def test_lost_create_publishes_reconciliation_and_label_never_clears_it(
    tmp_path: Path, fabro: FakeFabro, capsys: pytest.CaptureFixture[str]
) -> None:
    fabro.lose_create_response = True
    request = write_request(tmp_path / "work", fabro)
    out = tmp_path / "binding.json"
    status, payload, _ = _cli(capsys, "run", "--request", str(request), "--out", str(out))
    assert status == 1 and payload is not None
    assert payload["creation_state"] == "reconciliation_required"
    assert payload["reason_codes"] == ["RUN_CREATE_UNCERTAIN"]
    assert "run_id" not in payload or payload["run_id"] is None
    # Fabro holds a run carrying the intent label, but no list/label route is a capability.
    assert "run_list" not in CAPABILITIES
    fabro.lose_create_response = False
    status, payload, _ = _cli(capsys, "run", "--request", str(request), "--out", str(out))
    assert status == 1 and payload is not None
    assert payload["creation_state"] == "reconciliation_required"
    assert fabro.posts("/api/v1/runs") == 1
    assert len(fabro.runs) == 1


def test_interrupted_create_in_flight_becomes_reconciliation_without_post(
    tmp_path: Path, fabro: FakeFabro, capsys: pytest.CaptureFixture[str]
) -> None:
    request = write_request(tmp_path / "work", fabro)
    out = tmp_path / "binding.json"
    assert _cli(capsys, "register", "--request", str(request), "--out", str(out))[0] == 0
    selected = load_request(request)
    IntentLedger(selected.ledger_root).begin_create(selected.intent["intent_id"])
    status, payload, _ = _cli(capsys, "run", "--request", str(request), "--out", str(out))
    assert status == 1 and payload is not None
    assert payload["creation_state"] == "reconciliation_required"
    assert fabro.posts("/api/v1/runs") == 0


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("package_byte", "PACKAGE_DRIFT"),
        ("token_mode", "RUNTIME_AUTH_UNAVAILABLE"),
        ("unknown_field", "FIELD_UNKNOWN"),
        ("symlink", "INPUT_ALIAS"),
    ],
)
def test_malformed_request_exits_2_and_preserves_prior_output(
    tmp_path: Path,
    fabro: FakeFabro,
    capsys: pytest.CaptureFixture[str],
    change: str,
    code: str,
) -> None:
    request = write_request(tmp_path / "work", fabro)
    out = tmp_path / "prior.json"
    out.write_bytes(b"prior complete output\n")
    work = tmp_path / "work"
    if change == "package_byte":
        (work / "package.json").write_bytes((work / "package.json").read_bytes() + b" ")
    elif change == "token_mode":
        os.chmod(work / "token", 0o644)
    elif change == "unknown_field":
        request.write_text(request.read_text() + "unexpected: true\n")
    else:
        (work / "real.json").write_bytes((work / "package.json").read_bytes())
        (work / "package.json").unlink()
        (work / "package.json").symlink_to(work / "real.json")
    status, payload, text = _cli(capsys, "run", "--request", str(request), "--out", str(out))
    assert status == 2
    assert payload is not None and set(payload) == {"code", "pointer", "message"}
    assert payload["code"] == code
    assert TOKEN not in text
    assert out.read_bytes() == b"prior complete output\n"
    assert fabro.posts("/api/v1/runs") == 0


def test_output_into_ledger_or_protected_root_is_refused(
    tmp_path: Path, fabro: FakeFabro, capsys: pytest.CaptureFixture[str]
) -> None:
    request = write_request(tmp_path / "work", fabro)
    for target in (tmp_path / "work/ledger/copy.json", tmp_path / "work/protected/b.json"):
        status, payload, _ = _cli(
            capsys, "register", "--request", str(request), "--out", str(target)
        )
        assert status == 2 and payload is not None
        assert payload["code"] == "OUTPUT_PROTECTED"


def test_status_waiting_without_subject_is_non_success_snapshot(
    tmp_path: Path, fabro: FakeFabro, capsys: pytest.CaptureFixture[str]
) -> None:
    fabro.start_outcome = "blocked"
    request = write_request(tmp_path / "work", fabro)
    assert _cli(capsys, "run", "--request", str(request), "--out", str(tmp_path / "b.json"))[0] == 0
    status, payload, _ = _cli(
        capsys, "status", "--request", str(request), "--out", str(tmp_path / "s.json")
    )
    assert status == 1 and payload is not None
    assert payload["native_status"] == "blocked"
    assert "QUESTION_SUBJECT_UNKNOWN" in payload["reason_codes"]
    assert payload["next_action"] == "none"
    snapshot = read_json(tmp_path / "s.json")
    assert snapshot["gate_handoff"] is None
    assert snapshot["questions"] == [{"id": "review#1", "stage": "review@1"}]


def test_resume_blocks_terminal_drift_and_unavailable_capability(
    tmp_path: Path, fabro: FakeFabro, capsys: pytest.CaptureFixture[str]
) -> None:
    request = write_request(tmp_path / "work", fabro, baseline_now=baseline())
    assert _cli(capsys, "run", "--request", str(request), "--out", str(tmp_path / "b.json"))[0] == 0
    starts = fabro.posts("/start")
    status, payload, _ = _cli(
        capsys, "resume", "--request", str(request), "--out", str(tmp_path / "r.json")
    )
    assert status == 1 and payload is not None
    assert payload["decision"] == "refuse_terminal"
    assert fabro.posts("/start") == starts
    fabro.start_outcome = "terminated"
    effects = [{"stage": "hold@1", "effect_id": "effect-hold", "state": "confirmed_absent"}]
    second = write_request(tmp_path / "second", fabro, baseline_now=baseline(), effects=effects)
    assert _cli(capsys, "run", "--request", str(second), "--out", str(tmp_path / "b2.json"))[0] == 0
    starts = fabro.posts("/start")
    status, payload, _ = _cli(
        capsys, "resume", "--request", str(second), "--out", str(tmp_path / "r2.json")
    )
    assert status == 1 and payload is not None
    assert payload["decision"] == "block_unknown"
    assert payload["reason_codes"] == ["RUNTIME_CAPABILITY_UNAVAILABLE"]
    assert payload["native_action"] == "not_sent"
    drift = write_request(
        tmp_path / "second",
        fabro,
        baseline_now=baseline(policy_digest="f" * 64),
        effects=effects,
    )
    status, payload, _ = _cli(
        capsys, "resume", "--request", str(drift), "--out", str(tmp_path / "r3.json")
    )
    assert status == 1 and payload is not None
    assert payload["decision"] == "block_drift"
    assert payload["changed_bindings"] == ["baseline:policy_digest"]
    assert fabro.posts("/start") == starts


def test_admitted_resume_counts_attempt_and_reports_native_conflict(
    tmp_path: Path, fabro: FakeFabro, capsys: pytest.CaptureFixture[str]
) -> None:
    fabro.start_outcome = "terminated"
    effects = [{"stage": "hold@1", "effect_id": "effect-hold", "state": "confirmed_absent"}]
    request = write_request(
        tmp_path / "work",
        fabro,
        baseline_now=baseline(),
        effects=effects,
        demonstrated=sorted(CAPABILITIES),
    )
    assert _cli(capsys, "run", "--request", str(request), "--out", str(tmp_path / "b.json"))[0] == 0
    status, payload, _ = _cli(
        capsys, "resume", "--request", str(request), "--out", str(tmp_path / "r.json")
    )
    assert status == 0 and payload is not None
    assert (payload["decision"], payload["native_action"]) == ("admit", "accepted")
    selected = load_request(request)
    assert IntentLedger(selected.ledger_root).read("intent-006")["resume_attempts"] == 1
    status, payload, _ = _cli(
        capsys, "status", "--request", str(request), "--out", str(tmp_path / "s.json")
    )
    assert status == 1 and payload is not None
    assert payload["reason_codes"] == ["NATIVE_STATE_CONFLICT"]
    status, payload, _ = _cli(
        capsys, "resume", "--request", str(request), "--out", str(tmp_path / "r.json")
    )
    assert status == 1 and payload is not None and payload["decision"] == "block_unknown"


def test_cancel_reports_confirmed_terminal_only(
    tmp_path: Path, fabro: FakeFabro, capsys: pytest.CaptureFixture[str]
) -> None:
    fabro.start_outcome = "blocked"
    fabro.cancel_after_polls = 2
    request = write_request(tmp_path / "work", fabro)
    assert _cli(capsys, "run", "--request", str(request), "--out", str(tmp_path / "b.json"))[0] == 0
    status, payload, _ = _cli(
        capsys, "cancel", "--request", str(request), "--out", str(tmp_path / "c.json")
    )
    assert status == 0 and payload is not None
    assert payload["cancellation"] == "confirmed"
    assert payload["native_status"] == "failed" and payload["native_reason"] == "cancelled"
    status, payload, _ = _cli(
        capsys, "cancel", "--request", str(request), "--out", str(tmp_path / "c.json")
    )
    assert status == 2 and payload is not None and payload["code"] == "RUNTIME_RESPONSE"


def test_verify_incomplete_or_corrupt_exports(
    tmp_path: Path, fabro: FakeFabro, capsys: pytest.CaptureFixture[str]
) -> None:
    request = write_request(tmp_path / "work", fabro)
    assert _cli(capsys, "run", "--request", str(request), "--out", str(tmp_path / "b.json"))[0] == 0
    fabro.missing_blobs.update(fabro.blobs)
    export = tmp_path / "e.json"
    status, payload, _ = _cli(capsys, "export", "--request", str(request), "--out", str(export))
    assert status == 1 and payload is not None and payload["completeness"] == "incomplete"
    status, payload, _ = _cli(capsys, "verify", "--export", str(export))
    assert status == 1 and payload is not None
    assert payload["reproduced"] is True and payload["completeness"] == "incomplete"
    export.write_text(export.read_text().replace('"succeeded"', '"failed"', 1))
    status, payload, _ = _cli(capsys, "verify", "--export", str(export))
    assert status == 2 and payload is not None and payload["code"] == "SEMANTIC_DIGEST"


def test_quickstart_schema_required_fields_match_runtime_records() -> None:
    from score_sw_fabric.runtime.models import BINDING_FIELDS, EXPORT_FIELDS, INTENT_FIELDS
    from score_sw_fabric.runtime.request import REQUEST_FIELDS
    from score_sw_fabric.runtime.resume import DECISION_FIELDS

    for name, fields in (
        ("runtime-binding", BINDING_FIELDS),
        ("runtime-export", EXPORT_FIELDS),
        ("runtime-intent", INTENT_FIELDS),
        ("runtime-request", REQUEST_FIELDS),
        ("runtime-resume-decision", DECISION_FIELDS),
    ):
        schema = json.loads((ROOT / f"schemas/{name}.schema.json").read_text())
        assert set(schema["required"]) == fields | {"schema_version", "kind"}, name
    profile = json.loads((ROOT / "schemas/runtime-profile.schema.json").read_text())
    assert set(profile["$defs"]["capabilities"]["items"]["enum"]) == CAPABILITIES
