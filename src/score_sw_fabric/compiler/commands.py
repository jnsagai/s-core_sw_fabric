"""Explicit bindings from deterministic actions to closed packaged scripts."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from score_sw_fabric.compiler.models import CompilerSemanticError


def command_binding(action: dict[str, Any], action_type: str) -> str | None:
    """Validate an optional binding without interpreting its filename as shell code."""

    if "command_file" not in action:
        return None
    if action_type not in {"command", "deterministic_check"}:
        raise CompilerSemanticError("COMMAND_BINDING", "Only command actions may bind scripts")
    raw = action["command_file"]
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw:
        raise CompilerSemanticError("COMMAND_BINDING", "Invalid command script path")
    path = PurePosixPath(raw)
    if (
        not path.parts
        or path.is_absolute()
        or path.as_posix() != raw
        or any(p in {".", ".."} for p in path.parts)
    ):
        raise CompilerSemanticError("COMMAND_BINDING", "Unsafe command script path")
    if raw not in action["support_files"]:
        raise CompilerSemanticError("COMMAND_BINDING", "Command script must be in action support")
    return raw
