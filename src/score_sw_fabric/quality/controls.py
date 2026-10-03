"""Bounded quality control bytes and JSON-compatible YAML trees."""

from __future__ import annotations

import hashlib
import math
import stat
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import exact, sha
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.request import _local, _no_links, parse_yaml

MAX_CONTROL = 1024 * 1024


def bounded_tree(value: Any) -> None:
    pending = [(value, 0)]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if depth > 64 or count > 200_000:
            raise InputError("LIMIT_EXCEEDED", "Native nesting/node limit exceeded")
        if isinstance(node, dict):
            if any(not isinstance(k, str) for k in node):
                raise InputError("NATIVE_OUTPUT_INVALID", "Native object keys must be strings")
            pending.extend((v, depth + 1) for v in node.values())
        elif isinstance(node, list):
            pending.extend((v, depth + 1) for v in node)
        elif type(node) is float and not math.isfinite(node):
            raise InputError("NATIVE_OUTPUT_INVALID", "Nonfinite native number")
        elif node is not None and type(node) not in {str, int, float, bool}:
            raise InputError("NATIVE_OUTPUT_INVALID", "Non-JSON native value")


def read_control(path: Path, pointer: str = "/control") -> bytes:
    path = _no_links(path, pointer)
    try:
        details = path.stat()
        if not stat.S_ISREG(details.st_mode) or details.st_size > MAX_CONTROL:
            raise InputError("LIMIT_EXCEEDED", "Control exceeds regular-file/1 MiB bounds", pointer)
        with path.open("rb") as stream:
            data = stream.read(MAX_CONTROL + 1)
        if len(data) > MAX_CONTROL:
            raise InputError("LIMIT_EXCEEDED", "Control grew beyond 1 MiB", pointer)
        return data
    except OSError as exc:
        raise InputError("INPUT_INVALID", "Cannot read bounded control", pointer) from exc


def selected_bytes(base: Path, value: Any, pointer: str) -> tuple[Path, bytes]:
    ref = exact(value, {"path", "sha256"}, pointer)
    path = _local(base, ref["path"], pointer + "/path")
    data = read_control(path, pointer)
    if hashlib.sha256(data).hexdigest() != sha(ref["sha256"], pointer + "/sha256"):
        raise InputError("INPUT_DRIFT", "Selected control bytes changed", pointer)
    return path, data


def yaml_tree(data: bytes, pointer: str, *, max_bytes: int = MAX_CONTROL) -> Any:
    if len(data) > max_bytes:
        raise InputError("LIMIT_EXCEEDED", "YAML exceeds selected byte bound", pointer)
    try:
        value = parse_yaml(data, pointer)
        bounded_tree(value)
        return value
    except (RecursionError, ValueError) as exc:
        raise InputError("INPUT_INVALID", "Malformed or deeply nested YAML", pointer) from exc
