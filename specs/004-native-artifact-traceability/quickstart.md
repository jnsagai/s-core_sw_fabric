# Quickstart: validate native artifact traceability

This is the planned acceptance flow for increment 004 after implementation. It operates only on
checked-in licensed fixtures and disposable native build directories. It does not edit a protected
S-CORE checkout or establish engineering acceptance.

## Prerequisites

- Python 3.12 environment from the frozen project lock.
- Pinned Bazel 8.7.0/Bazelisk 1.29.0 available through `SCORE_BAZEL_BIN`.
- Locked native dependency graph for docs-as-code 8.2.0, process-description 2.1.2, and Python 3.12.
- Fixture source/template hashes matching the selected native artifact profile.
- At least 15 GiB free disposable storage for a cold native dependency/build cache. Reuse of a
  verified cache is allowed; build outputs never live in reference checkouts.

The fixture artifact and trace profiles retain fixture-only authority. They cannot be used to claim
production approval.

## 1. Inspect the representative native snapshot

~~~bash
uv run --frozen score-fabric artifact index \
  --request tests/fixtures/artifacts/component/index-request.yaml \
  --out tests/fixtures/artifacts/out/component-index.json \
  --json
~~~

Expected result: exit 0. The index contains one native document wrapper plus its live contained
needs, exact status/type/relation/source locations, and a successful fresh-export reconciliation.
Example FMEA/DFA directives inside `code-block:: rst` remain opaque and absent from live need counts.
All six later capability fields are `not_evaluated`.

Repeat the deterministic fixture checks for `feature` and `analysis`. Final acceptance also
runs `tests/integration/test_artifact_native.py` with `SCORE_BAZEL_BIN` and
`SCORE_NATIVE_MODULE_ROOT` so the exact locked `needs_json` and `docs_check` commands execute
in a disposable workspace.

## 2. Generate a template-based candidate

~~~bash
uv run --frozen score-fabric artifact candidate \
  --request tests/fixtures/artifacts/analysis/create-request.yaml \
  --out tests/fixtures/artifacts/out/analysis-candidate.json \
  --json
~~~

Expected result: exit 0. The sealed overlay contains the complete new/changed RST bytes, binds every
unchanged base file, cites the exact module-template/metamodel/plan/package/profile sources, passes
native build/export plus fabric checks, and has no production apply side effect.

Validate it independently:

~~~bash
uv run --frozen score-fabric artifact validate \
  --candidate tests/fixtures/artifacts/out/analysis-candidate.json \
  --profile profiles/s_core_native_artifacts_v1.yaml \
  --json
~~~

Expected result: exit 0 with matching candidate/source-set identity.

## 3. Prove scoped-update preservation

~~~bash
uv run --frozen score-fabric artifact candidate \
  --request tests/fixtures/artifacts/component/update-request.yaml \
  --out tests/fixtures/artifacts/out/component-candidate.json \
  --json
~~~

Expected result: exit 0. The requested option/content/link span changes; unrelated prose, comments,
IDs, manual decisions, containment, and trace links retain their preimage bytes. Re-indexing the
materialized candidate agrees with the fresh native export.

A stale preimage, out-of-scope field, wrapper status copied into a child type, changed comment, or
unresolved placeholder returns exit 1 and preserves the previous candidate.

## 4. Check expected-obligation coverage

~~~bash
uv run --frozen score-fabric artifact trace \
  --request tests/fixtures/artifacts/component/trace-request.yaml \
  --out tests/fixtures/artifacts/out/component-trace.json \
  --json
~~~

Expected result: exit 0. Each metric shows literal numerator and denominator IDs, exclusions,
partial/unresolved/mismatched items, exact source refs, allocation and verification paths, and zero
unclassified package outputs.

Run the missing-obligation fixture:

~~~bash
uv run --frozen score-fabric artifact trace \
  --request tests/fixtures/artifacts/invalid/missing-verification/missing-verification-request.yaml \
  --out tests/fixtures/artifacts/out/missing-verification-trace.json \
  --json
~~~

Expected result: exit 1 and a published blocked report with `TRACE_UNRESOLVED`. The removed need
or link remains in the expected denominator. A wrong relation direction/type and an entirely absent
expected artifact likewise fail instead of improving coverage.

## 5. Review semantic changes and direct drift

~~~bash
uv run --frozen score-fabric artifact diff \
  --before tests/fixtures/artifacts/component/before-candidate.json \
  --after tests/fixtures/artifacts/out/component-candidate.json \
  --profile profiles/s_core_native_artifacts_v1.yaml \
  --json

uv run --frozen score-fabric artifact drift \
  --candidate tests/fixtures/artifacts/out/component-candidate.json \
  --profile profiles/s_core_native_artifacts_v1.yaml \
  --request tests/fixtures/artifacts/component/update-request.yaml \
  --json
~~~

Expected result: diff exits 1 when the reviewed semantic change exists and reports only its expected
categories; drift exits 0 and reports `clean: true`. After directly editing candidate content or a
nested digest, drift exits 1 with `GENERATED_DRIFT`; it does not offer an accept/repair route.

## 6. Exercise conservative impact

Use the fixture mutations for a requirement, interface, allocation, assumption, analysis input,
template, and native metamodel. Each expected affected subject/review appears through native reverse
links or a cited conservative rule. A new unlinked interface and an unknown external dependency
expand scope or produce `IMPACT_UNLINKED`/`IMPACT_UNKNOWN`; neither yields an empty impact set.

## 7. Run the complete verification set

~~~bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
SCORE_BAZEL_BIN=/path/to/bazel-8.7.0 SCORE_NATIVE_MODULE_ROOT=/path/to/disposable-module-template \
  uv run --frozen pytest -q
uv run --frozen python scripts/check_foundation.py
uv build --offline
~~~

Acceptance additionally requires non-skipped real native feature/component/analysis integration,
relocation and set-order equivalence, exact-maximum and one-over-limit cases, and recorded hashes,
elapsed time, peak package size, tool identities, logs, limitations, and FAB-016–FAB-018 mapping.

## Expected boundary

Successful results prove deterministic native structure/build compatibility, scoped-edit
preservation, source binding, trace coverage, and impact reporting for the supported profile. They
do not prove requirement correctness, test adequacy, mitigation effectiveness, evidence trust,
human approval, engineering readiness, release, deployment, workflow registration, or execution.
