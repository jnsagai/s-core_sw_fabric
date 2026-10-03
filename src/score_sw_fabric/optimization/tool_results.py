"""Preserve full output on disk; serialize persistent stage budgets before reinjection."""

from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
from typing import Any

from score_sw_fabric.optimization.common import (
    OptimizationError,
    canonical,
    checked,
    integer,
    json_object,
    no_symlinks,
    record,
    safe_file,
    token_estimate,
)


def summarize_output(
    data: bytes, root: Path, name: str, *, max_bytes: int = 12000
) -> dict[str, Any]:
    integer(max_bytes, minimum=600, maximum=12000)
    path = safe_file(root, name, must_exist=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError as exc:
        raise OptimizationError("EVIDENCE_EXISTS") from exc
    raw = {"path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    preview_bytes = max_bytes // 2
    while True:
        clipped = len(data) > preview_bytes
        preview = (
            (
                data[: preview_bytes // 2]
                + b"\n[omitted; see raw reference]\n"
                + data[-preview_bytes // 2 :]
            )
            if clipped
            else data
        )
        result = record(
            "tool_result_summary",
            raw=raw,
            preview=preview.decode("utf-8", "replace"),
            truncated=clipped,
            estimate_method="utf8_bytes_upper_bound",
        )
        if len(canonical(result)) <= max_bytes:
            return result
        preview_bytes //= 2
        if not preview_bytes:
            raise OptimizationError("RESULT_LIMIT")


class StageBudget:
    """Derived context accounting; not Fabro run state or an approval ledger."""

    def __init__(
        self,
        path: Path,
        stage: str,
        *,
        max_result_bytes: int = 12000,
        max_result_tokens: int = 5000,
        max_total_tokens: int = 12000,
        binding: str | None = None,
    ) -> None:
        if not stage or len(stage) > 128 or path.is_symlink() or path.parent.is_symlink():
            raise OptimizationError("INPUT_PATH")
        no_symlinks(path)
        self.path, self.stage = path, stage
        self.binding = binding
        self.limits = {
            "max_result_bytes": integer(max_result_bytes, minimum=1),
            "max_result_tokens": integer(max_result_tokens, minimum=1),
            "max_total_tokens": integer(max_total_tokens, minimum=1),
        }

    def consume(
        self,
        request: dict[str, Any],
        result: dict[str, Any],
        *,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = canonical(result)
        tokens = token_estimate(payload)
        if (
            len(payload) > self.limits["max_result_bytes"]
            or tokens > self.limits["max_result_tokens"]
        ):
            raise OptimizationError("RESULT_LIMIT")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        if lock.is_symlink():
            raise OptimizationError("SYMLINK")
        with lock.open("a+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            if self.path.is_symlink():
                raise OptimizationError("SYMLINK")
            if self.path.exists():
                state = checked(json_object(self.path.read_bytes()), "stage_context_budget")
                if (
                    state["stage"] != self.stage
                    or state["limits"] != self.limits
                    or state.get("binding") != self.binding
                ):
                    raise OptimizationError("STAGE_MISMATCH")
            else:
                state = record(
                    "stage_context_budget",
                    stage=self.stage,
                    limits=self.limits,
                    tokens=0,
                    result_bytes=0,
                    queries=[],
                    binding=self.binding,
                    raw_bindings={},
                )
            raw_bindings = dict(state.get("raw_bindings", {}))
            if evidence is not None:
                previous = raw_bindings.get(evidence["path"])
                if previous is not None and previous != evidence["sha256"]:
                    raise OptimizationError("EVIDENCE_DRIFT")
                raw_bindings[evidence["path"]] = evidence["sha256"]
            query_digest = hashlib.sha256(canonical(request)).hexdigest()
            if query_digest in state["queries"]:
                raise OptimizationError("REPEATED_QUERY")
            if state["tokens"] + tokens > self.limits["max_total_tokens"]:
                raise OptimizationError("STAGE_BUDGET")
            state = record(
                "stage_context_budget",
                stage=self.stage,
                limits=self.limits,
                tokens=state["tokens"] + tokens,
                result_bytes=state["result_bytes"] + len(payload),
                queries=[*state["queries"], query_digest],
                binding=self.binding,
                raw_bindings=raw_bindings,
            )
            temporary = self.path.with_suffix(self.path.suffix + ".new")
            if temporary.is_symlink():
                raise OptimizationError("SYMLINK")
            with temporary.open("wb") as target:
                target.write(canonical(state))
                target.flush()
                os.fsync(target.fileno())
            temporary.replace(self.path)
        return result
