"""Minimal bounded MCP stdio client for observing pinned context servers."""

from __future__ import annotations

import hashlib
import json
import os
import selectors
import subprocess
import tempfile
import time
from pathlib import Path
from types import TracebackType
from typing import Any

from score_sw_fabric.process_source.reader import _pairs, _reject_constant

MAX_SKIPPED_MESSAGES = 1000
MAX_STDERR_BYTES = 64 * 1024
CLIENT_INFO = {"name": "score-fabric", "version": "007"}


class McpError(Exception):
    """A handshake, transport or tool failure with a stable code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail[:512]


class McpSession:
    """One stdio server process with newline-delimited JSON-RPC and hard bounds."""

    def __init__(
        self,
        argv: list[str],
        *,
        cwd: Path,
        environment: dict[str, str],
        line_bytes: int,
    ) -> None:
        self._argv = argv
        self._cwd = cwd
        self._environment = environment
        self._line_bytes = line_bytes
        self._buffer = b""
        self._next_id = 1
        self._stderr = tempfile.TemporaryFile(dir="/tmp")
        self._process: subprocess.Popen[bytes] | None = None
        self.returncode: int | None = None
        self.stderr_sha256: str | None = None
        self.stderr_bytes = 0

    def __enter__(self) -> McpSession:
        try:
            self._process = subprocess.Popen(
                self._argv,
                cwd=self._cwd,
                env=self._environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self._stderr,
                start_new_session=True,
            )
        except OSError as exc:
            self._stderr.close()
            raise McpError("HANDSHAKE_FAILED", f"Server could not start: {exc}") from exc
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        process = self._process
        if process is None:
            return
        self._process = None
        try:
            if process.stdin is not None:
                process.stdin.close()
        except OSError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if process.stdout is not None:
            process.stdout.close()
        self.returncode = process.returncode
        self._stderr.seek(0)
        payload = self._stderr.read(MAX_STDERR_BYTES + 1)
        self.stderr_bytes = len(payload)
        self.stderr_sha256 = hashlib.sha256(payload[:MAX_STDERR_BYTES]).hexdigest()
        self._stderr.close()

    def _send(self, message: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None:
            raise McpError("HANDSHAKE_FAILED", "Server is not running")
        try:
            process.stdin.write(json.dumps(message, separators=(",", ":")).encode() + b"\n")
            process.stdin.flush()
        except OSError as exc:
            raise McpError("HANDSHAKE_FAILED", "Server closed its input") from exc

    def _read_line(self, deadline: float) -> bytes:
        process = self._process
        if process is None or process.stdout is None:
            raise McpError("HANDSHAKE_FAILED", "Server is not running")
        descriptor = process.stdout.fileno()
        with selectors.DefaultSelector() as selector:
            selector.register(descriptor, selectors.EVENT_READ)
            while b"\n" not in self._buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise McpError("TIMEOUT", "Server response timed out")
                if not selector.select(remaining):
                    continue
                chunk = os.read(descriptor, 65536)
                if not chunk:
                    raise McpError("HANDSHAKE_FAILED", "Server closed its output")
                self._buffer += chunk
                if len(self._buffer.split(b"\n", 1)[0]) > self._line_bytes:
                    raise McpError("LINE_LIMIT", "Server message exceeds the line limit")
        line, self._buffer = self._buffer.split(b"\n", 1)
        if len(line) > self._line_bytes:
            raise McpError("LINE_LIMIT", "Server message exceeds the line limit")
        return line

    def request(self, method: str, params: dict[str, Any], timeout: float) -> Any:
        """Send one request and return its result, skipping bounded unrelated messages."""
        identifier = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        for _ in range(MAX_SKIPPED_MESSAGES):
            line = self._read_line(deadline)
            if not line.strip():
                continue
            try:
                message = json.loads(
                    line, object_pairs_hook=_pairs, parse_constant=_reject_constant
                )
            except (UnicodeDecodeError, ValueError) as exc:
                raise McpError("PROTOCOL_ERROR", "Server sent invalid JSON") from exc
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                raise McpError("PROTOCOL_ERROR", "Server sent a non JSON-RPC message")
            if "id" not in message or message["id"] != identifier:
                continue
            if "error" in message:
                error = message["error"]
                code = error.get("code") if isinstance(error, dict) else None
                raise McpError("JSONRPC_ERROR", f"{method} returned JSON-RPC error {code}")
            if set(message) != {"jsonrpc", "id", "result"}:
                raise McpError("PROTOCOL_ERROR", "Response lacks an exact result")
            return message["result"]
        raise McpError("PROTOCOL_ERROR", "Too many unrelated server messages")

    def notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})


def initialize(session: McpSession, protocol_version: str, timeout: float) -> dict[str, Any]:
    result = session.request(
        "initialize",
        {"protocolVersion": protocol_version, "capabilities": {}, "clientInfo": CLIENT_INFO},
        timeout,
    )
    if not isinstance(result, dict) or not isinstance(result.get("serverInfo"), dict):
        raise McpError("PROTOCOL_ERROR", "initialize result lacks serverInfo")
    session.notify("notifications/initialized")
    return result


def list_tools(session: McpSession, timeout: float, limit: int) -> list[dict[str, Any]]:
    result = session.request("tools/list", {}, timeout)
    if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
        raise McpError("PROTOCOL_ERROR", "tools/list result lacks tools")
    if result.get("nextCursor") is not None:
        raise McpError("PROTOCOL_ERROR", "Paginated tool lists are unsupported")
    tools: list[dict[str, Any]] = result["tools"]
    if len(tools) > limit or any(
        not isinstance(item, dict) or not isinstance(item.get("name"), str) for item in tools
    ):
        raise McpError("PROTOCOL_ERROR", "tools/list returned malformed or too many tools")
    return tools


def call_tool(
    session: McpSession, name: str, arguments: dict[str, Any], timeout: float, limit: int
) -> str:
    """Call one tool and return its concatenated text content, bounded to `limit` bytes."""
    result = session.request("tools/call", {"name": name, "arguments": arguments}, timeout)
    if not isinstance(result, dict) or not isinstance(result.get("content"), list):
        raise McpError("PROTOCOL_ERROR", "tools/call result lacks content")
    if result.get("isError") is True:
        raise McpError("TOOL_ERROR", f"{name} reported a tool error")
    parts = []
    for item in result["content"]:
        if (
            not isinstance(item, dict)
            or item.get("type") != "text"
            or not isinstance(item.get("text"), str)
        ):
            raise McpError("PROTOCOL_ERROR", "Only text tool content is supported")
        parts.append(item["text"])
    text = "".join(parts)
    if len(text.encode()) > limit:
        raise McpError("RESULT_LIMIT", f"{name} result exceeds the result limit")
    return text
