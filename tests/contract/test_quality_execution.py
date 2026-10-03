"""Actual bounded process capture and fail-closed native diagnostics."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

import pytest

from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.models import Budget, execute, load_inputs
from score_sw_fabric.quality.native_outputs import diagnostics
from score_sw_fabric.quality.source_includes import include_directives
from tests.quality_support import complementary_request, ref, request


def source_request(tmp_path: Path, adapter: str, source: str) -> Path:
    path = (
        request(tmp_path) if adapter == "clang-tidy" else complementary_request(tmp_path, adapter)
    )
    selected = tmp_path / "component/check.cpp"
    selected.write_text(source)
    value = json.loads(path.read_text())
    value["files"] = [{**ref(selected), "path": "check.cpp"}]
    path.write_text(json.dumps(value))
    return path


@pytest.mark.parametrize("adapter", ["clang-tidy", "cppcheck", "asan", "ubsan"])
@pytest.mark.parametrize(
    "directive",
    [
        '#/**/include "/tmp/unselected.h"',
        '#inc\\\nlude "/tmp/unselected.h"',
        '#include /* continued\ncomment */ "/tmp/unselected.h"',
        '%:include "/tmp/unselected.h"',
        '#import "/tmp/unselected.h"',
        "#include " + "\\" + '\n            "../unselected.h"',
        '#include "/tmp/unselected.h" extra_tokens',
        "/**/ " * 100 + '#include "/tmp/unselected.h"',
        '\ufeff#include "/tmp/unselected.h"',
        "#inc" + "\\" + ' \t\r\nlude "/tmp/unselected.h"',
    ],
)
def test_obscured_external_include_rejected_before_execution(
    tmp_path: Path, adapter: str, directive: str
) -> None:
    path = source_request(tmp_path, adapter, directive + "\nint main() { return 0; }\n")
    with pytest.raises(InputError):
        load_inputs(path, "run", adapter)


@pytest.mark.parametrize(
    "directive",
    [
        '#/**/include "missing.h"',
        '#inc\\\nlude "missing.h"',
        '#include /* continued\ncomment */ "missing.h"',
        '%:include "missing.h"',
        '#import "missing.h"',
    ],
)
def test_obscured_unselected_local_include_blocks_adequacy(tmp_path: Path, directive: str) -> None:
    path = source_request(tmp_path, "clang-tidy", directive + "\nint main() { return 0; }\n")
    assert "UNDECLARED_LOCAL_INCLUDE" in load_inputs(path, "run").gaps


@pytest.mark.parametrize(
    "directive, gap",
    [
        ("#/**/include HEADER", "DYNAMIC_INCLUDE_UNKNOWN"),
        ("#inc\\\nlude HEADER", "DYNAMIC_INCLUDE_UNKNOWN"),
        ('#/**/include_next "check.cpp"', "INCLUDE_NEXT_UNSUPPORTED"),
        ('%:include_next "check.cpp"', "INCLUDE_NEXT_UNSUPPORTED"),
        ('#import "check.cpp"', "IMPORT_UNSUPPORTED"),
    ],
)
def test_obscured_dynamic_or_extension_include_remains_explicit(
    tmp_path: Path, directive: str, gap: str
) -> None:
    path = source_request(tmp_path, "clang-tidy", directive + "\nint main() { return 0; }\n")
    assert gap in load_inputs(path, "run").gaps


def test_include_text_in_literals_or_comments_is_not_a_dependency(tmp_path: Path) -> None:
    source = """/* #include "/tmp/not-a-dependency.h" */
auto text = R"tag(
#include "/tmp/not-a-dependency.h"
)tag";
auto character = '#';
auto string = "// /* #include /tmp/not-a-dependency.h";
// #include "/tmp/not-a-dependency.h"
int main() { return 0; }
"""
    selected = load_inputs(source_request(tmp_path, "clang-tidy", source), "run")
    assert selected.gaps == []


def test_literal_angle_header_keeps_comment_characters_and_following_directive() -> None:
    source = b"/**/ " * 100 + (b'#include <dir/*header.h>\n#include "/tmp/unselected.h"\n')
    assert list(include_directives(source)) == [
        ("include", "<", "dir/*header.h"),
        ("include", '"', "/tmp/unselected.h"),
    ]


def test_comments_after_literal_and_inside_quoted_header() -> None:
    assert list(include_directives(b'#include "dir//header.h" /* note */\n')) == [
        ("include", '"', "dir//header.h")
    ]
    assert list(include_directives(b'#include "header.h" extra\n')) == [
        ("include", '"', "header.h"),
        ("include", None, None),
    ]


def test_commented_or_raw_string_continuations_cannot_create_a_directive() -> None:
    assert list(
        include_directives(
            b'// continued\\\n#include "/tmp/unselected.h"\n'
            b'auto text = u8R"tag(/*\n#include "/tmp/unselected.h"\n*/)tag";\n'
            b'#include "selected.h"\n'
        )
    ) == [("include", '"', "selected.h")]


def test_output_prefix_full_digest_and_timeout(tmp_path: Path) -> None:
    data = b"x" * 20000
    phase = execute(
        "loud",
        [sys.executable, "-c", "import sys;sys.stdout.write('x'*20000)"],
        tmp_path,
        5,
        Budget(1024),
        {},
    )
    raw = phase["stdout"]
    assert raw["bytes"] == len(data) and raw["truncated"]
    assert base64.b64decode(raw["base64"]) == data[:1024]
    assert raw["sha256"] == hashlib.sha256(data).hexdigest()
    phase = execute(
        "timeout",
        [sys.executable, "-c", "import time;time.sleep(10)"],
        tmp_path,
        1,
        Budget(1024),
        {},
    )
    assert phase["timed_out"] and phase["exit_code"] is not None


def test_native_duplicate_keys_and_unselected_path(tmp_path: Path) -> None:
    with pytest.raises(InputError):
        diagnostics(b"Diagnostics: []\nDiagnostics: []", "a", tmp_path, {"check.cpp": b"x"})
    with pytest.raises(InputError):
        diagnostics(
            b"Diagnostics:\n- DiagnosticName: x\n  Level: Warning\n"
            b"  DiagnosticMessage: {Message: x, FilePath: /other/x.cpp, FileOffset: 0}\n",
            "a",
            tmp_path,
            {"check.cpp": b"x"},
        )
