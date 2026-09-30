# Implementation Plan: Applicability and work-product planning

**Branch**: `002-applicability-and-work-product-plan` | **Date**: 2026-09-27 |
**Spec**: [spec.md](spec.md)

**Input**: The 002 specification, FAB-008–FAB-011, 001 verified minimal-consumer
baseline and ADR0003/0004. Status: implementation and automated validation complete;
human-owned review/profile decisions remain pending.

## Summary

Add an offline planner that reads a validated 001 catalogue, structured intake, a versioned
planning profile/mapping, existing artifact inventory and decision references. Enumerate
expected work-product instances independently of documents, compute explicit dependency
closure and emit coverage, dispositions and blockers in deterministic JSON. Scope, purpose
and namespace define identity; native revisions and baseline hashes bind it separately.

002 supports conservative draft planning. Effective reuse or tailoring requires authenticated
authority that 005 will supply. In production 002 those requests remain proposed/unresolved;
expected blocked outputs are valid fabric acceptance cases, never accepted target evidence.

## Technical Context

**Language/Version**: Existing Python >=3.12 integration package; target C++17 policy is data.

**Primary Dependencies**: Existing pinned standard library/PyYAML; no additional package is
planned. Reuse bounded JSON/YAML parsing and canonical encoding. Implement strict explicit
models/validation, consistent with 001. Reject unknown normative fields and boolean-as-integer
versions; preserve native raw metadata only in its existing open fields.

**Storage**: Local immutable inputs and one derived plan JSON file; no service/database.

**Testing**: Existing pytest, Ruff, strict mypy and foundation checks; source-backed fixtures
plus full saved native catalogue integration. No native rebuild is needed unless pins change.

**Target Platform / Project Type**: Offline Linux CLI/library within the existing package.

**Performance Goals**: Demonstrate bounded completion on the 74-work-product baseline and
representative multi-scope scenarios. Record time/peak size at implementation; do not claim
an unmeasured latency guarantee. Finite-set closure uses visited keys rather than recursion.

**Constraints**: 64 MiB per input, at most 1,000 scope nodes, 10,000 mapping rules,
100,000 candidate coverage rows, 10,000 instances and 100,000 dependency edges. Reject
oversized inputs before expansion; exceeding closure limits yields a blocked partial draft
marked incomplete. No fetching URLs, configuration execution, runtime/model calls or writes
to target/reference roots. Paths are operational and excluded from semantic hashes.

**Scale/Scope**: Pinned catalogue schema v1; four scope kinds; explicit purpose mappings;
new/reused/modified-reused component and security feature scenarios. The first source-cited
mapping must account for all 74 native work products at every supplied scope via explicit
coverage cells, including unresolved cells. Completeness of engineering support is not inferred
from coverage accounting. The native security-FDR mismatch remains a source-conflict blocker.

## Constitution Check

| Principle / gate | Pre-research decision | Post-design result |
| --- | --- | --- |
| Native authority and explicit policy (I, III) | Use source-cited, versioned mappings | Preserved; no automatic prose interpretation or ID rewrite |
| Portability and one runtime (II, VIII) | Derived plan only | Preserved; no scheduling/run state or new authority store |
| Human accountability and truthful evidence (IV, XI) | Treat input decision refs as unverified | Preserved; no production decision promotion before 005 |
| Deterministic checks and fail-closed readiness (V, VI) | Unknown facts retain obligations | Preserved; separate blocked draft and not_evaluated readiness |
| Traceability and provenance (VII, XII) | Bind sources/mappings/subjects by digest | Preserved; stable instance IDs separate from changing bindings |
| Bounded execution and increments (IX, X) | Offline planning, 002 only | Preserved; no provider calls, compiler, target edits or runtime |

No constitutional exception is required. User continuation authorizes design work; it does
not ratify the constitution, approve target classifications or complete owner review checkboxes.

## Project Structure

### Documentation delivered in this planning step

~~~text
specs/002-applicability-and-work-product-plan/
  spec.md
  plan.md
  research.md
  data-model.md
  contracts/planning.md
  quickstart.md
  checklists/requirements.md
  checklists/review.md
  evidence/source-review.json
  design-review.md
~~~

`tasks.md` records the completed implementation work and validation handoff.

### Implemented files

