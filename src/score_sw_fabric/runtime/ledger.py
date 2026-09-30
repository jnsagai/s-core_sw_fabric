"""Durable local intent correlation without becoming Fabro run state."""

from __future__ import annotations

import fcntl
import hashlib
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import digest, nonempty, seal, sha, stable_id
from score_sw_fabric.process_source.reader import InputError, read_json
from score_sw_fabric.runtime.models import publish, validate_binding, validate_intent


class IntentLedger:
    """Serialize local submission intent and stop on uncertain native create."""

    def __init__(self, root: Path) -> None:
        selected = root.absolute()
        if any(path.is_symlink() for path in (selected, *selected.parents)):
            raise InputError("OUTPUT_ALIAS", "Intent ledger root cannot be a symlink")
        self.root = selected

    def _paths(self, intent_id: str) -> tuple[Path, Path]:
        stable_id(intent_id, "/intent_id")
        token = hashlib.sha256(intent_id.encode()).hexdigest()
        return self.root / f"{token}.json", self.root / f"{token}.lock"

    @contextmanager
    def _locked(self, intent_id: str) -> Iterator[Path]:
        record, lock = self._paths(intent_id)
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except OSError as exc:
            raise InputError("OUTPUT_IO", "Cannot open intent lock") from exc
        try:
            if os.fstat(descriptor).st_nlink != 1:
                raise InputError("OUTPUT_ALIAS", "Intent lock is linked")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield record
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        if path.is_symlink() or (path.exists() and path.stat().st_nlink != 1):
            raise InputError("INPUT_ALIAS", "Intent binding is linked")
        if not path.is_file():
            raise InputError("INPUT_UNAVAILABLE", "Intent binding is absent")
        return validate_binding(read_json(path))

    @staticmethod
    def _write(path: Path, value: dict[str, Any]) -> dict[str, Any]:
        sealed = seal(value)
        validate_binding(sealed)
        publish(path, sealed, inputs=[], protected_roots=[])
        return sealed

    def prepare(
        self,
        intent: dict[str, Any],
        *,
        version_id: str,
        runtime_commit: str,
        source_package_digest: str,
        wire_digest: str,
    ) -> dict[str, Any]:
        selected = validate_intent(intent)
        nonempty(version_id, "/version_id", max_length=256)
        if (
            sha(source_package_digest, "/source_package_digest")
            != selected["package_ref"]["semantic_digest"]
        ):
            raise InputError("PACKAGE_DRIFT", "Intent package digest differs from selected package")
        sha(wire_digest, "/wire_digest")
        identifier = selected["intent_id"]
        with self._locked(identifier) as path:
            if path.exists():
                previous = self._read(path)
                if (
                    previous["intent_digest"] != selected["digest"]
                    or previous["version_id"] != version_id
                    or previous["source_package_digest"] != source_package_digest
                    or previous["wire_digest"] != wire_digest
                    or previous["runtime_commit"] != runtime_commit
                ):
                    raise InputError("INTENT_CONFLICT", "Intent ID binds a different request")
                return previous
            return self._write(
                path,
                {
                    "schema_version": 1,
                    "kind": "runtime_binding",
                    "intent_id": identifier,
                    "intent_digest": selected["digest"],
                    "source_package_digest": source_package_digest,
                    "wire_digest": wire_digest,
                    "runtime_commit": runtime_commit,
                    "version_id": version_id,
                    "run_id": None,
                    "creation_state": "prepared",
                    "start_state": "not_requested",
                    "baseline_digest": digest(selected["baseline"], exclude="__none__"),
                    "native_observation": None,
                    "reason_codes": [],
                },
            )

    def read(self, intent_id: str) -> dict[str, Any]:
        with self._locked(intent_id) as path:
            return self._read(path)

    def begin_create(self, intent_id: str) -> dict[str, Any]:
        with self._locked(intent_id) as path:
            current = self._read(path)
            if current["creation_state"] != "prepared":
                raise InputError("RUN_CREATE_UNCERTAIN", "Create cannot be sent again")
            return self._write(path, {**current, "creation_state": "create_in_flight"})

    def record_create_response(self, intent_id: str, run_id: str) -> dict[str, Any]:
        nonempty(run_id, "/run_id", max_length=256)
        with self._locked(intent_id) as path:
            current = self._read(path)
            if current["creation_state"] != "create_in_flight":
                raise InputError("RUN_CREATE_UNCERTAIN", "Create response has no active request")
            return self._write(
                path,
                {**current, "run_id": run_id, "creation_state": "run_known"},
            )

    def mark_create_uncertain(self, intent_id: str) -> dict[str, Any]:
        with self._locked(intent_id) as path:
            current = self._read(path)
            if current["creation_state"] not in {"create_in_flight", "reconciliation_required"}:
                raise InputError("RUN_CREATE_UNCERTAIN", "No uncertain create to reconcile")
            return self._write(
                path,
                {
                    **current,
                    "creation_state": "reconciliation_required",
                    "reason_codes": ["RUN_CREATE_UNCERTAIN"],
                },
            )

    def begin_start(self, intent_id: str) -> dict[str, Any]:
        with self._locked(intent_id) as path:
            current = self._read(path)
            if (
                current["creation_state"] != "run_known"
                or current["start_state"] != "not_requested"
            ):
                raise InputError("RUN_START_UNCERTAIN", "Known run is not safe to start again")
            return self._write(path, {**current, "start_state": "start_in_flight"})

    def record_start_response(self, intent_id: str) -> dict[str, Any]:
        with self._locked(intent_id) as path:
            current = self._read(path)
            if current["start_state"] != "start_in_flight":
                raise InputError("RUN_START_UNCERTAIN", "Start response has no active request")
            return self._write(path, {**current, "start_state": "started"})

    def mark_start_uncertain(self, intent_id: str) -> dict[str, Any]:
        with self._locked(intent_id) as path:
            current = self._read(path)
            if current["start_state"] not in {"start_in_flight", "reconciliation_required"}:
                raise InputError("RUN_START_UNCERTAIN", "No uncertain start to reconcile")
            return self._write(
                path,
                {
                    **current,
                    "start_state": "reconciliation_required",
                    "reason_codes": sorted(set(current["reason_codes"] + ["RUN_START_UNCERTAIN"])),
                },
            )
