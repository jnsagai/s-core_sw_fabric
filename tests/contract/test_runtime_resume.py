"""Same-run resume admits only exact, reconciled, non-terminal checkpoint continuation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime import client as runtime_client
from score_sw_fabric.runtime.inspect import inspect_run
from score_sw_fabric.runtime.ledger import IntentLedger
from score_sw_fabric.runtime.resume import admit_resume, validate_decision
from tests.runtime_support import FakeFabro, baseline, intent, linear_sources, project

EVIDENCE = "9" * 64


def _terminated(tmp_path: Path, *, evidence: list[str] | None = None, attempts: int = 2) -> Any:
    """Create a native run interrupted after one checkpoint with one in-flight stage."""
    fabro = FakeFabro(start_outcome="terminated")
    client = fabro.client()
    package, compiler_profile = linear_sources()
    projection = project(package, compiler_profile)
    version_id = client.register_package(package, compiler_profile)
    selected = intent(package, client, evidence=evidence, attempts=attempts)
    ledger = IntentLedger(tmp_path / "ledger")
    ledger.prepare(
        selected,
        version_id=version_id,
        runtime_commit="a" * 40,
        source_package_digest=package["digest"],
        wire_digest=projection["wire_digest"],
    )
    target = tmp_path / "target"
    target.mkdir()
    client.create_run(
        ledger,
        selected["intent_id"],
        target=target,
        disposable_root=tmp_path,
        environment_id="local",
        labels={},
    )
    binding = client.start_known_run(ledger, selected["intent_id"])
    return fabro, client, ledger, selected, binding


def _admit(
    binding: dict[str, Any],
    selected: dict[str, Any],
    inspection: dict[str, Any],
    *,
    now: dict[str, Any] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    effects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return admit_resume(
        binding=binding,
        intent=selected,
        baseline_now=selected["baseline"] if now is None else now,
        inspection=inspection,
        evidence=evidence or [],
        effects=[{"stage": "hold@1", "effect_id": "effect-hold", "state": "confirmed_absent"}]
        if effects is None
        else effects,
    )


def test_unchanged_interrupted_run_is_admitted_only_with_confirmed_absent_effect(
    tmp_path: Path,
) -> None:
    fabro, client, _, selected, binding = _terminated(tmp_path)
    inspection = inspect_run(client, binding["run_id"])
    decision = _admit(binding, selected, inspection)
    assert decision["decision"] == "admit"
    assert decision["in_flight_stages"] == ["hold@1"]
    assert decision["checkpoint"]["stage"] == "start@1"
    assert decision["native_action"] == "not_sent"
    assert decision["production_authority"] == "unavailable"
    assert decision["engineering_readiness"] == "not_evaluated"
    assert validate_decision(decision) == decision
    assert fabro.posts("/start") == 1


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("confirmed_once", "reconciliation_required"),
        ("unknown", "reconciliation_required"),
    ],
)
def test_in_flight_effect_that_may_repeat_requires_reconciliation(
    tmp_path: Path, state: str, expected: str
) -> None:
    _, client, _, selected, binding = _terminated(tmp_path)
    inspection = inspect_run(client, binding["run_id"])
    effects = [{"stage": "hold@1", "effect_id": "effect-hold", "state": state}]
    decision = _admit(binding, selected, inspection, effects=effects)
    assert decision["decision"] == expected
    assert decision["reason_codes"] == ["EFFECT_RECONCILIATION_REQUIRED"]
    assert _admit(binding, selected, inspection, effects=[])["decision"] == expected


@pytest.mark.parametrize(
    "field", ["source_digest", "process_digest", "policy_digest", "tool_digest", "subject_digest"]
)
def test_one_binding_drift_blocks_with_sorted_identity(tmp_path: Path, field: str) -> None:
    _, client, _, selected, binding = _terminated(tmp_path)
    inspection = inspect_run(client, binding["run_id"])
    before = deepcopy(inspection)
    decision = _admit(binding, selected, inspection, now=baseline(**{field: "f" * 64}))
    assert decision["decision"] == "block_drift"
    assert decision["changed_bindings"] == [f"baseline:{field}"]
    assert decision["reason_codes"] == ["RESUME_BASELINE_STALE"]
    assert inspection == before


def test_005_evidence_drift_staleness_and_replay_failure_block(tmp_path: Path) -> None:
    _, client, _, selected, binding = _terminated(tmp_path, evidence=[EVIDENCE])
    inspection = inspect_run(client, binding["run_id"])
    passing = {
        "assessment_digest": EVIDENCE,
        "reproduced": True,
        "outcome": "pass",
        "assurance_domain": "fixture_contract",
    }
    assert _admit(binding, selected, inspection, evidence=[passing])["decision"] == "admit"
    missing = _admit(binding, selected, inspection, evidence=[])
    assert missing["decision"] == "block_drift"
    assert missing["changed_bindings"] == [f"evidence:{EVIDENCE}"]
    for change in ({"outcome": "stale"}, {"reproduced": False}):
        decision = _admit(binding, selected, inspection, evidence=[{**passing, **change}])
        assert decision["decision"] == "block_drift"
        assert "EVIDENCE_NOT_ELIGIBLE" in decision["reason_codes"]
    other = "8" * 64
    swapped = _admit(
        binding,
        selected,
        inspection,
        now=baseline(evidence=[other]),
        evidence=[{**passing, "assessment_digest": other}],
    )
    assert swapped["changed_bindings"] == [f"evidence:{other}", f"evidence:{EVIDENCE}"]


def test_changed_registered_version_or_intent_blocks(tmp_path: Path) -> None:
    _, client, _, selected, binding = _terminated(tmp_path)
    inspection = inspect_run(client, binding["run_id"])
    changed = deepcopy(inspection)
    changed["events"][0]["item"]["record"]["spec"]["workflow_version_id"] = "0" * 64
    decision = _admit(binding, selected, changed)
    assert decision["decision"] == "block_drift"
    assert decision["changed_bindings"] == ["workflow_version"]
    other = seal({**selected, "limits": {**selected["limits"], "attempts": 3}})
    assert "intent" in _admit(binding, other, inspection)["changed_bindings"]


def test_missing_checkpoint_or_unknown_stage_state_blocks(tmp_path: Path) -> None:
    _, client, _, selected, binding = _terminated(tmp_path)
    inspection = inspect_run(client, binding["run_id"])
    missing = {**inspection, "checkpoints": []}
    decision = _admit(binding, selected, missing)
    assert decision["decision"] == "block_unknown"
    assert decision["reason_codes"] == ["CHECKPOINT_MISSING"]
    unknown = _admit(binding, selected, {**inspection, "stages": None})
    assert unknown["decision"] == "reconciliation_required"


@pytest.mark.parametrize(
    ("status", "reason", "code"),
    [
        ("succeeded", "completed", "RESUME_SOURCE_TERMINAL"),
        ("failed", "cancelled", "CANCELLED_TERMINAL"),
        ("failed", "workflow_error", "RESUME_SOURCE_TERMINAL"),
        ("failed", "approval_denied", "RESUME_SOURCE_TERMINAL"),
        ("dead", None, "RESUME_SOURCE_TERMINAL"),
    ],
)
def test_terminal_source_is_refused_before_native_call(
    tmp_path: Path, status: str, reason: str | None, code: str
) -> None:
    _, client, _, selected, binding = _terminated(tmp_path)
    inspection = {**inspect_run(client, binding["run_id"]), "native_status": status}
    inspection["native_reason"] = reason
    decision = _admit(binding, selected, inspection)
    assert decision["decision"] == "refuse_terminal"
    assert code in decision["reason_codes"]


@pytest.mark.parametrize("status", ["running", "blocked", "submitted", "paused"])
def test_active_source_is_not_resumed(tmp_path: Path, status: str) -> None:
    _, client, _, selected, binding = _terminated(tmp_path)
    inspection = {**inspect_run(client, binding["run_id"]), "native_status": status}
    decision = _admit(binding, selected, inspection)
    assert decision["decision"] == "block_unknown"
    assert decision["reason_codes"] == ["RESUME_SOURCE_ACTIVE"]


def test_incomplete_or_conflicting_native_view_is_unknown(tmp_path: Path) -> None:
    _, client, _, selected, binding = _terminated(tmp_path)
    inspection = inspect_run(client, binding["run_id"])
    conflicted = {**inspection, "complete": False, "reason_codes": ["NATIVE_STATE_CONFLICT"]}
    decision = _admit(binding, selected, conflicted)
    assert decision["decision"] == "block_unknown"
    assert {"NATIVE_STATE_CONFLICT", "NATIVE_STATE_UNKNOWN"} <= set(decision["reason_codes"])


def test_finite_attempts_are_counted_before_native_request(tmp_path: Path) -> None:
    _, client, ledger, selected, binding = _terminated(tmp_path, attempts=1)
    counted = ledger.begin_resume(selected["intent_id"], attempt_limit=1)
    assert counted["resume_attempts"] == 1
    with pytest.raises(InputError) as error:
        ledger.begin_resume(selected["intent_id"], attempt_limit=1)
    assert error.value.code == "RESUME_ATTEMPTS_EXHAUSTED"
    inspection = inspect_run(client, binding["run_id"])
    decision = _admit(counted, selected, inspection)
    assert decision["decision"] == "block_unknown"
    assert decision["reason_codes"] == ["RESUME_ATTEMPTS_EXHAUSTED"]


def test_uncertain_prior_resume_requires_reconciliation(tmp_path: Path) -> None:
    _, client, ledger, selected, binding = _terminated(tmp_path)
    uncertain = ledger.mark_resume_uncertain(selected["intent_id"])
    with pytest.raises(InputError) as error:
        ledger.begin_resume(selected["intent_id"], attempt_limit=2)
    assert error.value.code == "EFFECT_RECONCILIATION_REQUIRED"
    decision = _admit(uncertain, selected, inspect_run(client, binding["run_id"]))
    assert decision["decision"] == "reconciliation_required"


def test_native_resume_route_requires_admission_and_never_uses_retry(tmp_path: Path) -> None:
    fabro, client, _, selected, binding = _terminated(tmp_path)
    inspection = inspect_run(client, binding["run_id"])
    blocked = _admit(binding, selected, inspection, effects=[])
    with pytest.raises(InputError) as error:
        client.resume_run(blocked)
    assert error.value.code == "RESUME_NOT_ADMITTED"
    admitted = _admit(binding, selected, inspection)
    with pytest.raises(InputError) as unavailable:
        client.resume_run(admitted)
    assert unavailable.value.code == "RUNTIME_CAPABILITY_UNAVAILABLE"
    assert fabro.posts("/start") == 1
    assert all("/retry" not in route for _, route in runtime_client.ROUTES.values())
    tampered = {**admitted, "run_id": "run-other"}
    with pytest.raises(InputError):
        fabro.client(demonstrated=[*runtime_client.CAPABILITIES]).resume_run(tampered)


def test_accepted_native_resume_that_does_not_continue_is_visible_conflict(
    tmp_path: Path,
) -> None:
    fabro, _, _, selected, binding = _terminated(tmp_path)
    client = fabro.client(demonstrated=sorted(runtime_client.CAPABILITIES))
    admitted = _admit(binding, selected, inspect_run(client, binding["run_id"]))
    observed = client.resume_run(admitted)
    assert observed["lifecycle"]["status"] == {"kind": "failed", "reason": "terminated"}
    after = inspect_run(client, binding["run_id"])
    assert after["complete"] is False
    assert after["reason_codes"] == ["NATIVE_STATE_CONFLICT"]
    assert _admit(binding, selected, after)["decision"] == "block_unknown"
