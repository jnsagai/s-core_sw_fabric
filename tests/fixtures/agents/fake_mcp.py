"""Fixture stdio MCP server for 007 contract tests; `mode.txt` beside it selects a fault."""

import json
import sys
import time
from pathlib import Path

MODE_FILE = Path(__file__).with_name("mode.txt")
MODE = MODE_FILE.read_text().strip() if MODE_FILE.exists() else "normal"
SETUP = False

TOOLS = [
    {
        "name": "read_info",
        "description": "Return fixture information.",
        "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}}},
    },
    {
        "name": "note",
        "description": "Append a hint record.",
        "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}},
    },
    {
        "name": "setup_store",
        "description": "Create the local hint store.",
        "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}}},
    },
]


def tools() -> list[dict]:
    selected = TOOLS if SETUP else TOOLS[:2]
    if MODE == "extra_tool":
        return [*selected, {"name": "surprise", "inputSchema": {"type": "object"}}]
    if MODE == "missing_tool":
        return selected[1:]
    if MODE == "schema_drift":
        changed = dict(selected[0], description="Changed instructions.")
        return [changed, *selected[1:]]
    return selected


def call(name: str, arguments: dict) -> dict:
    store = Path.cwd() / ".score-local"
    if name == "read_info":
        if MODE == "tool_error":
            return {"content": [{"type": "text", "text": "failed"}], "isError": True}
        return {"content": [{"type": "text", "text": json.dumps({"ok": True, "mode": MODE})}]}
    if name == "note":
        store.mkdir(exist_ok=True)
        with (store / "sessions.jsonl").open("a") as stream:
            record = {"id": f"reasoning__{time.time_ns()}", "record_type": "reasoning"}
            stream.write(json.dumps({**record, "text": arguments.get("text", "")}) + "\n")
        return {"content": [{"type": "text", "text": "{}"}]}
    if name == "setup_store":
        repo = Path(arguments["repo_path"])
        (repo / ".score-local").mkdir(exist_ok=True)
        ignore = repo / ".gitignore"
        if ".score-local/" not in (ignore.read_text() if ignore.exists() else ""):
            with ignore.open("a") as stream:
                stream.write(".score-local/\n")
        if MODE == "setup_stray":
            (repo / "stray.txt").write_text("x")
        return {"content": [{"type": "text", "text": json.dumps({"ok": True})}]}
    raise ValueError(name)


def main() -> None:
    if MODE == "crash":
        sys.exit(3)
    (Path.cwd() / ".score-local").mkdir(exist_ok=True)
    (Path.cwd() / ".score-local" / "started").write_text("1")
    if MODE == "undeclared_write":
        (Path.cwd() / "stray.txt").write_text("x")
    for line in sys.stdin:
        request = json.loads(line)
        method = request.get("method")
        if "id" not in request:
            continue
        if MODE == "timeout":
            time.sleep(30)
        if MODE == "oversize":
            sys.stdout.write("x" * 5000 + "\n")
            sys.stdout.flush()
            continue
        if MODE == "invalid_json":
            sys.stdout.write("{not json\n")
            sys.stdout.flush()
            continue
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/message"}) + "\n")
        if method == "initialize":
            result = {
                "protocolVersion": "2025-03-26" if MODE == "protocol" else "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "impostor" if MODE == "identity" else "fake",
                    "version": "1.0.0",
                },
            }
        elif method == "tools/list":
            result = {"tools": tools()}
        elif method == "tools/call":
            try:
                result = call(request["params"]["name"], request["params"].get("arguments", {}))
            except (KeyError, ValueError) as exc:
                message = {"code": -32000, "message": str(exc)}
                response = {"jsonrpc": "2.0", "id": request["id"], "error": message}
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                continue
        else:
            result = {}
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}))
        sys.stdout.write("\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
