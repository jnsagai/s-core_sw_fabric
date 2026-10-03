"""Repository-owned bounded stdio MCP tools; no providers, shell or raw evidence tools."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from score_sw_fabric.optimization.common import (
    OptimizationError,
    canonical,
    integer,
    json_object,
    raw_file,
    record,
)
from score_sw_fabric.optimization.evidence_query import query
from score_sw_fabric.optimization.firewall import BOUNDED_TOOLS, admit_tool
from score_sw_fabric.optimization.tool_results import StageBudget
from score_sw_fabric.process_source.reader import InputError

MAX_REQUEST = 8192


def tool_schema(name: str) -> dict[str, Any]:
    properties: dict[str, Any] = {"path": {"type": "string", "maxLength": 1024}}
    required = ["path"]
    if name == "get_source_excerpt":
        properties.update(
            start={"type": "integer", "minimum": 1}, end={"type": "integer", "minimum": 1}
        )
        required += ["start", "end"]
    elif name == "get_observation":
        properties.update(
            id={"type": "string", "maxLength": 512},
            sha256={"type": "string", "pattern": "^[0-9a-f]{64}$"},
        )
        required += ["id", "sha256"]
    else:
        properties.update(
            operation={
                "enum": ["summary", "findings", "count_by_rule", "count_by_path", "json_summary"]
            },
            rule={"type": "string", "maxLength": 512},
            file={"type": "string", "maxLength": 512},
            line={"type": "integer", "minimum": 1},
            offset={"type": "integer", "minimum": 0},
            limit={"type": "integer", "minimum": 1, "maximum": 30},
            expected_sha256={"type": "string", "pattern": "^[0-9a-f]{64}$"},
        )
        required += {
            "sarif_find_rule": ["rule"],
            "sarif_find_file": ["file"],
            "sarif_find_location": ["file", "line"],
        }.get(name, [])
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


class BoundedService:
    def __init__(
        self,
        root: Path,
        state: Path,
        *,
        stage: str = "bounded-tools",
        sources: dict[str, str] | None = None,
    ) -> None:
        from score_sw_fabric.optimization.common import no_symlinks

        no_symlinks(root)
        self.root = root.resolve(strict=True)
        self.storage_bindings = {
            str(parent): hashlib.sha256(
                (parent / "storage-selection.json").read_bytes()
            ).hexdigest()
            for selected in (self.root, state.absolute().parent)
            for parent in (selected, *selected.parents)
            if (parent / "storage-selection.json").is_file()
        }
        self.budget = StageBudget(
            state, stage, binding=hashlib.sha256(str(self.root).encode()).hexdigest()
        )
        state.parent.mkdir(parents=True, exist_ok=True)
        self.sources = sources or {}

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        from score_sw_fabric.storage import validate_run_root

        for parent, expected in self.storage_bindings.items():
            binding_root = Path(parent)
            try:
                validate_run_root(binding_root)
                if (
                    hashlib.sha256(
                        (binding_root / "storage-selection.json").read_bytes()
                    ).hexdigest()
                    != expected
                ):
                    raise OptimizationError("STORAGE_BINDING_DRIFT")
            except (ValueError, OSError) as error:
                raise OptimizationError("STORAGE_DISCONNECTED") from error
        stop = self.budget.path.with_suffix(self.budget.path.suffix + ".stop")
        if stop.is_symlink():
            raise OptimizationError("SYMLINK")
        if stop.exists():
            raise OptimizationError("STAGE_STOPPED")
        try:
            return self._call(name, arguments)
        except (InputError, ValueError, KeyError, TypeError, OSError) as error:
            code = error.code if isinstance(error, InputError) else "INPUT_REJECTED"
            try:
                with stop.open("xb") as stream:
                    stream.write(
                        canonical(
                            record("stage_context_stop", stage=self.budget.stage, reason=code)
                        )
                    )
            except FileExistsError:
                pass
            raise OptimizationError(str(code)) from error

    def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        admit_tool(name, arguments)
        if set(tool_schema(name)["required"]) - set(arguments):
            raise OptimizationError("QUERY_FIELDS")
        if name == "get_source_excerpt":
            if set(arguments) != {"path", "start", "end"} or arguments["path"] not in self.sources:
                raise OptimizationError("SOURCE_NOT_IN_MANIFEST")
            start = integer(arguments["start"], minimum=1)
            end = integer(arguments["end"], minimum=start, maximum=start + 249)
            path = arguments["path"]
            if Path(path).suffix.lower() in {".json", ".jsonl", ".sarif", ".xml", ".log"}:
                raise OptimizationError("RAW_STRUCTURED_EVIDENCE_FORBIDDEN")
            data, raw = raw_file(self.root, path, self.sources[path])
            lines = data.decode("utf-8").splitlines()
            excerpt = "\n".join(lines[start - 1 : end])
            if len(excerpt.encode()) > 3000:
                raise OptimizationError("RESULT_LIMIT")
            from score_sw_fabric.agents.context import credential_like

            if credential_like(excerpt):
                raise OptimizationError("CREDENTIAL_IN_CONTEXT")
            result = record(
                "source_excerpt", raw=raw, start=start, end=min(end, len(lines)), text=excerpt
            )
        elif name == "get_observation":
            if set(arguments) != {"path", "id", "sha256"}:
                raise OptimizationError("QUERY_FIELDS")
            data, raw = raw_file(self.root, arguments["path"], arguments["sha256"])
            matches = [json_object(line) for line in data.splitlines() if line.strip()]
            selected = [item for item in matches if item.get("id") == arguments["id"]]
            if len(selected) != 1:
                raise OptimizationError("OBSERVATION_UNKNOWN")
            from score_sw_fabric.agents.context import credential_like

            text = str(selected[0].get("text", ""))
            if credential_like(text):
                raise OptimizationError("CREDENTIAL_IN_CONTEXT")
            result = record(
                "observation_hint", id=arguments["id"], text=text, raw=raw, authority="hint_only"
            )
        else:
            fields = {
                "path",
                "operation",
                "rule",
                "file",
                "line",
                "offset",
                "limit",
                "expected_sha256",
            }
            if set(arguments) - fields or "path" not in arguments:
                raise OptimizationError("QUERY_FIELDS")
            operations = {
                "finding_list": "findings",
                "finding_get": "findings",
                "sarif_find_rule": "findings",
                "sarif_find_file": "findings",
                "sarif_find_location": "findings",
                "sarif_count_by_rule": "count_by_rule",
                "sarif_count_by_path": "count_by_path",
            }
            options = dict(arguments)
            path = options.pop("path")
            options["operation"] = operations.get(name, options.get("operation", "summary"))
            if name == "finding_get":
                options["limit"] = 1
            result = query(self.root, path, **options)
        # Include escaping, MCP metadata and maximum request-ID overhead in context accounting.
        delivery = {
            "jsonrpc": "2.0",
            "id": "x" * 64,
            "result": {
                "content": [{"type": "text", "text": canonical(result).decode()}],
                "isError": False,
            },
        }
        self.budget.consume(
            {"name": name, "arguments": arguments}, delivery, evidence=result.get("raw")
        )
        return result


def serve(
    service: BoundedService, incoming: TextIO = sys.stdin, outgoing: TextIO = sys.stdout
) -> None:
    """One JSON-RPC line per request; notifications produce no response."""
    while True:
        line = incoming.readline(MAX_REQUEST + 1)
        if not line:
            return
        if len(line.encode()) > MAX_REQUEST or not line.endswith("\n"):
            # Stop rather than interpreting the remaining tail as another request.
            return
        identifier: Any = None
        try:
            request = json_object(line.encode())
            identifier = request.get("id")
            if identifier is None:
                continue
            if not (
                type(identifier) is int
                and 0 <= identifier <= 2**31
                or isinstance(identifier, str)
                and len(identifier.encode()) <= 64
            ):
                raise OptimizationError("REQUEST_ID_LIMIT")
            method = request.get("method")
            if method == "initialize":
                result: dict[str, Any] = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "score-fabric-bounded-context", "version": "011-v1"},
                }
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": name,
                            "description": "Bounded digest-bound retrieval",
                            "inputSchema": tool_schema(name),
                        }
                        for name in sorted(BOUNDED_TOOLS)
                    ]
                }
            elif method == "tools/call":
                params = request["params"]
                output = service.call(params["name"], params.get("arguments", {}))
                result = {
                    "content": [{"type": "text", "text": canonical(output).decode()}],
                    "isError": False,
                }
            else:
                raise OptimizationError("MCP_METHOD")
            response = {"jsonrpc": "2.0", "id": identifier, "result": result}
        except (OptimizationError, ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
            code = exc.code if isinstance(exc, OptimizationError) else "INPUT_REJECTED"
            response = {
                "jsonrpc": "2.0",
                "id": identifier,
                "error": {"code": -32602, "message": str(code)},
            }
        outgoing.write(json.dumps(response, separators=(",", ":")) + "\n")
        outgoing.flush()
