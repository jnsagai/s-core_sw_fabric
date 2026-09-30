"""Canonical draft-plan sealing and protected atomic output."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.planning.models import PlanningInputs
from score_sw_fabric.process_source.reader import InputError


def seal_plan(payload: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    digest = hashlib.sha256(canonical(payload)).hexdigest()
    plan = {**payload, "digest": digest}
    return plan, canonical(plan)


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.exists() and right.exists() and os.path.samefile(left, right)
    except OSError:
        return False


def write_plan(path: Path, data: bytes, inputs: PlanningInputs) -> None:
    """Atomically replace an output after excluding all input/reference locations."""

    target = (Path.cwd() / path).absolute()
    resolved = target.resolve()
    if not resolved.is_relative_to(inputs.output_root.resolve()):
        raise InputError("OUTPUT_PATH", "Output must be beneath the declared output root")
    if target.is_symlink() or any(
        parent.is_symlink()
        for parent in target.parents
        if parent != inputs.output_root and parent.is_relative_to(inputs.output_root)
    ):
        raise InputError("OUTPUT_SYMLINK", "Output path may not traverse a symlink")
    if any(
        resolved == root.resolve() or resolved.is_relative_to(root.resolve())
        for root in inputs.reference_roots
    ):
        raise InputError("OUTPUT_SOURCE_ROOT", "Output may not modify a reference tree")
    if any(resolved == item.resolve() or _same_file(target, item) for item in inputs.input_paths):
        raise InputError("OUTPUT_ALIAS", "Output aliases a planning input")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".plan-", dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError as exc:
        raise InputError("OUTPUT_IO", str(exc)) from exc
