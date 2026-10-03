"""Inspect literal include selections without interpreting macros or executing source."""

from __future__ import annotations

import re
from collections.abc import Iterator
from io import StringIO

_TOKEN = re.compile(
    r"(?P<block>/\*)|(?P<line>//)"
    r'|(?P<raw>(?<!\w)(?:u8|u|U|L)?R"(?P<delimiter>[^ ()\\\t\n]{0,16})\()'
    r'|(?P<quoted>"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\')'
    r"|(?P<angle><)"
)
_HEADER_PREFIX = re.compile(r"^\s*(?:#|%:)\s*(?:include|include_next|import)\s*$")
_DIRECTIVE = re.compile(
    r"^[ \t\v\f]*(?:#|%:)[ \t\v\f]*(include_next|include|import)\b([^\n]*)", re.M
)


def include_directives(data: bytes) -> Iterator[tuple[str, str | None, str | None]]:
    """Return (directive, delimiter, target); unknown macro operands stay explicitly unknown.

    The projection merges continued lines and replaces comments with spaces. Literal
    contents are preserved for header names; raw string bodies cannot introduce directives.
    This is a selection check, not a compiler dependency graph or system-header qualification.
    """
    text = data.decode("utf-8", "replace").removeprefix("\ufeff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\\[ \t\v\f]*\n", "", text)
    projection = StringIO()
    prefix = ""

    def append(value: str) -> None:
        nonlocal prefix
        projection.write(value)
        if "\n" in value:
            prefix = ""
            value = value.rsplit("\n", 1)[1]
        # Only an initial directive prefix can open a literal <header>. Bound this
        # state even for long physical lines; legal directive prefixes remain short
        # after whitespace compression. The complete text stays in projection.
        compressed = re.sub(r"[ \t\v\f]+", " ", value)
        prefix = re.sub(r"[ \t\v\f]+", " ", prefix + compressed)[:64]

    cursor = 0
    while match := _TOKEN.search(text, cursor):
        append(text[cursor : match.start()])
        cursor = match.end()
        if match.lastgroup == "block":
            end = text.find("*/", cursor)
            cursor = len(text) if end == -1 else end + 2
            append(" ")
        elif match.lastgroup == "line":
            end = text.find("\n", cursor)
            cursor = len(text) if end == -1 else end
            append(" ")
        elif match.group("raw") is not None:
            ending = ")" + match["delimiter"] + '"'
            end = text.find(ending, cursor)
            cursor = len(text) if end == -1 else end + len(ending)
            append('""')
        elif match.lastgroup == "angle" and _HEADER_PREFIX.fullmatch(prefix):
            end = text.find(">", cursor)
            newline = text.find("\n", cursor)
            if end != -1 and (newline == -1 or end < newline):
                append(text[match.start() : end + 1])
                cursor = end + 1
            else:
                append("<")
        else:
            append(match[0])
    append(text[cursor:])
    for match in _DIRECTIVE.finditer(projection.getvalue()):
        operand = match[2].strip()
        literal = re.match(r'(?:"([^"\n]*)"|<([^>\n]*)>)', operand)
        if literal is None:
            yield match[1], None, None
        else:
            target = literal[1] if literal[1] is not None else literal[2]
            yield match[1], '"' if literal[1] is not None else "<", target
            if operand[literal.end() :].strip():
                yield match[1], None, None
