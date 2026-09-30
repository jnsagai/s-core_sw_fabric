# 003 validation guide

Status: implemented and validated on 2026-09-28.
Increment 003 is complete only after the representative packages pass the fabric validator and
a real native validator matching the pinned profile. No command in this guide registers or runs
a workflow.

## Prerequisites

- Python >=3.12 and the repository's frozen `uv` environment.
- A complete, sealed 002 plan whose selected execution mapping has completed owner review.
- A Fabro validator binary verified against commit
  `1b4fb15281ebb724426f9e480dce48d0100ff79b`.
- The checked-in compiler and validator profiles and their declared source hashes.

Set the validator path only to a binary that the profile identity check can accept:

```bash
export SCORE_FABRO_BIN=/absolute/path/to/fabro
```

Do not point the tests at a production settings directory. The integration helper creates an
isolated configuration and disposable package tree.

## Compile a representative package

```bash
uv run --frozen score-fabric workflow compile \
  --request tests/fixtures/compiler/linear/request.yaml \
  --out tests/fixtures/compiler/linear/out/package.json \
  --json
```

Expected result: exit 0 and one canonical JSON package. Its report says semantic validation and
the profiled native validation passed. It also says registration, execution, trusted evidence,
human acceptance, engineering readiness, release, and deployment are `not_evaluated`.

Inspect the package without extracting mutable files:

```bash
uv run --frozen python -m json.tool tests/fixtures/compiler/linear/out/package.json
```

The package contains `entrypoint`, `files`, a semantic manifest, complete source map, compile
report, semantic validation result, native validation receipt, and self-digest. Every native file
path is relative and listed in the manifest.

## Revalidate without publication

```bash
uv run --frozen score-fabric workflow validate \
  --package tests/fixtures/compiler/linear/out/package.json \
  --validator profiles/fabro-conformance-1b4fb152-v1.yaml \
  --json
```

Expected result: exit 0, no output package modification, and a bounded receipt. Validation runs
against a fresh disposable materialization and does not register or execute the workflow.

## Prove deterministic compilation

Compile the relocation and set-order variants:

```bash
uv run --frozen score-fabric workflow compile \
  --request tests/fixtures/compiler/linear-relocated/request.yaml \
  --out /tmp/s-core-003/linear-relocated.json \
  --json

cmp tests/fixtures/compiler/linear/out/package.json /tmp/s-core-003/linear-relocated.json
```

Expected result: both compiles exit 0 and `cmp` reports no difference. Operational request paths,
temporary validator paths, and set-like input order do not affect bytes or package identity.

## Review a semantic change

```bash
uv run --frozen score-fabric workflow diff \
  --before tests/fixtures/compiler/linear/out/package.json \
  --after PATH/TO/reviewed-change.package.json \
  --profile profiles/deterministic-compiler-v1.yaml \
  --json
```

Expected result: exit 1 with a change in `permission`, the affected logical node, and its source
origins. Unrelated categories have zero changes. Comparing identical packages exits 0.

## Detect direct generated-output drift

Use a disposable copy, modify one `files` value, then run:

```bash
uv run --frozen score-fabric workflow drift \
  --request tests/fixtures/compiler/linear/request.yaml \
  --package PATH/TO/edited-package.json \
  --profile profiles/deterministic-compiler-v1.yaml \
  --json
```

Expected result: exit 1 with the changed logical path and expected/actual digest. The command does
not repair or reseal the file. Regenerate from reviewed source to produce a new package.

## Required representative native cases

The integration suite must compile and validate all three:

| Case | Required behavior |
| --- | --- |
| Linear obligations | Dependency ordering comes only from reviewed mapping; each action and edge is source-mapped |
| Shared parallel review | Agreeing gate tuple deduplicates once; parallel branches join through complete mandatory fan-in |
| Bounded correction feedback | Retry/feedback retains positive limit and explicit exhausted failure destination |

Run them with the matching real validator:

```bash
SCORE_FABRO_BIN="$SCORE_FABRO_BIN" \
  uv run --frozen pytest -q tests/integration/test_workflow_compiler_native.py
```

An unset validator may produce an explicit local skip while implementation is in progress, but
the 003 acceptance record cannot mark SC003-03 complete from a skipped run.

## Required rejection cases

The contract suite mutates one valid fixture at a time. Each case must exit 1 with a stable finding
and preserve a byte-for-byte sentinel already present at `--out`:

- required human gate removed or bypassed;
- fallible node missing failure, blocked, timeout, unknown, malformed, infrastructure, or exhausted
  routing required by its type;
- zero, negative, missing, or above-profile retry/visit bound;
- cycle without an explicit exhausted destination;
- dangling or unreachable node/edge;
- empty, mismatched, or partial mandatory fan-in;
- missing, unknown, unlimited, zero where positive is required, or above-profile action paths,
  data destinations, model-capability bindings, wall-time/attempt/tool-call/token/cost budgets;
- a deterministic check that selects a model or renders as anything other than native `command`;
- automatic approval, replayed approval, approval credentials, or success timeout default;
- mapping gap, conflict, unreviewed rule, missing origin, or unsupported action type;
- undeclared, absent, extra, case-colliding, traversing, absolute, oversized, or digest-mismatched
  native file;
- blocked/incomplete/tampered 002 plan or mismatched compiler/validator profile;
- syntactically native-valid graph that violates a stricter fabric semantic invariant.

Malformed YAML/JSON, validator identity mismatch/unavailability, unsafe output aliases, or invalid
schema/version exit 2 and likewise preserve the sentinel.

## Bounds cases

Version 1 verifies these maximums and one-over-limit failures:

| Boundary | Maximum |
| --- | ---: |
| Each selected input | 64 MiB |
| Plan instances | 10,000 |
| Plan dependencies | 100,000 |
| Execution mapping rules | 50,000 |
| IR nodes | 50,000 |
| IR edges | 200,000 |
| Cyclic components | 10,000 |
| Native files | 512 |
| One native file | 512 KiB |
| Total native source text | 2 MiB |
| Canonical package | 64 MiB |
| Per-action execution budgets | Exact finite compiler-profile ceilings |

Each structural and byte boundary receives an exact-maximum passing case and a one-over-limit
failure with a stable diagnostic. The combined representative maximum case records elapsed time
and peak package size in acceptance evidence. It establishes bounded deterministic completion on
the test platform, not a general latency service-level claim.

## Repository validation

Run the focused suite:

```bash
uv run --frozen pytest -q \
  tests/contract/test_compiler_inputs.py \
  tests/contract/test_compiler_ir.py \
  tests/contract/test_compiler_graph_semantics.py \
  tests/contract/test_compiler_rendering.py \
  tests/contract/test_compiler_package.py \
  tests/contract/test_compiler_diff_drift.py \
  tests/contract/test_compiler_cli.py \
  tests/integration/test_workflow_compiler.py
```

Then run the complete repository checks:

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
uv run --frozen pytest -q
uv run --frozen python scripts/check_foundation.py
uv build --offline
```

Finally run the real-validator integration separately with `SCORE_FABRO_BIN` set and record the
binary/profile identity and results in the 003 acceptance artifact.

See [compiler contract](contracts/compiler.md), [data model](data-model.md), and
[research decisions](research.md).
