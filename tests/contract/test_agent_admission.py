"""007 model capability, fallback and budget admission on the captured catalogue (AC007-11–13)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from score_sw_fabric.agents.admission import admit, estimate_cost, load_catalogue
from score_sw_fabric.process_source.reader import InputError
from tests.agent_support import CATALOGUE, DEVELOPER, MODELS, admit_request, entry

PAGES = [CATALOGUE / "models-offset-0.json", CATALOGUE / "models-offset-100.json"]


def profiles(mutate: Any = None) -> dict[str, Any]:
    value: dict[str, Any] = yaml.safe_load(MODELS.read_text())
    if mutate is not None:
        mutate(value)
    return value


def role(**changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = yaml.safe_load(DEVELOPER.read_text())
    value.update(changes)
    return value


def codes(record: dict[str, Any]) -> set[str]:
    return {item["code"] for item in record["reasons"]}


def test_captured_catalogue_is_complete_and_unique() -> None:
    catalogue = load_catalogue([page.read_bytes() for page in PAGES])
    assert len(catalogue) == 129
    flash = catalogue[("deepseek", "deepseek-v4-flash")]
    assert flash["reasoning_effort"] == ["low", "medium", "high", "xhigh", "max"]
    assert flash["configured"] is False
    assert catalogue[("vercel", "jev")]["context_window"] is None
    assert not any(row["configured"] for row in catalogue.values())
    with pytest.raises(InputError) as error:
        load_catalogue([PAGES[0].read_bytes()])
    assert error.value.code == "CATALOGUE_INCOMPLETE"
    with pytest.raises(InputError) as error:
        load_catalogue([PAGES[0].read_bytes(), PAGES[0].read_bytes(), PAGES[1].read_bytes()])
    assert error.value.code == "CATALOGUE_FORMAT"


def test_estimate_uses_catalogue_prices_and_rounds_up() -> None:
    offering = {"input_cost_per_mtok": "0.14", "output_cost_per_mtok": "0.28"}
    assert estimate_cost(offering, 120_000, 32_000) == 25_760
    assert estimate_cost(offering, 1, 1) == 1
    assert estimate_cost({"input_cost_per_mtok": None, "output_cost_per_mtok": "1"}, 1, 1) is None


def test_admissible_call_never_authorizes_a_live_call(tmp_path: Path) -> None:
    status, record, inputs, _ = admit(admit_request(tmp_path))
    assert status == 0 and record["decision"] == "admissible"
    assert record["call_authorized"] is False and record["provider_configured"] is False
    assert record["estimate"]["cost_microusd"] == 100_000 * 0.14 + 32_000 * 0.28
    assert record["remaining"]["calls"] == 6
    assert record["engineering_readiness"] == "not_evaluated"
    assert len(inputs) == 6


def _set(profile_id: str, **changes: Any) -> Any:
    def mutate(value: dict[str, Any]) -> None:
        for item in value["profiles"]:
            if item["id"] == profile_id:
                item.update(changes)

    return mutate


FLASH = "model.routine.deepseek-v4-flash"


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (_set(FLASH, model="deepseek-flash"), "MODEL_ALIAS"),
        (_set(FLASH, model="deepseek-v9"), "MODEL_UNKNOWN"),
        (_set(FLASH, reasoning_effort="ultra"), "REASONING_UNSUPPORTED"),
        (_set(FLASH, max_output_tokens=400_000, max_context_tokens=1_000_000), "OUTPUT_LIMIT"),
        (_set(FLASH, max_context_tokens=2_000_000), "CONTEXT_LIMIT"),
        (_set(FLASH, max_context_tokens=120_000), "CONTEXT_LIMIT"),
        (_set(FLASH, provider="vercel", model="jev"), "LIMIT_UNKNOWN"),
        (_set(FLASH, provider="vercel", model="jev"), "TOOLS_UNSUPPORTED"),
        (_set(FLASH, data_destination="provider.elsewhere"), "DESTINATION_NOT_ALLOWED"),
    ],
)
def test_capability_faults_refuse(tmp_path: Path, mutate: Any, code: str) -> None:
    status, record, _, _ = admit(admit_request(tmp_path, profiles=profiles(mutate)))
    assert status == 1 and record["decision"] == "refused"
    assert code in codes(record)
    assert record["call_authorized"] is False


def test_named_reasoning_on_catalogue_without_levels_refuses(tmp_path: Path) -> None:
    sol = "model.supervision.gpt-5.6-sol"
    value = profiles(_set(sol, reasoning_effort="high"))
    selected = role(model_profile=sol, data_destinations=["provider.openai"])
    call = {"call_id": "c", "attempt": "initial", "profile": sol, "estimated_input_tokens": 1000}
    status, record, _, _ = admit(admit_request(tmp_path, profiles=value, role=selected, call=call))
    assert status == 1 and "REASONING_UNSUPPORTED" in codes(record)


def _fallback(profile: str = "model.review.deepseek-v4-pro") -> dict[str, Any]:
    return {
        "call_id": "fb",
        "attempt": "fallback",
        "profile": profile,
        "estimated_input_tokens": 1000,
    }


def test_explicit_allowlisted_fallback_is_admissible(tmp_path: Path) -> None:
    status, record, _, _ = admit(admit_request(tmp_path, call=_fallback()))
    assert status == 0 and record["profile"]["id"] == "model.review.deepseek-v4-pro"


@pytest.mark.parametrize(
    ("mutate", "call_profile", "code"),
    [
        (lambda value: value["profiles"][0].update(fallbacks=[]), None, "FALLBACK_NOT_ALLOWLISTED"),
        (
            lambda value: value["profiles"][0]["fallbacks"][0].update(allow_higher_price=False),
            None,
            "FALLBACK_PRICE_ESCALATION",
        ),
        (
            lambda value: value["profiles"][1].update(data_destination="provider.other"),
            None,
            "FALLBACK_DESTINATION",
        ),
        (
            lambda value: value["profiles"][1].update(reasoning_effort=None),
            None,
            "FALLBACK_INCOMPATIBLE",
        ),
        (None, "model.supervision.gpt-5.6-sol", "FALLBACK_NOT_ALLOWLISTED"),
    ],
)
def test_fallback_faults_refuse(
    tmp_path: Path, mutate: Any, call_profile: str | None, code: str
) -> None:
    value = profiles(mutate)
    call = _fallback(call_profile) if call_profile else _fallback()
    status, record, _, _ = admit(admit_request(tmp_path, profiles=value, call=call))
    assert status == 1 and code in codes(record)


def test_non_fallback_call_must_use_role_profile(tmp_path: Path) -> None:
    call = {**_fallback(), "attempt": "initial"}
    status, record, _, _ = admit(admit_request(tmp_path, call=call))
    assert status == 1 and "PROFILE_NOT_ROLE" in codes(record)


@pytest.mark.parametrize(
    ("entries", "attempt", "code"),
    [
        ([entry("a", cost_microusd=495_000)], "initial", "BUDGET_EXHAUSTED"),
        ([entry("a", input_tokens=1_999_500)], "initial", "BUDGET_EXHAUSTED"),
        ([entry("a", wall_seconds=3_000)], "initial", "BUDGET_EXHAUSTED"),
        ([entry("a", cost_microusd=None)], "initial", "USAGE_UNKNOWN"),
        (
            [
                entry(
                    "a",
                    input_tokens=None,
                    output_tokens=None,
                    cost_microusd=None,
                    wall_seconds=None,
                )
            ],
            "initial",
            "USAGE_UNKNOWN",
        ),
        ([entry(f"c{index}") for index in range(6)], "initial", "CALL_LIMIT"),
        ([entry("a"), entry("b", "retry")], "retry", "RETRY_LIMIT"),
        (
            [entry("a"), entry("b", "correction_visit"), entry("c", "correction_visit")],
            "correction_visit",
            "VISIT_LIMIT",
        ),
    ],
)
def test_budget_faults_refuse(
    tmp_path: Path, entries: list[dict[str, Any]], attempt: str, code: str
) -> None:
    call = {"call_id": "new", "attempt": attempt, "profile": FLASH, "estimated_input_tokens": 1000}
    status, record, _, _ = admit(admit_request(tmp_path, entries=entries, call=call))
    assert status == 1 and code in codes(record)
    if code == "USAGE_UNKNOWN":
        assert None in record["used"].values()


def test_known_usage_within_limits_is_admissible(tmp_path: Path) -> None:
    entries = [entry("a"), entry("b", "retry"), entry("c", "correction_visit")]
    call = {
        "call_id": "new",
        "attempt": "correction_visit",
        "profile": FLASH,
        "estimated_input_tokens": 1000,
    }
    status, record, _, _ = admit(admit_request(tmp_path, entries=entries, call=call))
    assert status == 0, record["reasons"]
    assert record["used"]["cost_microusd"] == 3000 and record["used"]["calls"] == 3


@pytest.mark.parametrize(
    ("kind", "code"),
    [
        ("live", "LIVE_CALLS_UNAUTHORIZED"),
        ("pages", "CATALOGUE_MISMATCH"),
        ("duplicate_call", "DUPLICATE_ID"),
        ("usage_claim", "USAGE_FORMAT"),
        ("ledger_role", "LEDGER_MISMATCH"),
        ("forbidden_role", "CREDENTIAL_FORBIDDEN"),
    ],
)
def test_admission_input_refusals(tmp_path: Path, kind: str, code: str) -> None:
    kwargs: dict[str, Any] = {}
    if kind == "live":
        kwargs["profiles"] = profiles(lambda value: value.update(live_calls="enabled"))
    elif kind == "pages":
        kwargs["profiles"] = profiles(
            lambda value: value["catalogue"].update(pages_sha256=["0" * 64])
        )
    elif kind == "duplicate_call":
        kwargs["entries"] = [entry("call.new")]
    elif kind == "usage_claim":
        bad = copy.deepcopy(entry("a"))
        bad["usage_origin"] = "unknown"
        kwargs["entries"] = [bad]
    elif kind == "forbidden_role":
        kwargs["role"] = role(credentials=["approval_key"])
    path = admit_request(tmp_path, **kwargs)
    if kind == "ledger_role":
        ledger = tmp_path / "ledger.yaml"
        data = yaml.safe_load(ledger.read_text())
        data["role_id"] = "role.other"
        from tests.agent_support import write_yaml

        request = yaml.safe_load(path.read_text())
        request["ledger"] = write_yaml(ledger, data)
        write_yaml(path, request)
    with pytest.raises(InputError) as error:
        admit(path)
    assert error.value.code == code
