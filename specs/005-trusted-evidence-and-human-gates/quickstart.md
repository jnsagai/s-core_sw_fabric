# Quickstart: validate trusted evidence and human gates

This runbook exercises the checked-in Increment 005 fixture-domain implementation. The fixture
inputs and CLI subcommands below exist and are covered by contract/integration tests. Fixture receipts
and keys exercise contract logic only. No fixture result grants production acceptance.

## Prerequisites

- Python >=3.12 and the frozen `uv.lock`, including the pinned public-key verification library.
- Sealed Increment 002 plan and Increment 004 candidate/report fixture closures.
- Version-1 assurance trust and gate policies with explicit `fixture_contract` domain.
- Test-only issuer public/private key pair in isolated fixture setup. The private test key is never
  accepted by a production trust profile; production private keys never enter this repository.
- Disposable output directory under the request's declared `output_root`.

All referenced contracts are in [assurance.md](contracts/assurance.md), with field and lifecycle
rules in [data-model.md](data-model.md). Run commands from the repository root.

## 1. Construct the exact subject

```bash
uv run --frozen score-fabric assurance subject   --request tests/fixtures/assurance/passing-scope/subject-request.yaml   --out tests/fixtures/assurance/passing-scope/out/subject.json   --json
```

Expected: exit 0. The subject binds the complete sealed plan, candidate, source baseline,
profile, native receipt and expected obligation IDs. The selected 004 candidate has no bound trace
report, so `TRACE_NOT_EVALUATED` remains explicit; a separate sealed but unbound 004 report is
rejected by the mutation test. A separate positive trace-bound closure is available:

```bash
uv run --frozen score-fabric assurance subject \
  --request tests/fixtures/assurance/traced-scope/subject-request.yaml \
  --out tests/fixtures/assurance/traced-scope/out/subject.json --json
```

That fixture uses a public 004 candidate with an explicitly requested trace profile and an attached
report over the candidate's edited native index. The subject builder recomputes report obligations
from the selected trace profile, plan, workflow package, and index. Its subject includes all eight
report obligation IDs plus the two 002 plan IDs, and has no `TRACE_NOT_EVALUATED` limitation.
The output is a derived manifest;
004 candidate/report capability fields remain `not_evaluated`. Tamper with one overlay byte, plan
digest, native receipt, report obligation or profile: exit 2 and the prior subject output remains
unchanged.

## 2. Classify and verify evidence origin

```bash
uv run --frozen score-fabric assurance evidence   --request tests/fixtures/assurance/passing-scope/evidence-request.yaml   --out tests/fixtures/assurance/passing-scope/out/evidence-result.json   --json
```

Expected: exit 0 for an intact test-signed `fixture_contract` protected-observation simulation,
with exact subject/tool/policy/raw-output bindings and an explicit fixture-domain label. A copied
fixture result submitted to a `production` request exits 1 with `DOMAIN_MISMATCH` or
`EVIDENCE_UNTRUSTED`, never eligible. Wrong signature, issuer key, result digest, scope, tool digest,
import chain, or absent raw bytes is rejected or blocked with a stable reason. Timeout and absent
measurements remain unknown, not clean or zero.

## 3. Verify an authenticated decision in its declared domain

```bash
uv run --frozen score-fabric assurance decision   --request tests/fixtures/assurance/passing-scope/decision-request.yaml   --out tests/fixtures/assurance/passing-scope/out/decision-result.json   --json
```

Expected: exit 0 for the test-domain receipt only when actor, role, issuer authority,
independence, subject, scope, rationale, conditions and validity match. Replace the signed payload
with a `claimed_actor` from the 002 decision-reference schema, a Fabro interview/replay answer, or
an agent-written approval-looking file: exit 1, with no authenticated human decision. Wrong scope,
expired role, failed independence, conflict, withdrawal, or unmet condition likewise prevents
eligibility.

## 4. Evaluate a complete scoped gate

```bash
uv run --frozen score-fabric assurance gate   --request tests/fixtures/assurance/passing-scope/gate-request.yaml   --out tests/fixtures/assurance/passing-scope/out/assessment.json   --json
```

Expected: exit 0 with `outcome: pass`, `assurance_domain: fixture_contract`, a non-empty expected
predicate list and one result per predicate. A complete gate over the trace-bound subject is also
available:

