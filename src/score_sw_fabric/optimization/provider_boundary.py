"""Bounded DeepSeek transport for a disposable Fabro experiment, not an executor.

Reservations precede transmission. Unknown outcomes keep their reservation and stop
continuation. A response's reported usage and a conservative price calculation are
different observations; missing bills and reasoning counts remain null.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import HTTPRedirectHandler, Request, build_opener

from score_sw_fabric.optimization.activation import (
    governor_limits,
    private_file,
    verify_instruction,
)
from score_sw_fabric.optimization.common import OptimizationError, canonical, json_object


def project_request(raw: bytes, instruction: dict[str, Any]) -> bytes:
    """Remove only unavailable declarations; preserve messages and admitted schemas."""
    if "tool_projection" not in instruction:
        return raw
    from score_sw_fabric.optimization.firewall import BOUNDED_TOOLS

    selected = instruction["tool_projection"]["allowed_tools"]
    if not isinstance(selected, list) or not set(selected) <= BOUNDED_TOOLS:
        raise OptimizationError("TOOL_SELECTION")
    allowed = {"mcp__score_bounded__" + name for name in selected}
    value = json_object(raw)
    tools = value.get("tools", [])
    if not isinstance(tools, list):
        raise OptimizationError("TOOL_DECLARATION")
    names = set()
    retained = []
    for tool in tools:
        if (
            not isinstance(tool, dict)
            or tool.get("type") != "function"
            or not isinstance(tool.get("function"), dict)
        ):
            raise OptimizationError("TOOL_DECLARATION")
        name = tool["function"].get("name")
        if not isinstance(name, str) or name in names:
            raise OptimizationError("TOOL_DECLARATION")
        names.add(name)
        if name in allowed:
            retained.append(tool)
    choice = value.get("tool_choice")
    if not allowed <= names:
        raise OptimizationError("TOOL_SELECTION")
    if isinstance(choice, dict):
        if (
            choice.get("type") != "function"
            or not isinstance(choice.get("function"), dict)
            or choice["function"].get("name") not in allowed
        ):
            raise OptimizationError("TOOL_CHOICE")
    elif choice not in (None, "none", "auto", "required"):
        raise OptimizationError("TOOL_CHOICE")
    if not retained:
        if choice == "required" or isinstance(choice, dict):
            raise OptimizationError("TOOL_CHOICE")
        value.pop("tools", None)
        value.pop("tool_choice", None)
    else:
        value["tools"] = retained
    return canonical(value)


class RequestMeter:
    def __init__(self, instruction: Path, pin: str, state: Path):
        self.instruction, self.pin, self.state = instruction, pin, state
        if (
            state.parent != instruction.parent
            or state.is_symlink()
            or state.with_suffix(".lock").is_symlink()
        ):
            raise OptimizationError("PRIVATE_METER_REQUIRED")

    @contextmanager
    def transaction(self) -> Iterator[dict[str, Any]]:
        with open(self.state.with_suffix(".lock"), "a", opener=_private_open) as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = (
                json_object(private_file(self.state))
                if self.state.exists()
                else {
                    "instruction_sha256": self.pin,
                    "requests": 0,
                    "reserved_microusd": 0,
                    "stopped": None,
                    "records": [],
                }
            )
            try:
                if state["instruction_sha256"] != self.pin:
                    state["stopped"] = "INSTRUCTION_SUBSTITUTION"
                    raise OptimizationError("INSTRUCTION_SUBSTITUTION")
                yield state
            finally:
                descriptor, filename = tempfile.mkstemp(prefix=".meter-", dir=self.state.parent)
                try:
                    with os.fdopen(descriptor, "w") as output:
                        json.dump(state, output, sort_keys=True)
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(filename, self.state)
                finally:
                    if Path(filename).exists():
                        Path(filename).unlink()

    def stop(self, reason: str) -> None:
        with self.transaction() as state:
            state["stopped"] = state["stopped"] or reason

    def reserve(self, raw: bytes) -> int:
        return self.reserve_payload(raw)[0]

    def reserve_payload(self, raw: bytes) -> tuple[int, bytes]:
        with self.transaction() as state:
            try:
                if state["stopped"]:
                    raise OptimizationError("QUALIFICATION_STOPPED")
                config = verify_instruction(self.instruction, self.pin)
                if any(r["status"] == "reserved" for r in state["records"]):
                    raise OptimizationError("INFLIGHT_REQUEST")
                limits = config["limits"]
                admitted = governor_limits(config)
                if len(raw) > limits["request_bytes"]:
                    raise OptimizationError("CONTEXT_LIMIT")
                wire = project_request(raw, config)
                if len(wire) > min(limits["request_bytes"], admitted["context_tokens"]):
                    raise OptimizationError("CONTEXT_LIMIT")
                value = json_object(raw)
                if value.get("model") not in config["models"]:
                    raise OptimizationError("FLASH_ONLY")
                maximum = value.get("max_tokens", value.get("max_completion_tokens"))
                if type(maximum) is not int or not 0 < maximum <= min(
                    limits["output_tokens"], admitted["output_tokens"]
                ):
                    raise OptimizationError("OUTPUT_LIMIT")
                if (
                    "max_tokens" in value
                    and "max_completion_tokens" in value
                    or value.get("n", 1) != 1
                ):
                    raise OptimizationError("OUTPUT_LIMIT")
                messages = value.get("messages")
                if not isinstance(messages, list):
                    raise OptimizationError("TASK_BINDING")
                texts = list(_strings(messages))
                selected = [
                    t for t in config["tasks"] if any(t["prompt"] in text for text in texts)
                ]
                if len(selected) != 1:
                    raise OptimizationError("TASK_BINDING")
                task = selected[0]
                used = sum(r["task"] == task["marker"] for r in state["records"])
                if used >= min(task["max_requests"], admitted["calls"]):
                    raise OptimizationError("TASK_CALL_LIMIT")
                previous = [r for r in state["records"] if r["task"] == task["marker"]]
                if len(wire) + sum(r["request_bytes"] for r in previous) > admitted["input_tokens"]:
                    raise OptimizationError("OPERATIONAL_INPUT_LIMIT")
                if (
                    maximum + sum(r["maximum_output_tokens"] for r in previous)
                    > admitted["output_tokens"]
                ):
                    raise OptimizationError("OPERATIONAL_OUTPUT_LIMIT")
                if state["requests"] >= limits["requests"]:
                    raise OptimizationError("CALL_LIMIT")
                # One token per UTF-8 byte bounds serialized context conservatively.
                upper = math.ceil(len(wire) * 0.3 + maximum * 1.2)
                if state["reserved_microusd"] + upper > limits["cost_microusd"]:
                    raise OptimizationError("COST_LIMIT")
                ticket = state["requests"]
                state["requests"] += 1
                state["reserved_microusd"] += upper
                state["records"].append(
                    {
                        "ticket": ticket,
                        "task": task["marker"],
                        "status": "reserved",
                        "model": value["model"],
                        "native_request_sha256": hashlib.sha256(raw).hexdigest(),
                        "native_request_bytes": len(raw),
                        "request_sha256": hashlib.sha256(wire).hexdigest(),
                        "request_bytes": len(wire),
                        "maximum_output_tokens": maximum,
                        "admitted_limits": admitted,
                        "reserved_microusd": upper,
                    }
                )
                return int(ticket), wire
            except (OptimizationError, OSError, ValueError, TypeError, KeyError) as error:
                state["stopped"] = state["stopped"] or (
                    error.code if isinstance(error, OptimizationError) else "INPUT_REJECTED"
                )
                raise

    def finish(self, ticket: int, usage: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as state:
            try:
                config = verify_instruction(self.instruction, self.pin)
                entry = state["records"][ticket]
                if entry["status"] != "reserved" or state["stopped"]:
                    raise OptimizationError("QUALIFICATION_STOPPED")
                names = (
                    "prompt_tokens",
                    "completion_tokens",
                    "prompt_cache_hit_tokens",
                    "prompt_cache_miss_tokens",
                )
                if any(type(usage.get(n)) is not int or usage[n] < 0 for n in names):
                    raise OptimizationError("USAGE_UNKNOWN")
                if (
                    usage["prompt_cache_hit_tokens"] + usage["prompt_cache_miss_tokens"]
                    != usage["prompt_tokens"]
                ):
                    raise OptimizationError("USAGE_INCONSISTENT")
                if (
                    usage["prompt_tokens"] > entry["request_bytes"]
                    or usage["completion_tokens"] > entry["maximum_output_tokens"]
                ):
                    raise OptimizationError("USAGE_EXCEEDS_BOUND")
                bound = math.ceil(usage["prompt_tokens"] * 0.3 + usage["completion_tokens"] * 1.2)
                details = usage.get("completion_tokens_details") or {}
                if not isinstance(details, dict):
                    raise OptimizationError("USAGE_INCONSISTENT")
                reasoning = details.get("reasoning_tokens")
                if reasoning is not None and (
                    type(reasoning) is not int or not 0 <= reasoning <= usage["completion_tokens"]
                ):
                    raise OptimizationError("USAGE_INCONSISTENT")
                entry.update(
                    status="observed",
                    usage={n: usage[n] for n in names},
                    actual_cost_usd=None,
                    reasoning_tokens=reasoning,
                    cost_upper_bound_microusd=bound,
                    price_source="https://api-docs.deepseek.com/quick_start/pricing/",
                    price_bounds=config["price_bounds"],
                )
                return dict(entry)
            except (
                OptimizationError,
                OSError,
                ValueError,
                TypeError,
                KeyError,
                IndexError,
            ) as error:
                state["stopped"] = state["stopped"] or (
                    error.code if isinstance(error, OptimizationError) else "INPUT_REJECTED"
                )
                raise


def _private_open(path: str, flags: int) -> int:
    return os.open(path, flags | os.O_NOFOLLOW, 0o600)


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def reported_usage(response: bytes, *, stream: bool) -> dict[str, Any]:
    if not stream:
        return dict(json_object(response).get("usage") or {})
    observations = []
    for line in response.splitlines():
        if line.startswith(b"data: ") and line != b"data: [DONE]":
            value = json_object(line[6:])
            if value.get("usage"):
                observations.append(value["usage"])
    return dict(observations[-1]) if observations else {}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def boundary_server(
    meter: RequestMeter, port: int, nonce: str, artifact_root: Path
) -> ThreadingHTTPServer:
    """Loopback-only transport; credentials are never recorded or printed."""
    from score_sw_fabric.storage import validate_run_root

    validate_run_root(artifact_root)
    if len(nonce) < 32:
        raise OptimizationError("PRIVATE_TRANSPORT_REQUIRED")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            try:
                validate_run_root(artifact_root)
                if self.path not in (f"/{nonce}/chat/completions", f"/{nonce}/v1/chat/completions"):
                    raise OptimizationError("TRANSPORT_PATH")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 24000 or self.headers.get("Transfer-Encoding"):
                    meter.stop("CONTEXT_LIMIT")
                    raise OptimizationError("CONTEXT_LIMIT")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise OptimizationError("INPUT_REJECTED")
                ticket, wire = meter.reserve_payload(raw)
                (artifact_root / f"native-request-{ticket:02d}.json").write_bytes(raw)
                (artifact_root / f"request-{ticket:02d}.json").write_bytes(wire)
                auth = self.headers.get("Authorization", "")
                if not auth.startswith("Bearer "):
                    raise OptimizationError("PROVIDER_CREDENTIAL_REQUIRED")
                upstream = Request(
                    "https://api.deepseek.com/chat/completions",
                    wire,
                    {"Authorization": auth, "Content-Type": "application/json"},
                )
                # Buffer bounded response so missing usage stops before another request.
                with build_opener(_NoRedirect()).open(upstream, timeout=180) as reply:
                    response = reply.read(2_000_001)
                    if len(response) > 2_000_000:
                        raise OptimizationError("RESPONSE_LIMIT")
                    (artifact_root / f"response-{ticket:02d}.raw").write_bytes(response)
                    meter.finish(
                        ticket,
                        reported_usage(response, stream=bool(json_object(raw).get("stream"))),
                    )
                    self.send_response(reply.status)
                    self.send_header(
                        "Content-Type", reply.headers.get("Content-Type", "application/json")
                    )
                    self.send_header("Content-Length", str(len(response)))
                    self.end_headers()
                    self.wfile.write(response)
            except Exception as error:
                reason = (
                    error.code
                    if isinstance(error, OptimizationError)
                    else "PROVIDER_TRANSPORT_FAILED"
                )
                meter.stop(str(reason))
                self.send_response(403 if isinstance(error, OptimizationError) else 502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {"error": {"message": str(reason), "type": "qualification_stop"}}
                    ).encode()
                )

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
