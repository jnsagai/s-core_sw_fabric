# Source include selection validation

2026-10-01. Follow-up to the user's continuation of increment 010, covering the shared
source-selection portions of T007/T010 and requirements 010-R02/R03/R06/R11.

## Measured defect and correction

The original physical-line regex missed literal includes whose directive contained comments,
continued lines or the `%:` spelling. Native `import` extensions were also absent from the
selection check. Conversely, an apparent directive inside a raw string was treated as a real
dependency. The negative-first checkpoint retained [35 failing cases and two passing cases](
evidence/include-confinement-before.txt). Those cases used local fixture selections; no fixture
result is native readiness evidence.

The shared check now projects logical directives while preserving selected source bytes. It
handles comment replacement, continued lines, literal header names, comments/string literals
and directive spellings. Literal absolute/traversal paths fail before native execution, including
operands with extra tokens. Unknown macro operands, missing quoted selections, `include_next`
and `import` remain explicit adequacy gaps. Header contents that resemble comments remain
literal. Directive results are streamed.

The transformation order and GNU continued-line behavior were checked against the selected
compiler's [GCC 11.4 initial processing documentation](
https://gcc.gnu.org/onlinedocs/gcc-11.4.0/cpp/Initial-processing.html).
This inspection is conservative: conditional branches and unusual literal spellings can be
rejected or left unknown. It does not evaluate macros, enumerate compiler-generated dependencies,
qualify host system headers, execute hooks or establish full target CodeQL source closure.

## Verification

The retained [intermediate focused checkpoint](evidence/include-confinement-after.txt) passed
175 checks. The [final focused checkpoint](evidence/include-confinement-final.txt) passes
**175 checks in 18.88 seconds** and covers shared
execution/input/control checks, complementary requests and CodeQL prerequisite requests, plus
genuine Clang-Tidy integration. Five genuine selected-header cases exercise ordinary includes,
comments, continued keywords, multiline comments and `%:` directives. Each retains the native
null-dereference finding at the selected header and checks original source/header bytes remain
unchanged. Local results remain unprotected and engineering readiness stays not evaluated.

Ruff and formatting pass, mypy passes for 117 source files, foundation
consistency passes, and the offline source distribution/wheel build passes. Prior logs and
sealed records remain unchanged; no native analyzer settings, source locks or original profile
selection hashes were changed for this correction.

Commands:

```bash
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen pytest tests/contract/test_quality_execution.py tests/contract/test_quality_contracts.py tests/contract/test_quality_controls.py tests/contract/test_quality_complementary.py tests/contract/test_quality_codeql.py tests/integration/test_quality_tools.py -q --tb=short
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen ruff check .
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen ruff format --check .
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen mypy src scripts/verify_asan_host_records.py
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen python scripts/check_foundation.py
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv build --offline
```

This focused follow-up does not repeat the complete host suite. Its prior
[1773 passed / 13 skipped checkpoint](asan-host-validation.md) remains historical host evidence.
Restricted agent ASan runtime remains incompatible. The full target execution, generated-input
closure, CodeQL eligibility and human reviews remain open. Task count stays **77/88 complete**.
