# Quickstart

Run from the repository with Python >=3.12 and `uv sync --frozen`.

```sh
uv run --frozen score-fabric optimization evidence --root tests/fixtures --path optimization/sample.sarif --operation summary
uv run --frozen score-fabric optimization benchmark --output specs/011-change-impact-and-freshness/evidence/benchmark
uv run --frozen score-fabric optimization audit --root .
uv run --frozen pytest -q tests/contract/test_optimization_evidence.py tests/contract/test_optimization_context.py tests/contract/test_optimization_governor.py tests/integration/test_optimization_service.py
uv run --frozen ruff check .
uv run --frozen mypy src
uv run --frozen python scripts/check_foundation.py
uv build
```

The evidence CLI returns bounded normalized findings with raw checksum refs. For full regression,
set `SCORE_FABRO_BIN` to the previously validated pinned binary; required native compiler tests
must not skip. New scratch uses `score-fabric storage workspace` and volume bindings.
Use the bounded service only with its mandatory runtime guard. No model call is performed by
these commands. Live savings/owner acceptance stay pending in [acceptance](acceptance.md).

Opt-in context/governor requests use the new schemas in [the schema inventory](schemas/README.md).
The existing v1 requests retain their exact field sets. Supply native IDs and checksum references
from your measured indexes, reviewed role/model policy and current workspace; fixture identifiers
cannot qualify a real task. Use `optimization prepare|context|govern|classify|mode|skills --request FILE`
to derive records. The compiler adapter `narrow_projection` consumes these bindings before
`build_ir`, retains every command/human node and refuses agents in command-only modes.

Native conformance uses the pinned executable without runtime registration or model execution:

```sh
SCORE_FABRO_BIN=/home/jefferson/.local/share/s-core-tools/fabro-1b4fb152-agent32768/fabro uv run --frozen pytest -q tests/integration/test_workflow_compiler_native.py tests/integration/test_optimization_service.py
```

The default activation hook refuses live stages. Scoped qualification requires an operator
private instruction pinned through `guard --instruction FILE --instruction-sha256 SHA`,
exact native run/cwd binding and the bounded transport in
[the contract](contracts/optimization.md). These inputs are execution instructions for a
disposable experiment, not engineering acceptance or production authority. See the retained
[qualification](evidence/qualification/README.md) for source-derived configuration and results.
[Projection qualification](evidence/projection-qualification/README.md) records the separately
authorized second comparison; neither closed ledger may be reset or reused for more calls.
The ten-request experiment is closed; replay/projection creates no further provider calls.
