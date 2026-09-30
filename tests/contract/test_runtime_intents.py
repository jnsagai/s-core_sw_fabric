"""A lost run-create response cannot trigger a second native create."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.client import FabroClient, Transport
from score_sw_fabric.runtime.ledger import IntentLedger

SHA = "a" * 64
COMMIT = "b" * 40
TOKEN = "fabro_dev_" + "c" * 64


def _intent(identifier: str = "intent-006") -> dict[str, Any]:
    return seal(
        {
            "schema_version": 1,
            "kind": "runtime_intent",
            "intent_id": identifier,
            "package_ref": {"path": "package.json", "sha256": SHA, "semantic_digest": SHA},
            "runtime_profile_ref": {
                "path": "profile.json",
                "sha256": SHA,
                "semantic_digest": SHA,
            },
            "baseline": {
                "source_digest": SHA,
                "process_digest": SHA,
                "policy_digest": SHA,
                "tool_digest": SHA,
                "subject_digest": SHA,
                "evidence_digests": [],
            },
            "start_args": {"target_id": "local-006", "labels": {}},
            "limits": {
                "timeout_seconds": 30,
                "event_pages": 10,
                "output_bytes": 1024,
                "attempts": 2,
            },
        }
    )


def _prepare(ledger: IntentLedger, intent: dict[str, Any] | None = None) -> dict[str, Any]:
    return ledger.prepare(
        _intent() if intent is None else intent,
        version_id="wv-006",
        runtime_commit=COMMIT,
        source_package_digest=SHA,
        wire_digest=SHA,
    )


def test_repeat_prepare_reuses_exact_intent(tmp_path: Path) -> None:
    ledger = IntentLedger(tmp_path / "ledger")
    first = _prepare(ledger)
    assert first["creation_state"] == "prepared"
    assert _prepare(ledger) == first
    assert ledger.read("intent-006") == first
    assert len(list((tmp_path / "ledger").glob("*.json"))) == 1


def test_changed_intent_cannot_reuse_version_or_run(tmp_path: Path) -> None:
    ledger = IntentLedger(tmp_path / "ledger")
    first = _prepare(ledger)
    changed = _intent()
    changed["baseline"]["policy_digest"] = "c" * 64
    with pytest.raises(InputError) as error:
        _prepare(ledger, seal(changed))
    assert error.value.code == "INTENT_CONFLICT"
    assert ledger.read("intent-006") == first


def test_lost_create_response_stops_automatic_retry(tmp_path: Path) -> None:
    ledger = IntentLedger(tmp_path / "ledger")
    _prepare(ledger)
    pending = ledger.begin_create("intent-006")
    assert pending["creation_state"] == "create_in_flight"
    assert pending["run_id"] is None
    uncertain = ledger.mark_create_uncertain("intent-006")
    assert uncertain["creation_state"] == "reconciliation_required"
    assert uncertain["reason_codes"] == ["RUN_CREATE_UNCERTAIN"]
    with pytest.raises(InputError) as error:
        ledger.begin_create("intent-006")
    assert error.value.code == "RUN_CREATE_UNCERTAIN"
    with pytest.raises(InputError):
        ledger.record_create_response("intent-006", "late-id")
    assert ledger.read("intent-006") == uncertain


def test_known_create_response_persists_native_run_id(tmp_path: Path) -> None:
    ledger = IntentLedger(tmp_path / "ledger")
    _prepare(ledger)
    ledger.begin_create("intent-006")
    known = ledger.record_create_response("intent-006", "01234567-89ab-cdef-0123-456789abcdef")
    assert known["creation_state"] == "run_known"
    assert ledger.read("intent-006")["run_id"] == known["run_id"]
    with pytest.raises(InputError):
        ledger.begin_create("intent-006")


def test_two_local_callers_cannot_both_begin_create(tmp_path: Path) -> None:
    ledger = IntentLedger(tmp_path / "ledger")
    _prepare(ledger)

    def attempt() -> str:
        try:
            return ledger.begin_create("intent-006")["creation_state"]
        except InputError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == ["RUN_CREATE_UNCERTAIN", "create_in_flight"]


def test_linked_or_conflicting_ledger_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(InputError) as error:
        IntentLedger(alias)
    assert error.value.code == "OUTPUT_ALIAS"
    ledger = IntentLedger(real)
    _prepare(ledger)
    with pytest.raises(InputError) as error:
        ledger.prepare(
            _intent(),
            version_id="different-version",
            runtime_commit=COMMIT,
            source_package_digest=SHA,
            wire_digest=SHA,
        )
    assert error.value.code == "INTENT_CONFLICT"


def _client(transport: Transport) -> FabroClient:
    profile = seal(
        {
            "schema_version": 1,
            "kind": "runtime_profile",
            "id": "disposable-contract",
            "source_commit": COMMIT,
            "executable_sha256": SHA,
            "source_api_sha256": SHA,
            "base_url": "http://127.0.0.1:43286",
            "auth_mode": "dev_token_disposable",
            "declared_capabilities": ["run_create", "run_inspect", "run_start"],
            "demonstrated_capabilities": ["run_create", "run_inspect", "run_start"],
            "limits": {"timeout_seconds": 5, "response_bytes": 4096},
            "status": "candidate_only",
        }
    )
    return FabroClient(
        profile, expected_commit=COMMIT, credential_provider=lambda: TOKEN, transport=transport
    )


def test_native_create_lost_response_blocks_duplicate_request(tmp_path: Path) -> None:
    calls = 0

    def transport(
        method: str, _url: str, body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        nonlocal calls
        assert method == "POST"
        assert body is not None
        payload = json.loads(body)
        assert payload["args"]["auto_approve"] is False
        assert payload["args"]["labels"]["score_intent"] == "intent-006"
        calls += 1
        raise OSError("response lost after server accepted create")

    ledger = IntentLedger(tmp_path / "ledger")
    _prepare(ledger)
    target = tmp_path / "target"
    target.mkdir()
    client = _client(transport)
    with pytest.raises(InputError) as error:
        client.create_run(
            ledger,
            "intent-006",
            target=target,
            disposable_root=tmp_path,
            environment_id="local",
            labels={},
        )
    assert error.value.code == "RUNTIME_UNAVAILABLE"
    assert ledger.read("intent-006")["creation_state"] == "reconciliation_required"
    with pytest.raises(InputError) as error:
        client.create_run(
            ledger,
            "intent-006",
            target=target,
            disposable_root=tmp_path,
            environment_id="local",
            labels={},
        )
    assert error.value.code == "RUN_CREATE_UNCERTAIN"
    assert calls == 1


def test_known_run_is_inspected_before_start_and_not_restarted(tmp_path: Path) -> None:
    calls: list[str] = []

    def transport(
        method: str, url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        calls.append(method + " " + url.rsplit("/", 1)[-1])
        if method == "GET":
            return 200, b'{"id":"native-run","lifecycle":{"status":{"kind":"submitted"}}}'
        return 200, b'{"id":"native-run","lifecycle":{"status":{"kind":"runnable"}}}'

    ledger = IntentLedger(tmp_path / "ledger")
    _prepare(ledger)
    ledger.begin_create("intent-006")
    ledger.record_create_response("intent-006", "native-run")
    client = _client(transport)
    binding = client.start_known_run(ledger, "intent-006")
    assert binding["start_state"] == "started"
    assert client.start_known_run(ledger, "intent-006") == binding
    assert calls == ["GET native-run", "POST start"]


def test_start_refuses_native_state_conflict_without_post(tmp_path: Path) -> None:
    calls: list[str] = []

    def transport(
        method: str, _url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        calls.append(method)
        return 200, b'{"id":"native-run","lifecycle":{"status":{"kind":"running"}}}'

    ledger = IntentLedger(tmp_path / "ledger")
    _prepare(ledger)
    ledger.begin_create("intent-006")
    ledger.record_create_response("intent-006", "native-run")
    with pytest.raises(InputError) as error:
        _client(transport).start_known_run(ledger, "intent-006")
    assert error.value.code == "RUN_START_UNCERTAIN"
    assert ledger.read("intent-006")["start_state"] == "reconciliation_required"
    assert calls == ["GET"]


def test_disposable_target_parent_escape_is_rejected_before_create(tmp_path: Path) -> None:
    calls = 0

    def transport(
        _method: str, _url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        nonlocal calls
        calls += 1
        return 201, b'{"id":"native-run"}'

    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    ledger = IntentLedger(tmp_path / "ledger")
    _prepare(ledger)
    with pytest.raises(InputError) as error:
        _client(transport).create_run(
            ledger,
            "intent-006",
            target=root / ".." / "outside",
            disposable_root=root,
            environment_id="local",
            labels={},
        )
    assert error.value.code == "RUNTIME_TARGET"
    assert ledger.read("intent-006")["creation_state"] == "prepared"
    assert calls == 0
