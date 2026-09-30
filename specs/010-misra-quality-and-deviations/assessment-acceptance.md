# Independent quality assessment implementation evidence

2026-10-01 (Lisbon). [Contract](contracts/assessment.md),
[authorized autonomous window](../../docs/handoff/010-overnight.md).

## Implemented scope

`quality assess` independently replays the selected portable packet, native import/extraction,
guideline matrix and fixture decision evidence. It retains original profile/packet/005 transports
and current source bytes, compares an explicitly selected current baseline, and reevaluates
fixture gate/decision validity at the requested time and domain. Offline selection leaves
BASELINE_FRESHNESS_UNKNOWN; archived path labels cannot establish current host state.

Every declared guideline remains an obligation, including missing rows, manual/audit/unsupported
and excluded states; an unknown denominator stays null. Current adequate complementary tool
observations can pass structurally while overall compliance is blocked. Historical/changed or
unknown-current analyses cannot be reused as current clean evidence. Retained findings stay
visible. A correction label without fresh matching retained output stays unresolved, and retained
local corrections are never upgraded to authenticated or newly executed analysis.

Supporting 005 originals must replay and include exact canonical packet bytes in their verified
file closure before their packet binding is exact. Current gate expiry/domain/subject failures,
conflicting signed IDs and reused receipt sequences stay named. These supporting decisions do
not adopt mappings or discharge manual reviews. Packet disposition decisions also reevaluate at
this assessment's current fixture as-of/domain. Source/tool/configuration/validity drift prevents
fixture reuse. All source/control/005 selections are refrozen before guarded atomic publication.

The supported profile remains unmapped with primary CodeQL execution/eligibility and protected
production authority unavailable. Thus every current overall fixture/production assessment is
blocked. Output pass/fail/blocked/not_evaluated types retain observation distinctions without
inventing an engineering pass. Every record has zero accepted claims, not_eligible, readiness
not_evaluated and untrusted requested time. T032, 009 T018 and 005 T009 remain human/external gates.

## Actual retained record

[Executed request](../../examples/quality/assessment-unknown.yaml),
[portable assessment](evidence/assessment-unknown.json).

```bash
uv run --frozen score-fabric quality assess --request examples/quality/assessment-unknown.yaml --out /tmp/quality-010-assessment.json --json
```

Exit 1 publishes a production-domain blocked record with null denominator, explicit current
fixture source bytes, no analyzer execution and zero accepted claims. CodeQL execution/use
eligibility, primary capability, mapping, manual review, tool confidence/current tool state and
protected production authority remain gaps. Original native statuses/licenses remain intact.
Independent verification of the saved assessment reproduces without original host files.

## Verification

- Focused contract/integration: 28 passed, 20.66 seconds. Actual seeded and clean Clang-Tidy
  observations remain distinct from synthetic 005 receipt/source fixtures. Current expiry,
  production-domain replay, exact/wrong packet binding, current config/source drift, invalid
  correction headers, portable offline verification, bounded controls, final refreezing,
  deterministic CLI and previous output protection are covered.
- Broad regression: `uv run --frozen pytest --ignore=tests/integration/test_workflow_compiler_native.py -q --tb=short`: **1382 passed, 11 skipped**, 193.82 seconds. The three existing native Fabro compiler tests remain excluded because the pinned runtime is not selected. Existing external/native skips cannot satisfy engineering readiness.
- `uv sync --frozen`: no dependency changes (18 existing packages).
- Ruff check/format, mypy (107 source files), foundation and build pass; final document/link gates also pass.
- Offline Draft 2020-12 schema validation with local references/format checking passes for the
  executed request and retained assessment. No schema dependency was added to the package.

Assessment originals/selected derived records/final output remain bounded at 96 MiB; controls
at 1 MiB, source selection at 500 files/64 MiB, supporting and disposition signed records at
20 total, plus existing depth/node limits. Native binaries are not executed or redistributed.
Reference repositories remain untouched. No human acceptance, automatic approval, paid call,
publishing, merge, release, deployment or 011 work occurred.
