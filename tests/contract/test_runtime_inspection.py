"""Native status and event identity remain explicit and bounded."""

from __future__ import annotations

import json
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.runtime.client import FabroClient, Transport
from score_sw_fabric.runtime.inspect import inspect_run

RUN = "native-run"
COMMIT = "a" * 40
TOKEN = "fabro_dev_" + "b" * 64


def _client(transport: Transport) -> FabroClient:
    profile = seal(
        {
            "schema_version": 1,
            "kind": "runtime_profile",
            "id": "inspection-contract",
            "source_commit": COMMIT,
            "executable_sha256": "c" * 64,
            "source_api_sha256": "d" * 64,
            "base_url": "http://127.0.0.1:43286",
            "auth_mode": "dev_token_disposable",
            "declared_capabilities": [
                "event_read",
                "question_read",
                "run_inspect",
                "timeline_read",
            ],
            "demonstrated_capabilities": [
                "event_read",
                "question_read",
                "run_inspect",
                "timeline_read",
            ],
            "limits": {"timeout_seconds": 5, "response_bytes": 4096},
            "status": "candidate_only",
        }
    )
    return FabroClient(
        profile, expected_commit=COMMIT, credential_provider=lambda: TOKEN, transport=transport
    )


def _item(seq: int, *, identifier: str | None = None) -> dict[str, Any]:
    return {"id": identifier or str(seq), "stream_seq": seq, "kind": "platform", "item": {}}


def _transport(pages: list[dict[str, Any]], *, kind: str = "blocked") -> Transport:
    calls = 0

    def transport(
        method: str, url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        nonlocal calls
        assert method == "GET"
        if url.endswith("/events?after=0&limit=1000"):
            page = pages[0]
        elif "/events?after=" in url:
            calls += 1
            page = pages[calls]
        elif url.endswith("/timeline"):
            page = {"entries": [{"ordinal": 1, "stage": "start@1"}]}
        elif url.endswith("/questions"):
            page = {"data": [{"id": "q-1", "stage": "review@1"}], "meta": {"has_more": False}}
        else:
            page = {
                "id": RUN,
                "lifecycle": {
                    "status": {"kind": kind, "blocked_reason": "human_input_required"},
                    "pending_control": "cancel" if kind == "running" else None,
                },
            }
        return 200, json.dumps(page).encode()

    return transport


def test_paginated_events_and_waiting_question_are_preserved() -> None:
    pages = [
        {"data": [_item(1), _item(2)], "meta": {"has_more": True}, "event_contract_version": 3},
        {"data": [_item(3)], "meta": {"has_more": False}, "event_contract_version": 3},
    ]
    inspection = inspect_run(_client(_transport(pages)), RUN)
    assert inspection["complete"] is True
    assert inspection["native_status"] == "blocked"
    assert inspection["native_blocked_reason"] == "human_input_required"
    assert inspection["event_position"] == 3
    assert [item["id"] for item in inspection["events"]] == ["1", "2", "3"]
    assert inspection["questions"] == [{"id": "q-1", "stage": "review@1"}]
    assert inspection["engineering_readiness"] == "not_evaluated"


def test_identical_event_overlap_is_deduplicated_by_native_identity() -> None:
    pages = [
        {"data": [_item(1), _item(2)], "meta": {"has_more": True}, "event_contract_version": 3},
        {"data": [_item(2), _item(3)], "meta": {"has_more": False}, "event_contract_version": 3},
    ]
    inspection = inspect_run(_client(_transport(pages)), RUN)
    assert inspection["complete"] is True
    assert [item["stream_seq"] for item in inspection["events"]] == [1, 2, 3]


def test_pending_native_cancellation_is_not_terminal() -> None:
    pages = [{"data": [_item(1)], "meta": {"has_more": False}, "event_contract_version": 3}]
    inspection = inspect_run(_client(_transport(pages, kind="running")), RUN)
    assert inspection["native_status"] == "running"
    assert inspection["native_summary"]["lifecycle"]["pending_control"] == "cancel"
    assert inspection["engineering_readiness"] == "not_evaluated"


@pytest.mark.parametrize(
    "pages",
    [
        [{"data": [_item(1), _item(3)], "meta": {"has_more": False}, "event_contract_version": 3}],
        [
            {"data": [_item(1)], "meta": {"has_more": True}, "event_contract_version": 3},
            {
                "data": [_item(1, identifier="changed"), _item(2)],
                "meta": {"has_more": False},
                "event_contract_version": 3,
            },
        ],
        [
            {"data": [_item(1)], "meta": {"has_more": True}, "event_contract_version": 3},
            {"data": [], "meta": {"has_more": True}, "event_contract_version": 3},
        ],
    ],
)
def test_gap_changed_overlap_or_stalled_page_is_incomplete(pages: list[dict[str, Any]]) -> None:
    inspection = inspect_run(_client(_transport(pages)), RUN)
    assert inspection["complete"] is False
    assert inspection["reason_codes"] == ["EVENT_GAP"]


def test_unknown_native_status_stays_unknown() -> None:
    pages = [{"data": [], "meta": {"has_more": False}, "event_contract_version": 3}]
    inspection = inspect_run(_client(_transport(pages, kind="new_native_kind")), RUN)
    assert inspection["native_status"] == "unknown"
    assert inspection["reason_codes"] == ["NATIVE_STATE_UNKNOWN"]
