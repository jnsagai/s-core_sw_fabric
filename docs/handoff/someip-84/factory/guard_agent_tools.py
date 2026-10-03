"""Fail-closed Fabro pre_tool_use hook for the disposable SOME/IP agent stage."""

from __future__ import annotations

import json
import posixpath
import sys

ROOT = "/workspace"
WRITABLE = {
    f"{ROOT}/score/socom/BUILD",
    f"{ROOT}/score/socom/impl/service_identifier.cpp",
    f"{ROOT}/score/socom/impl/service_identifier.hpp",
    f"{ROOT}/score/socom/test/unit/BUILD",
    f"{ROOT}/score/socom/test/unit/runtime_tests.cpp",
    f"{ROOT}/score/socom/test/unit/service_identifier_tests.cpp",
}


def safe_path(value: object, *, exact_write: bool = False) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    path = posixpath.normpath(value if value.startswith("/") else ROOT + "/" + value)
    if path != ROOT and not path.startswith(ROOT + "/"):
        return False
    return path in WRITABLE if exact_write else True


def allowed(context: object) -> bool:
    if not isinstance(context, dict) or context.get("event") != "pre_tool_use":
        return False
    args = context.get("tool_input")
    if not isinstance(args, dict):
        return False
    name = context.get("tool_name")
    if name == "write_file":
        return safe_path(args.get("file_path"), exact_write=True) and isinstance(
            args.get("content"), str
        )
    if name == "read_file":
        return safe_path(args.get("file_path"))
    if name in {"grep", "glob"}:
        return isinstance(args.get("pattern"), str) and safe_path(args.get("path", ROOT))
    return False


def main() -> int:
    try:
        context = json.load(sys.stdin)
    except (ValueError, UnicodeDecodeError):
        context = None
    if allowed(context):
        return 0
    print('{"decision":"block","reason":"SOME/IP file-tool boundary"}')
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
