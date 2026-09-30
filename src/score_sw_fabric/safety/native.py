"""Native S-CORE needs and list-table applicability rows, read with the 004 RST scanner."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from score_sw_fabric.artifacts.rst import scan_rst
from score_sw_fabric.process_source.reader import InputError

ROW_START = re.compile(r"^(?P<indent>\s*)\* - ?(?P<text>.*)$")
CELL_START = re.compile(r"^(?P<indent>\s*)- ?(?P<text>.*)$")
PLACEHOLDER = re.compile(r"<[^<>\n]*>")
LINK_SPLIT = re.compile(r"[,\s]+")
MAX_ROWS = 10_000


def list_table_rows(content: str, header_rows: int = 1) -> list[dict[str, Any]]:
    """Parse a list-table body into rows of cells, keeping each row's relative line."""
    rows: list[dict[str, Any]] = []
    for offset, line in enumerate(content.splitlines()):
        if not line.strip():
            continue
        row = ROW_START.match(line)
        if row:
            rows.append({"line": offset, "cells": [row.group("text").strip()]})
            continue
        cell = CELL_START.match(line)
        if cell and rows:
            rows[-1]["cells"].append(cell.group("text").strip())
        elif rows:
            rows[-1]["cells"][-1] = (rows[-1]["cells"][-1] + " " + line.strip()).strip()
        if len(rows) > MAX_ROWS:
            raise InputError("ENTITY_LIMIT", "List-table row limit exceeded")
    return rows[header_rows:]


def links(value: str) -> list[str]:
    return [item for item in LINK_SPLIT.split(value.strip()) if item]


@dataclass
class NativeSet:
    """Needs and applicability rows from one set of native files."""

    needs: dict[str, dict[str, Any]] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)


def read_native(files: list[tuple[str, bytes, str]], directives: set[str]) -> NativeSet:
    """Scan native RST files; list-tables are read only from `analysis` files."""
    result = NativeSet()
    for path, data, role in files:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InputError("NATIVE_ENCODING", f"Native file is not UTF-8: {path}") from exc
        scanned = scan_rst(path, text, directives | {"document", "list-table"})
        for directive in scanned["directives"]:
            name = directive["name"]
            options = directive["option_values"]
            if name == "list-table":
                if role != "analysis":
                    continue
                header = options.get("header-rows", "1").strip()
                if not header.isdigit():
                    raise InputError("LIST_TABLE_FORMAT", f"Invalid header-rows in {path}")
                table = list_table_rows(directive["content"], 0)
                if int(header) != 1 or not table:
                    continue
                names = table[0]["cells"]
                for row in table[1:]:
                    result.rows.append(
                        {
                            "path": path,
                            "table": directive["title"],
                            "line": directive["start_line"] + row["line"],
                            "columns": dict(zip(names, row["cells"], strict=False)),
                            "complete": len(row["cells"]) == len(names),
                        }
                    )
                continue
            record = {
                "id": directive["native_id"],
                "type": name,
                "title": directive["title"],
                "path": path,
                "role": role,
                "line": directive["start_line"],
                "digest": directive["original_digest"],
                "options": dict(options),
                "content": directive["content"].strip(),
            }
            if name == "document":
                result.documents.append(record)
            if not record["id"]:
                continue
            if record["id"] in result.needs:
                result.duplicates.append(record["id"])
                continue
            result.needs[record["id"]] = record
    return result
