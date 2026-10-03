"""Exact records, bounded byte estimates and root-bound immutable artifact references."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import seal, verify_digest
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.request import parse_json

MAX_RAW_BYTES = 128 * 1024 * 1024


class OptimizationError(InputError):
    """Stable bounded refusal without copying raw input into model context."""

    def __init__(self, code: str) -> None:
        super().__init__(code, code + ": use bounded context/evidence tooling", "/optimization")


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def token_estimate(value: str | bytes) -> int:
    """Conservative UTF-8-byte upper estimate; never reported as provider usage."""
    return len(value.encode("utf-8") if isinstance(value, str) else value)


def checked(value: dict[str, Any], kind: str | None = None) -> dict[str, Any]:
    verify_digest(value, "/optimization")
    if kind and value.get("kind") != kind:
        raise OptimizationError("KIND_MISMATCH")
    return value


def record(kind: str, **fields: Any) -> dict[str, Any]:
    return seal({"schema_version": 1, "kind": kind, **fields})


def no_symlinks(path: Path) -> None:
    current = Path(path.absolute().anchor)
    for part in path.absolute().parts[1:]:
        current = current / part
        if current.is_symlink():
            raise OptimizationError("SYMLINK")


def safe_file(root: Path, relative: str, *, must_exist: bool = True) -> Path:
    if not isinstance(relative, str) or not relative or len(relative) > 1024:
        raise OptimizationError("INPUT_PATH")
    if relative.startswith("/") or "\\" in relative or "\x00" in relative:
        raise OptimizationError("INPUT_PATH")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise OptimizationError("INPUT_PATH")
    no_symlinks(root)
    selected = root.resolve(strict=True)
    for part in parts:
        selected = selected / part
        if selected.is_symlink():
            raise OptimizationError("SYMLINK")
    if must_exist and not selected.is_file():
        raise OptimizationError("EVIDENCE_MISSING")
    return selected


def raw_file(
    root: Path, relative: str, expected: str | None = None
) -> tuple[bytes, dict[str, Any]]:
    path = safe_file(root, relative)
    if path.stat().st_size > MAX_RAW_BYTES:
        raise OptimizationError("RAW_SIZE_LIMIT")
    data = path.read_bytes()
    if len(data) > MAX_RAW_BYTES:
        raise OptimizationError("RAW_SIZE_LIMIT")
    digest = hashlib.sha256(data).hexdigest()
    if expected is not None and expected != digest:
        raise OptimizationError("EVIDENCE_DRIFT")
    return data, {"path": relative, "sha256": digest, "bytes": len(data)}


def json_object(data: bytes) -> dict[str, Any]:
    try:
        value = parse_json(data, "/optimization")
    except (InputError, UnicodeError, RecursionError) as exc:
        raise OptimizationError("MALFORMED_JSON") from exc
    if not isinstance(value, dict):
        raise OptimizationError("JSON_ROOT")
    return value


def integer(value: Any, *, minimum: int = 0, maximum: int = 100_000_000) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise OptimizationError("INTEGER_LIMIT")
    return int(value)
