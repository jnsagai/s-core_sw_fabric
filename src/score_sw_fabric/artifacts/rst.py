"""Lossless bounded RST directive scanning without executing RST content."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from score_sw_fabric.artifacts.models import ArtifactSemanticError, finding
from score_sw_fabric.process_source.reader import InputError

DIRECTIVE = re.compile(
    r"^(?P<indent>[ ]*)\.\. (?P<name>[A-Za-z][A-Za-z0-9_.-]*)::(?:[ ]?(?P<title>.*))?$"
)
OPTION = re.compile(r"^(?P<indent>[ ]*):(?P<name>[A-Za-z][A-Za-z0-9_.-]*):(?:[ ]?(?P<value>.*))?$")
LITERAL_NAMES = {"code-block", "sourcecode", "parsed-literal", "literalinclude"}


def _offsets(lines: list[str]) -> list[int]:
    result = [0]
    total = 0
    for line in lines:
        total += len(line.encode("utf-8"))
        result.append(total)
    return result


def scan_rst(path: str, content: str, supported: set[str]) -> dict[str, Any]:
    encoded = content.encode("utf-8")
    lines = content.splitlines(keepends=True)
    offsets = _offsets(lines)
    directives: list[dict[str, Any]] = []
    opaque_until_indent: int | None = None
    index = 0
    while index < len(lines):
        raw = lines[index].rstrip("\r\n")
        stripped = raw.lstrip(" ")
        indent = len(raw) - len(stripped)
        if opaque_until_indent is not None:
            if stripped and indent <= opaque_until_indent:
                opaque_until_indent = None
            else:
                index += 1
                continue
        match = DIRECTIVE.match(raw)
        if not match:
            index += 1
            continue
        name = match.group("name")
        base_indent = len(match.group("indent"))
        end = index + 1
        while end < len(lines):
            candidate = lines[end].rstrip("\r\n")
            if not candidate.strip():
                end += 1
                continue
            candidate_indent = len(candidate) - len(candidate.lstrip(" "))
            if candidate_indent <= base_indent:
                break
            end += 1
        if name in LITERAL_NAMES:
            opaque_until_indent = base_indent
            index = end
            continue
        if name not in supported:
            index = end
            continue
        options: list[dict[str, Any]] = []
        seen: set[str] = set()
        cursor = index + 1
        while cursor < end:
            option_raw = lines[cursor].rstrip("\r\n")
            if not option_raw.strip():
                cursor += 1
                continue
            option_match = OPTION.match(option_raw)
            if not option_match:
                break
            option_name = option_match.group("name")
            if option_name in seen:
                raise ArtifactSemanticError(
                    "DIRECTIVE_DUPLICATE_OPTION",
                    f"Duplicate option {option_name!r} in {path}:{index + 1}",
                    findings=[
                        finding(
                            "DIRECTIVE_DUPLICATE_OPTION",
                            "Duplicate directive option",
                            path,
                            option_name,
                        )
                    ],
                )
            seen.add(option_name)
            options.append(
                {
                    "name": option_name,
                    "value": option_match.group("value") or "",
                    "start_byte": offsets[cursor],
                    "end_byte": offsets[cursor + 1],
                    "line": cursor + 1,
                    "raw": lines[cursor],
                }
            )
            cursor += 1
        start_byte = offsets[index]
        end_byte = offsets[end]
        content_start = offsets[cursor]
        raw_bytes = encoded[start_byte:end_byte]
        option_map = {item["name"]: item["value"] for item in options}
        directives.append(
            {
                "name": name,
                "title": match.group("title") or "",
                "start_byte": start_byte,
                "end_byte": end_byte,
                "start_line": index + 1,
                "end_line": end,
                "indent": base_indent,
                "options": options,
                "option_values": option_map,
                "content_start_byte": content_start,
                "content": encoded[content_start:end_byte].decode("utf-8"),
                "original_digest": hashlib.sha256(raw_bytes).hexdigest(),
                "path": path,
                "native_id": option_map.get("id"),
                "native_version": option_map.get("version", "1"),
            }
        )
        index = end
    if len(directives) > 100_000:
        raise InputError("ENTITY_LIMIT", "RST directive count exceeds limit")
    return {
        "path": path,
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "newline": "crlf" if "\r\n" in content else "lf",
        "directives": directives,
    }
