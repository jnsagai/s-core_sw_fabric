"""Cancellation is terminal only when native state confirms it and stays terminal."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.inspect import inspect_run
from score_sw_fabric.runtime.ledger import IntentLedger
from score_sw_fabric.runtime.resume import admit_resume
from tests.runtime_support import FakeFabro, intent, linear_sources, project


def _started(tmp_path: Path, fabro: FakeFabro) -> tuple[Any, IntentLedger, dict[str, Any]]:
    client = fabro.client()
    package, compiler_profile = linear_sources()
    selected = intent(package, client)
    ledger = IntentLedger(tmp_path / "ledger")
    ledger.prepare(
        selected,
        version_id=client.register_package(package, compiler_profile),
        runtime_commit="a" * 40,
        source_package_digest=package["digest"],
        wire_digest=project(package, compiler_profile)["wire_digest"],
    )
    (tmp_path / "target").mkdir()
    client.create_run(
        ledger,
        selected["intent_id"],
        target=tmp_path / "target",
        disposable_root=tmp_path,
        environment_id="local",
        labels={},
    )
    return client, ledger, selected


def test_accepted_cancel_is_pending_until_native_terminal_observation(tmp_path: Path) -> None:
    fabro = FakeFabro(start_outcome="blocked", cancel_after_polls=3)
    client, ledger, selected = _started(tmp_path, fabro)
    run_id = client.start_known_run(ledger, selected["intent_id"])["run_id"]
    pending = client.cancel_run(run_id, polls=2, interval_seconds=0)
    assert pending["request_http_status"] == 202
    assert pending["request_pending_control"] == "cancel"
    assert pending["cancellation"] == "pending"
    assert pending["reason_codes"] == ["CANCEL_PENDING"]
    assert pending["native_status"] == {"kind": "blocked", "blocked_reason": "human_input_required"}
    confirmed = client.cancel_run(run_id, polls=5, interval_seconds=0)
    assert confirmed["cancellation"] == "confirmed"
    assert confirmed["native_status"] == {"kind": "failed", "reason": "cancelled"}
    assert confirmed["engineering_readiness"] == "not_evaluated"


def test_other_terminal_outcome_is_not_reported_as_cancelled(tmp_path: Path) -> None:
    fabro = FakeFabro(
        start_outcome="blocked", cancel_outcome={"kind": "succeeded", "reason": "completed"}
    )
    client, ledger, selected = _started(tmp_path, fabro)
    run_id = client.start_known_run(ledger, selected["intent_id"])["run_id"]
    result = client.cancel_run(run_id, polls=1, interval_seconds=0)
    assert result["cancellation"] == "terminal_other"
    assert result["reason_codes"] == ["CANCEL_NOT_CONFIRMED"]
    with pytest.raises(InputError) as error:
        client.cancel_run(run_id, polls=1, interval_seconds=0)
    assert error.value.code == "RUNTIME_RESPONSE"


def test_confirmed_cancel_refuses_resume_and_known_id_start(tmp_path: Path) -> None:
    fabro = FakeFabro(start_outcome="blocked")
    client, ledger, selected = _started(tmp_path, fabro)
    binding = client.start_known_run(ledger, selected["intent_id"])
    client.cancel_run(binding["run_id"], polls=3, interval_seconds=0)
    inspection = inspect_run(client, binding["run_id"])
    assert inspection["native_status"] == "failed"
    assert inspection["native_reason"] == "cancelled"
    decision = admit_resume(
        binding=binding,
        intent=selected,
        baseline_now=selected["baseline"],
        inspection=inspection,
        evidence=[],
        effects=[],
    )
    assert decision["decision"] == "refuse_terminal"
    assert "CANCELLED_TERMINAL" in decision["reason_codes"]
    starts = fabro.posts("/start")
    with pytest.raises(InputError) as error:
        ledger.begin_start(selected["intent_id"])
    assert error.value.code == "RUN_START_UNCERTAIN"
    assert fabro.posts("/start") == starts


def test_unstarted_known_run_start_is_refused_after_native_cancel(tmp_path: Path) -> None:
    fabro = FakeFabro()
    client, ledger, selected = _started(tmp_path, fabro)
    run_id = ledger.read(selected["intent_id"])["run_id"]
    assert client.cancel_run(run_id, polls=3, interval_seconds=0)["cancellation"] == "confirmed"
    with pytest.raises(InputError) as error:
        client.start_known_run(ledger, selected["intent_id"])
    assert error.value.code == "RUN_START_UNCERTAIN"
    assert fabro.posts("/start") == 0
    assert ledger.read(selected["intent_id"])["start_state"] == "reconciliation_required"


def test_cancel_route_requires_demonstrated_capability_and_valid_run(tmp_path: Path) -> None:
    fabro = FakeFabro()
    client = fabro.client(demonstrated=["run_inspect"])
    with pytest.raises(InputError) as error:
        client.cancel_run("run-1", polls=1, interval_seconds=0)
    assert error.value.code == "RUNTIME_CAPABILITY_UNAVAILABLE"
    with pytest.raises(InputError):
        fabro.client().cancel_run("../run", polls=1, interval_seconds=0)
    with pytest.raises(InputError):
        fabro.client().cancel_run("run-1", polls=0, interval_seconds=0)
    assert fabro.calls == []
