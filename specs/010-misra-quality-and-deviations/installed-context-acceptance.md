# T001 candidate installed-context validation

2026-10-01. This records implemented profile consolidation and deterministic checks.
Engineering acceptance and human-owned T032/T082 remain pending.

## Implemented boundary

[Exact contract](contracts/installed-context.md),
[pure validator](../../src/score_sw_fabric/quality/installed_context.py) and
[schema](../../schemas/quality-installed-context.schema.json) add a strict optional context
to the existing version 1 profile. Four candidate toolchain snapshots retain declared versions,
original executable/dependency identities and complete original notices. The selected compiled
CodeQL pack retains manifest/metadata/observation identities and reviewed versus declared build
commits with measured tree equality. The five original notices total 89,585 bytes.

Qualification and project-use eligibility stay `unknown`; compiled/library provenance stays
`unverified`; reporting stays `unexecuted`. Snapshot paths are labels during pure replay. No
tool is selected, analyzer executed, licensed use authorized or engineering decision accepted
by this context. Native policy source pins, IDs/statuses and unknown mapping/categories remain.

## Original and current policy identities

| Profile | SHA-256 |
| --- | --- |
| [Retained original](../../tests/fixtures/quality/profiles/s-core-quality-legacy-v1.yaml) | `720a64d14ecc193e034a45e3c68dffed27df1d23837b886268af55acd1413ec9` |
| [Current primary](../../profiles/s-core-quality-v1.yaml) | `c15507fb7047ccc45bb8a830f2af686879b9c38507e4589b65b1ed275ca3dd39` |

Current examples select the current SHA. The fixture native-import example explicitly selects
the retained original profile, matching its unchanged original artifact bindings. Historical
records, source transport hashes and immutable legacy packet bytes are preserved.

The same-policy imported-contributor test now explicitly selects its original profile. A
separate policy-transition test proves current selection produces `stale`/`POLICY_CHANGED`,
retains all contributors and has no fresh run. Neither path proves correction or acceptance.

## Verification

- Sixteen contract cases pass, including malformed/promoted context, full notice-byte/hash,
  duplicate identity, source/build relation and byte-exact legacy checks. Valid pure context
  loading forbids host reads/probes.
- Combined parser/context/packet checkpoint: **246 passed, 48.75 seconds**.
- Focused original/current imported-policy checks: **2 passed, 4 deselected, 1.02 seconds**.
- Current and original profiles plus all three current CLI outputs validate against their local
  Draft 2020-12 schemas with format checking. All references resolve from local schema files.
- The retained current packet reproduces with `Path.open` and `Path.stat` forbidden.

The public CLI example pipeline preserves its original origins and outcomes:

| Operation | Exit | Retained output |
| --- | --- | --- |
| Fixture import | 1 | Temporary fixture output; not eligible |
| Coverage | 1 | [Current matrix](evidence/coverage-installed-context.json), incomplete |
| Packet | 0 | [Current packet](evidence/packet-installed-context.json), structurally complete |
| Assessment | 1 | [Current assessment](evidence/assessment-installed-context.json), blocked, zero accepted claims |

A fresh actual read-only prerequisite inspection also uses the current profile and returns
exit 1 / `unavailable`, `not_eligible`, zero accepted claims and the same fourteen gaps.
[Original inventory](evidence/codeql-prerequisites-installed-context.json) has digest
`3861be36eb469cd0ef41e1a2f2b8316db45320c0d36c011bbee315735f98c963` and validates against
its local schema. Only bounded read-only Git/file inspection occurs; no CodeQL/native-report
process runs. Previous inventories retain their exact original profile bytes.

Frozen sync (18 packages), Ruff/formatting (474 files), mypy (113 sources), foundation
consistency and offline sdist/wheel build pass. The build uses the existing byte-verified
pinned dependency cache and changes no dependency or native source lock.

The first broad run after consolidation finished with **1,680 passed, 11 skipped, four
failures**, 357.19 seconds. Three are the known restricted native ASan failures; the fourth
was the test comparing a legacy import with a changed policy while expecting same-policy
pending status. Production correctly returned stale. Its intended same-policy selection was
fixed and a distinct changed-policy case added. The
[intermediate output](evidence/overnight-regression-installed-context-intermediate.txt) is
retained rather than presented as a passing gate.

The final broad run with the same documented native selectors finishes with **1,682 passed,
11 skipped and the three known ASan failures**, 358.60 seconds. Both policy cases pass in
that run. [Full original output](evidence/overnight-regression-installed-context.txt) retains
the failed native seed/fix, disposition and import cases. Native Fabro compiler tests remain
excluded because their pinned runtime is not selected; skips do not establish readiness.
The exact command is unchanged from [CodeQL validation](codeql-prerequisites-acceptance.md#verification).

T001 is complete; T030/T081, genuine CodeQL tasks and all human gates remain open.