~~~text
src/score_sw_fabric/
  catalog/reader.py            # verified sealed-catalogue reader/index
  planning/models.py          # intake, scope, rule, instance, result shapes
  planning/reader.py          # bounded inputs and local path/baseline checks
  planning/mapping.py         # coverage and finite predicate evaluation
  planning/closure.py         # expected instance/dependency fixed point
  planning/dispositions.py    # inventory, reuse/tailoring proposals and blockers
  planning/export.py         # canonical plan and protected atomic output
  cli.py                      # plan command
schemas/
  intake.schema.json
  planning-profile.schema.json
  applicability-mapping.schema.json
  artifact-inventory.schema.json
  decision-references.schema.json
  work-product-plan.schema.json
profiles/cpp17-review-draft-v1.yaml
policies/s_core_applicability_v1.yaml
tests/contract/test_catalogue_reader.py
tests/contract/test_planning_inputs.py
tests/contract/test_planning_coverage.py
tests/contract/test_planning_dispositions.py
tests/contract/test_planning_cli.py
tests/integration/test_work_product_plan.py
tests/fixtures/planning/        # source-cited scenarios, origin explicitly fixture
~~~

**Structure Decision**: Keep one package and pure, separately testable stages. Add only
catalogue consumption and planning concerns. Store no mutable target artifact or review state.
A profile/mapping under these paths is project configuration, not a new native process source.

## Phase 0 — Research outcome

[Research](research.md) resolves technical design choices against pinned source files.
Key findings are absence of generic applicability attributes, multiple formal-review purposes,
human judgment in reuse classification, a safety/security review-template conflict and the
missing persisted-catalogue validation boundary. The 001 output protection defect found during
review was repaired separately and covered by three regression cases.

No product clarification is required for planning. Real profile approval, target decisions and
source-conflict resolution are explicit blocked inputs; implementation must not manufacture them.

## Phase 1 — Contracts and algorithm

Use [data model](data-model.md) and [planning contract](contracts/planning.md) in this order:

1. Parse bounded inputs and validate exact versions/identities, paths and declared hashes.
   Verify the catalogue's self-digest and selected baseline digest; build immutable indices.
2. Validate scope topology and exact profile compatibility. Record unsupported combinations
   and unverified decisions as blockers. No fallback to a weaker language/reliability profile.
3. Build coverage for every native work-product/scope pair. Evaluate only whitelisted finite
   predicates; unknown authority-sensitive facts never become false. Select or retain unresolved
   candidate instances; record source-backed outside-scope results separately from tailoring.
4. Expand explicit dependency mappings to a fixed point with visited keys and size bounds.
   Resolve parent/member selectors only through declared topology. Merge identical shared
   instances only when semantic bindings agree; aggregate origins and requesting scopes.
5. Match exact existing bindings against the expected set. Complete inventory absence permits
   create; explicit change permits update. Reuse/tailoring require checks recorded separately
   from the proposal and remain unresolved when authority is unavailable. External work stays owed.
6. Bind normalized semantic input digests; keep transport hashes only in validation receipts.
   Use stable diagnostic identities and sorted traversal even on bounded failure. Seal the plan and atomically write it only inside
   the configured output boundary, outside every input/source root. Retain blocked drafts with
   their status; malformed input produces diagnostics and preserves prior output.

Forward/backlinks, native statuses, definition IDs and planning outcomes remain separate.
Dependency edges explain obligations; they do not schedule execution or become accepted reviews.

## Validation and handoff to implementation

[Quickstart](quickstart.md) distinguishes today's runnable checks from future CLI scenarios.
Every AC002 case must map to tests in the subsequent task list. Add negative cases for missing
mapping, ambiguity, contradictory rules, cycles/limits, digest resealing against a selected
baseline, forged decision flags, unknown profile, stale reuse, false inventory absence and
output/source aliasing. Verify permutation/relocation determinism for each auxiliary input, deterministic limit failures,
logical ID stability and explicit selection when multiple native revisions coexist.

A source-backed integration run must enumerate all 74 work products and prove that introduced
unknown work products make coverage incomplete. It must exercise new, reused and security
scenarios and preserve the known source conflict. Tests may verify expected blocked outcomes;
no fixture may set a production trusted-authority flag.

Frozen lint/format/mypy/pytest, foundation checks, a public CLI example and the offline package
build pass; exact outcomes and hashes are recorded in `acceptance.md`. Implementation stops before
increment 003. Fabro release selection belongs to 003/006 and does not block 002.
