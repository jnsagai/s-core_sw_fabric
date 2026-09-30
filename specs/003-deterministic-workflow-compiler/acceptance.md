# 003 acceptance record

Date: 2026-09-28

Increment 003 implements an offline deterministic compiler from a complete sealed 002 plan and a
reviewed execution mapping to a closed, source-mapped Fabro package. This is fabric-development
and native-conformance evidence. It does not register or execute a workflow and does not establish
target engineering acceptance, readiness, release, or deployment suitability.

## Delivered behavior

- Strict hash-selected compiler requests, exact plan/mapping/profile compatibility, bounded input
  parsing, reviewed mapping selection, explicit action authority and finite action budgets.
- Stable typed IR with full logical keys, explicit start/exit and native types, deterministic-check
  to command mapping, source origins, shared gate subjects, fan groups, and bounded loop policies.
- Fabric-semantic validation before rendering: endpoints, reachability, outcome coverage, gate
  dominance and concrete bypass paths, sorted cyclic components, finite exhaustion, mandatory
  fan-in, permission/model/budget boundaries, and approval-authority prohibitions.
- Canonical Fabro DOT/TOML rendering, closed UTF-8 file maps, per-file and package identities,
  complete source maps, guarded atomic publication, and isolated native validation.
- Read-only semantic diff and drift classification. Direct generated edits never become source
  authority and no inspection operation reseals or replaces the selected package.
- Public `workflow compile`, `validate`, `diff`, and `drift` commands with exit 0 for success or
  equivalence, exit 1 for semantic/native rejection or detected change, and exit 2 for malformed
  input or unavailable infrastructure.

The checked-in `policies/s_core_execution_mapping_v1.yaml` remains visibly `pending`; synthetic
fixture review records exercise compilation without claiming production owner approval.

## Acceptance coverage

| Acceptance cases | Evidence |
| --- | --- |
| AC003-01–04 | Mapping/IR, canonical rendering, closed package, source-map, deterministic bytes, and linear/shared-review integration tests |
| AC003-05–08 | Gate bypass, outcome gap/overlap, reachability, unbounded cycle, fan-in, authority, budget, and prior-output rejection tests |
| AC003-09–12 | Canonical identity, semantic diff categories, direct-drift classification, deterministic-check binding, and relocation-independent receipts |
| AC003-13–16 | Strict package integrity/closure, exact validator profile identity, disposable native materialization, CLI exit classes, and explicit unevaluated capabilities |

The contract tests use independent assertions. The side-effect-recording validator double is
reported only as simulated test acceptance. It is not used for the three real native cases below.

## Real native conformance

Fabro was built from a disposable copy of pinned source commit
`1b4fb15281ebb724426f9e480dce48d0100ff79b`; the protected reference checkout was not built or
modified. Fabro reports abbreviated Git SHA `1b4fb15`, version `0.362.0-nightly.0`, debug profile.
The adapter accepts that identity only as a minimum-seven-character prefix of the exact profiled
full commit and records the executable content digest.

| Representative package | Result | Native graph |
| --- | --- | --- |
| Linear obligations | Pass | 4 nodes, 3 edges |
| Shared parallel review | Pass | Parallel fan-out, complete mandatory fan-in, one shared human gate |
| Bounded correction feedback | Pass | Typed failure route, correction retry cycle, positive bound and exhausted destination in fabric semantics |

The command was:

```bash
SCORE_FABRO_BIN=/tmp/score-fabro-build-kDgEvg/target/debug/fabro \
  uv run pytest -q tests/integration/test_workflow_compiler_native.py
```

Result: 3 passed. Validation used a fresh temporary HOME and source tree for every invocation and
called only `fabro --json version` and `fabro --json validate`. No registration, run, provider,
model, approval-authentication, source edit, or target-artifact write occurred.

## Repository validation

- `ruff check .`: pass.
- `ruff format --check .`: pass (154 files).
- strict `mypy`: pass (30 source files).
- full `pytest -q` with `SCORE_FABRO_BIN` set: 123 passed, 1 optional 001 live-export test skipped.
- `scripts/check_foundation.py`: pass after this acceptance and handoff record were added.
- `uv build --offline`: pass; wheel and source distribution created.
- Exact-boundary suite: 12 passed in 0.23 seconds (0.37 seconds measured wall time), 98,048 KiB peak RSS. It covers exact maximum and one-over 64 MiB input/package bytes, 10,000 plan instances, 100,000 plan dependencies, 50,000 mapping rules/nodes, 200,000 edges, 10,000 cyclic components, 512 files, 512 KiB per file, 2 MiB native text, and all six action-budget ceilings. The representative linear package is 15,556 bytes.

Artifact hashes are recorded after the final build:

| Artifact | SHA-256 |
| --- | --- |
| Compiler profile | `f72e812b7dcb5371d7d0d749540971da5011bbd6bcd5e0f2397542c72b19647d` |
| Validator profile | `c2ced8f4f25a0161d966776201081eb7e3e9d6e54c8046a9abda06e8f1376d37` |
| Pending production execution mapping | `35a0fa1872820d6328e6f43329a43a5cec991830d85bf2c49c7c51e0ee486fc4` |
| Disposable Fabro executable | `09d338fbbe107d6c2e41fe9f3b33531c72b54782a2e17dac7c720b89898a68cf` |
| Linear representative package | `22b8ff2654ef362cdcfe29bf80939c540a3a076295107501ea8efe8c62938ab4` self-digest |
| Source distribution | `fbbdcb1abda5638d63cd4eb4720bdb587917a032340c97e31d093948cdc933a7` |
| Wheel | `792cb052d1fa963e3ece385c2d7b3aea300a1e7984a3c3108cb39e3c1300e0ab` |

## Open owner and later-increment work

- Review, revise, and approve the pending production execution mapping before compiling a
  production workflow. Fixture review evidence does not satisfy this decision.
- Increment 004 may consume the compiler’s logical plan-instance IDs and source map while adding
  native artifact generation and traceability; it must not treat workflow output as artifact
  authority.
- Increment 005 still owns protected evidence and human-decision authentication.
- Increment 006 still owns supported Fabro selection plus registry/run/inspect/resume behavior.
- Existing 000–002 owner reviews, the security-FDR source conflict, and full upstream
  score/module_template documentation builds remain open.
