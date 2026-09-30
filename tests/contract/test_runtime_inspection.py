"""Native status and event identity remain explicit and bounded."""

from __future__ import annotations

import json
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.runtime.client import FabroClient, Transport
from score_sw_fabric.runtime.inspect import inspect_run, lifecycle_conflict
from tests.runtime_support import FakeFabro, linear_sources

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


def _lifecycle(seq: int, status: dict[str, Any] | None, transition: str) -> dict[str, Any]:
    record: dict[str, Any] = {"kind": "run.lifecycle", "transition": transition}
    if status is not None:
        record["status"] = status
    return {"id": f"p{seq}", "stream_seq": seq, "kind": "platform", "item": {"record": record}}


FAILED_TERMINATED = {"kind": "failed", "reason": "terminated"}
FAILED_ERROR = {"kind": "failed", "reason": "workflow_error"}
SUCCEEDED = {"kind": "succeeded", "reason": "completed"}
RUNNING = {"kind": "running"}


@pytest.mark.parametrize(
    ("summary", "records", "conflict"),
    [
        # Observed: accepted resume on a terminated run appended runnable; summary stayed failed.
        (
            FAILED_TERMINATED,
            [
                (RUNNING, "running"),
                (FAILED_TERMINATED, "failed"),
                (None, "start_requested"),
                ({"kind": "runnable"}, "runnable"),
            ],
            True,
        ),
        # Observed: crash continuation race recorded failed twice, then succeeded.
        (
            FAILED_ERROR,
            [(FAILED_ERROR, "failed"), (FAILED_ERROR, "failed"), (SUCCEEDED, "succeeded")],
            True,
        ),
        (RUNNING, [(RUNNING, "running"), (SUCCEEDED, "succeeded")], True),
        (SUCCEEDED, [(RUNNING, "running"), (SUCCEEDED, "succeeded")], False),
        # Native waiting has no lifecycle record; blocked after running is consistent.
        (
            {"kind": "blocked", "blocked_reason": "human_input_required"},
            [(RUNNING, "running")],
            False,
        ),
        (
            {"kind": "failed", "reason": "cancelled"},
            [
                (RUNNING, "running"),
                (None, "cancel_requested"),
                (
                    {"kind": "failed", "reason": "cancelled"},
                    "failed",
                ),
            ],
            False,
        ),
    ],
)
def test_summary_and_lifecycle_record_disagreement_is_conflict(
    summary: dict[str, Any], records: list[tuple[dict[str, Any] | None, str]], conflict: bool
) -> None:
    events = [_lifecycle(index, status, name) for index, (status, name) in enumerate(records, 1)]
    assert lifecycle_conflict(summary, events) is conflict
    pages = [{"data": events, "meta": {"has_more": False}, "event_contract_version": 3}]

    def transport(
        method: str, url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        if "/events?" in url:
            page: dict[str, Any] = pages[0]
        elif url.endswith("/timeline"):
            page = {"entries": []}
        elif url.endswith("/questions"):
            page = {"data": [], "meta": {"has_more": False}}
        else:
            page = {"id": RUN, "lifecycle": {"status": summary}}
        return 200, json.dumps(page).encode()

    inspection = inspect_run(_client(transport), RUN)
    assert ("NATIVE_STATE_CONFLICT" in inspection["reason_codes"]) is conflict
    assert inspection["complete"] is not conflict
    assert inspection["native_status"] == summary["kind"]


def test_stage_list_and_malformed_timeline_are_explicit() -> None:
    fabro = FakeFabro(start_outcome="terminated")
    client = fabro.client()
    package, compiler_profile = linear_sources()
    version = client.register_package(package, compiler_profile)
    status, body = client.request(
        "run_create",
        "POST",
        "/api/v1/runs",
        {
            "workflow_version_id": version,
            "target": {"kind": "folder", "path": "/tmp/unused"},
            "environment_id": "local",
            "args": {"labels": {}, "auto_approve": False, "dry_run": False},
        },
    )
    run_id = json.loads(body)["id"]
    client.request("run_start", "POST", f"/api/v1/runs/{run_id}/start", {})
    inspection = inspect_run(client, run_id)
    assert inspection["stages"] == [
        {"id": "start@1", "status": "succeeded"},
        {"id": "hold@1", "status": "running"},
    ]
    fabro.runs[run_id].stages.append({"id": "../escape", "status": "running"})
    fabro.runs[run_id].timeline = "not-a-list"  # type: ignore[assignment]
    broken = inspect_run(client, run_id)
    assert broken["stages"] is None
    assert broken["checkpoints"] == []
    assert {"CHECKPOINT_INCOMPLETE", "STAGE_INCOMPLETE"} <= set(broken["reason_codes"])
    assert broken["complete"] is False
