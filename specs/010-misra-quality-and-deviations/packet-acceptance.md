# Portable quality packet implementation evidence

2026-09-30. [Contract](contracts/packet.md), [overnight scope](../../docs/handoff/010-overnight.md).

## Implemented observations

`quality packet` reads original, hash-bound selections without analyzer execution.
It retains current/prior imports and extraction, the full guideline matrix and source
records, local original outputs, immutable disposition history, selected fixture 005
assessment/context originals, explicit historical/current target source bytes and
license/notice originals. Every questionnaire answer is `pending_human`.

The offline verifier reads embedded originals. Native imports, extraction, matrix
transformations and current fixture decision validity reproduce independently. 005 replay
may materialize its embedded fixture in a fresh temporary directory; it opens no original
host path label and calls no analyzer. Selected native IDs/statuses and local/import/fixture
origins remain distinct. Seals cannot authenticate execution or engineering acceptance.

Explicit snapshot roots bind each encountered baseline's full digest and exact source file
hashes. A missing snapshot or unassociated notice makes the packet incomplete; mismatched
selected bytes refuse. Native truncation retains its original prefix/full-stream hash and
remains incomplete. Output guards and final refreezing preserve selected inputs and history.
The archive is bounded at 5000 files/64 MiB retained bytes, files at 16 MiB, final records
at 96 MiB with depth/node limits. Executable binaries are not redistributed.

The unchanged default profile has unknown MISRA mapping, category/applicability/manual
review, CodeQL eligibility/source/build/reporting and protected authority. A complete
portable packet can exit 0 while these engineering gaps remain. Every output has zero
accepted claims, `not_eligible`, and readiness `not_evaluated`.

## Actual retained example

[Request](../../examples/quality/packet-unknown.yaml) and
[portable original-byte record](evidence/packet-unknown.json): eleven original files,
complete structural closure, unknown guideline denominator, no analysis execution,
zero accepted claims and eight explicit review questions. Its baseline is an explicitly
synthetic source/CodeQL identity fixture; no CodeQL execution is implied. Native notice
references retain original licensed files, without deciding tool/project eligibility.

Executed command:

```bash
uv run --frozen score-fabric quality packet --request examples/quality/packet-unknown.yaml --out /tmp/quality-010-packet.json --json
```

Exit 0 emits the portable packet. RULE_MAPPING_UNKNOWN, GUIDELINE_DENOMINATOR_UNKNOWN,
MANUAL_REVIEW_PENDING, CODEQL_ELIGIBILITY_UNKNOWN, TOOL_CONFIDENCE_UNKNOWN and
PRODUCTION_AUTHORITY_UNAVAILABLE remain visible.

## Verification

- `uv sync --frozen`: 18 packages, no dependency changes.
- Packet tests cover genuine clean local analysis, a fresh correction with both source
  versions retained, exact fixture 005 replay, all linked history, missing snapshots/notices,
  source drift, tampered bytes/findings/questions, unsafe/duplicate/extra archive labels,
  output protection and deterministic CLI/refusal.
- Broad regression: `uv run --frozen pytest --ignore=tests/integration/test_workflow_compiler_native.py -q --tb=short`: **1354 passed, 11 skipped**, 173.97 seconds. The three existing 003 native Fabro compiler tests remain excluded because the pinned runtime is not selected; eleven existing external/native skips are not readiness evidence.
- Final packet tests: `uv run --frozen pytest tests/contract/test_quality_assessment.py tests/integration/test_quality_packet.py -q --tb=short`: **28 passed**, 8.83 seconds. The broad run includes the complete packet behavior and decision refactor; the final focused run additionally checks retention of supplied manifest origins.
- Ruff, mypy (106 source files), foundation consistency and source/wheel build pass;
  final documentation/link gates also pass.
- Offline Draft 2020-12 schemas validate the actual request and retained packet through
  local references; no schema dependency was added to the fabric environment.

Engineering review is pending. Compliance assessment and eligible real CodeQL execution
remain separate work. Human-owned T032 is unchecked. No source reference repository was
written or built in; no acceptance, paid call, publishing, merge or deployment occurred.