```bash
uv run --frozen score-fabric assurance gate \
  --request tests/fixtures/assurance/traced-scope/gate-request.yaml \
  --out tests/fixtures/assurance/traced-scope/out/passing-assessment.json --json
```

It evaluates all ten 002/004 obligation IDs through eleven predicates and exits 0 in the
fixture domain. The same subject with an incomplete three-predicate policy exits 2 with
`OBLIGATION_SET_INCOMPLETE` and preserves the previous assessment. This demonstrates the gate algorithm, not production
acceptance. For the same subject, run the blocked fixture:

```bash
uv run --frozen score-fabric assurance gate   --request tests/fixtures/assurance/blocked-scope/gate-request.yaml   --out tests/fixtures/assurance/blocked-scope/out/assessment.json   --json
```

Expected: exit 1 with `blocked`, exact missing/untrusted predicate IDs and required actions.
Remove all expected obligations or one mandatory review: no vacuous pass. Replace one eligible
measurement with a verified failed result: `fail` if all other mandatory predicates are resolved.
Combine that failure with a missing mandatory input: aggregate `blocked`, with the measured failure
preserved in the predicate matrix. An exact authenticated whole-gate tailoring decision yields
`not_applicable`; an unverified tailoring claim remains blocked.

## 5. Recheck freshness without rewriting history

Mutate exactly one binding at a time: candidate, report, source, process, template, metamodel,
validator, tool, policy, trust root, expected obligation, evidence, decision, condition or validity.
A prior gate result becomes stale or ineligible for current use and a new assessment explains the
affected subjects. The historical receipt and prior assessment bytes remain unchanged. A new
unlinked subject or unknown dependency expands review or blocks. An agent-selected earlier
`as_of` cannot revive expired production approval without a protected time receipt.

The checked-in [old/new fixture](../../tests/fixtures/assurance/no-impact-scope/README.md)
uses public 004 before/current candidates. Its old gate passes at 10:00 UTC. A signed
no-impact review at 10:30 UTC binds both subjects and policies and the exact changed paths;
the current gate at 11:00 UTC records the review but stays `stale` with `whole_gate`
scope because evaluation time advanced. Its freshness result retains the three 004 native
paths from the changed component requirement to the interface and test case. Regenerate
and replay it with:

```bash
uv run --frozen python -m tests.build_assurance_no_impact_fixture
uv run --frozen score-fabric assurance gate \
  --request tests/fixtures/assurance/no-impact-scope/current-gate-request.yaml \
  --out tests/fixtures/assurance/no-impact-scope/out/current-assessment.json --json
uv run --frozen score-fabric assurance verify \
  --assessment tests/fixtures/assurance/no-impact-scope/out/current-assessment.json \
  --trust-context tests/fixtures/assurance/fixture-trust/context.json --json
```

The current gate exits 1 with `stale`; portable verification exits 0 only when it
reproduces that non-pass outcome. Fixture-selected time is not a protected production clock.

## 6. Verify the portable record without Fabro

```bash
uv run --frozen score-fabric assurance verify   --assessment tests/fixtures/assurance/passing-scope/out/assessment.json   --trust-context tests/fixtures/assurance/fixture-trust/context.json   --json
```

Expected: exit 0 when the verifier reproduces the fixture-domain historical outcome and every
subject/evidence/decision/policy binding. Repeat from another root with permuted input ordering;
canonical subject, eligibility, reasons and gate outcome match. Delete one referenced raw result,
receipt, source file or trust root: verification cannot endorse the recorded pass. Verify a valid
blocked assessment: exit 0 only when it faithfully reproduces `blocked`; the gate is still non-pass.

## 7. Run implementation checks

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
uv run --frozen pytest -q
uv run --frozen python scripts/check_foundation.py
uv build --offline
```

Acceptance requires signature test vectors, wrong-domain and forged-origin cases, exact-one-change
staleness matrix, role/independence/conflict tests, empty-set and timeout tests, all six gate states,
relocation and input-order equivalence, exact-max and one-over-limit cases, a Fabro-free portable
verifier, and a non-skipped integration path from sealed 002/004 fixture records. Record actual
commands, hashes, counts, elapsed time, output sizes and limitations in `acceptance.md` when
implemented. A live production gate remains blocked until owner-controlled identity, collector,
trust root, role, independence, policy and protected time inputs are available and reviewed.
