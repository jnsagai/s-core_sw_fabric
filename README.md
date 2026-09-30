# s-core_sw_fabric

Fabro-based orchestration for Eclipse S-CORE engineering workflows, with native
traceability, safety analysis, human approval gates, and deterministic verification.

**Status:** increments 000-004 are implemented for review. Increment 005 now has a fixture-domain assurance CLI under active acceptance review. Increment 004 adds bounded native
artifact indexing, isolated hash-bound create/update candidates, expected-set trace coverage,
semantic diff/drift, conservative impact, and locked module-template Bazel validation. Increment 003
retains isolated Fabro validation at commit
`1b4fb15281ebb724426f9e480dce48d0100ff79b`. Checked-in production mappings and profiles remain
visibly pending owner review, so no production workflow or artifact policy is approved.
Registration, execution, production evidence acceptance, readiness, release, deployment,
protected production decisions, and model calls remain unevaluated. See the
[004 acceptance record](specs/004-native-artifact-traceability/acceptance.md),
[004-to-005 handoff](docs/handoff/004-to-005.md), and [roadmap](docs/backlog/roadmap.md).
Increment 006 (candidate runtime) and increment 007 (agent context and profiles) are implemented
for disposable use only, and increment 008 (component safety feedback) for fixture
demonstrations only; see the [008-to-009 handoff](docs/handoff/008-to-009.md).

Spec Kit manages development of this fabric. S-CORE owns target engineering semantics
and work products. Fabro owns workflow execution/run state. APM/MCP supplies supported
context/tools. Agents draft; deterministic tools verify; authorized humans accept.

## Development

Requires Python >=3.12 and uv 0.12.17. From this repository:

```bash
uv sync --frozen
uv run --frozen score-fabric --help
uv run --frozen score-fabric doctor --json
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
uv run --frozen pytest
uv run --frozen python scripts/check_foundation.py
uv build
```

Pytest disables automatic loading of unrelated host plugins (this workstation exports ROS
plugins through PYTHONPATH); project plugins must be explicitly declared if added.

`doctor` checks only the two lock-file envelopes, offline. Exit 0 means those files
were readable with schema version 1; exit 2 means blocked/usage error. It always
reports engineering readiness as `not_evaluated`. It does not yet check source
compatibility, installed tools, credentials, roles or runtime availability.
The catalogue CLI imports a local, hash-pinned export without fetching URLs or
executing Sphinx configuration. From the repository root:

~~~
uv run --frozen score-fabric catalog export --manifest tests/fixtures/native/export-manifest.yaml --out tests/fixtures/native/build/catalogue.json --json
~~~

Exit 0 means a catalogue was generated, 1 means native semantic integrity failed,
and 2 means input or output was invalid. The output stays beneath the manifest
directory, outside every declared source tree, and is replaced atomically only after validation. Its digest covers native
rules, export bytes, source content fingerprints, references and declared provenance.
It always reports engineering readiness as not_evaluated. See
[001 acceptance](specs/001-native-process-catalog/acceptance.md) for supported
formats, tests and fresh-build evidence.

The planning CLI consumes a hash-selected local intake plus sealed catalogue, profile, mapping,
inventory and decision-reference documents:

~~~
uv run --frozen score-fabric plan --input PATH/TO/intake.yaml --out PATH/TO/out/plan.json --json
~~~

Exit 0 writes a complete draft, exit 1 writes a blocked draft with retained findings, and exit 2
preserves any prior output because input or output validation failed. Every result has
`plan_kind: draft` and `engineering_readiness: not_evaluated`. The planner never authenticates
reuse or tailoring decisions; those proposals remain unresolved until increment 005 supplies a
protected verifier. See the [002 validation guide](specs/002-applicability-and-work-product-plan/quickstart.md).


The workflow compiler accepts a sealed complete 002 plan plus a reviewed execution mapping and
exact compiler/validator profiles. It validates fabric semantics before rendering or native
validation and publishes only after every stage passes:

~~~
uv run --frozen score-fabric workflow compile --request PATH/request.yaml --out PATH/out/package.json --json
uv run --frozen score-fabric workflow validate --package PATH/out/package.json --validator profiles/fabro-conformance-1b4fb152-v1.yaml --json
uv run --frozen score-fabric workflow diff --before A.json --after B.json --profile profiles/deterministic-compiler-v1.yaml --json
uv run --frozen score-fabric workflow drift --package A.json --profile profiles/deterministic-compiler-v1.yaml --json
~~~

Exit 0 means accepted/equivalent/clean, exit 1 means a semantic/native rejection or detected
difference/drift, and exit 2 means malformed input or unavailable infrastructure. Compilation
preserves any prior output on both failure classes. See the [003 validation guide](specs/003-deterministic-workflow-compiler/quickstart.md).


## Trusted evidence and human gates (Increment 005)

`score-fabric assurance subject|evidence|decision|gate|verify` consumes sealed 002/004 records,
checks signed Ed25519 origins against a separately supplied trust context, and produces a scoped
portable assessment. The version-1 records have strict [schemas](schemas/README.md) and exact
`fixture_contract` or `production` domains. A fixture pass proves the gate algorithm only;
production remains blocked because no owner-controlled identity provider, collector, signing
service, trust-root provenance, role registry, reviewed gate policy, or protected time authority
has been provisioned. The verifier never signs evidence or records a human act.

```bash
uv run --frozen score-fabric assurance subject --request tests/fixtures/assurance/passing-scope/subject-request.yaml --out tests/fixtures/assurance/passing-scope/out/subject.json --json
uv run --frozen score-fabric assurance evidence --request tests/fixtures/assurance/passing-scope/evidence-request.yaml --out tests/fixtures/assurance/passing-scope/out/evidence-result.json --json
uv run --frozen score-fabric assurance decision --request tests/fixtures/assurance/passing-scope/decision-request.yaml --out tests/fixtures/assurance/passing-scope/out/decision-result.json --json
uv run --frozen score-fabric assurance gate --request tests/fixtures/assurance/passing-scope/gate-request.yaml --out tests/fixtures/assurance/passing-scope/out/assessment.json --json
uv run --frozen score-fabric assurance verify --assessment tests/fixtures/assurance/passing-scope/out/assessment.json --trust-context tests/fixtures/assurance/fixture-trust/context.json --json
```

`subject`, `evidence`, and `decision` return 0 for a complete eligible fixture result, 1 for a
well-formed ineligible result, and 2 for malformed or unsafe inputs. `gate` returns 0 only for an
exact scoped `pass`; `fail`, `blocked`, `not_evaluated`, `not_applicable`, and `stale` return 1.
`verify` returns 0 when it reproduces the *historical* outcome, including a historical non-pass;
semantic disagreement returns 1 and malformed or unavailable inputs return 2. Every output
retains `engineering_readiness: not_evaluated`; no module, platform, or release authority is
conferred. See the [005 quickstart](specs/005-trusted-evidence-and-human-gates/quickstart.md)
and [005 acceptance record](specs/005-trusted-evidence-and-human-gates/acceptance.md).

Module/platform readiness and release decisions remain for 014 and later increments; a 005
result cannot substitute for those gates.

### Runtime integration (006, candidate only)

The following commands were executed against a disposable loopback server built from the pinned
Fabro candidate `1b4fb15281ebb724426f9e480dce48d0100ff79b`. No production runtime is selected.
A version-1 `runtime_request` binds the sealed 003 package, runtime intent, candidate profile and
executable/API bytes, an owner-only disposable token file, a ledger root and a disposable target:

```bash
uv run --frozen score-fabric runtime register --request REQUEST.yaml --out BINDING.json --json
uv run --frozen score-fabric runtime run      --request REQUEST.yaml --out BINDING.json --json
uv run --frozen score-fabric runtime status   --request REQUEST.yaml --out SNAPSHOT.json --json
uv run --frozen score-fabric runtime resume   --request REQUEST.yaml --out DECISION.json --json
uv run --frozen score-fabric runtime cancel   --request REQUEST.yaml --out CANCEL.json --json
uv run --frozen score-fabric runtime export   --request REQUEST.yaml --out EXPORT.json --json
uv run --frozen score-fabric runtime verify   --export EXPORT.json --json
```

Exit 0 means the exact operation or faithful observation completed (for `verify`, a complete
historical reproduction, even of a waiting or failed run). Exit 1 publishes an explicit
non-success record: reconciliation required, waiting without a bound subject, blocked resume,
pending cancellation, or incomplete export. Exit 2 leaves prior output byte-identical. Explicit
same-run resume is **not** a demonstrated capability of the candidate: native resume was accepted
but inert, so `resume` never admits continuation there. Fabro success, events and answers remain
runtime observations; 005 production authority is still pending (005 T009). See the
[006 contract](specs/006-fabro-runtime-integration/contracts/runtime.md) and
[acceptance record](specs/006-fabro-runtime-integration/acceptance.md).

### Agent context and profiles (007, disposable use)

Increment 007 bounds engineering agents around the pinned S-CORE `mcp-servers` packages
(`29aeaa8`) and the model catalogue captured from the pinned Fabro candidate. Each command reads
one version-1 request and publishes one sealed record:

```bash
uv run --frozen score-fabric agent discover --request DISCOVER.yaml --out INVENTORY.json --json
uv run --frozen score-fabric agent setup    --request SETUP.yaml    --out SETUP.json     --json
uv run --frozen score-fabric agent context  --request CONTEXT.yaml  --out BUNDLE.json    --json
uv run --frozen score-fabric agent admit    --request ADMIT.yaml    --out ADMISSION.json --json
uv run --frozen score-fabric agent check    --request CHECK.yaml    --out CHECK.json     --json
```

Servers run only from a verified disposable copy, never through the unpinned upstream `uvx`
references; drift or a failed handshake blocks. Setup is separate and idempotent. Context binds
the workspace commit and native source digests and labels local observations as hints.
Roles cannot hold approval, collector, answer, run-management, resume, setup or credential
grants. Admission never authorizes a live call (`call_authorized: false`). Exits follow 006
(0 exact result, 1 published stop, 2 malformed input). Role, model and budget profiles are
drafts pending owner review. See the [007 contract](specs/007-apm-agent-context-and-profiles/contracts/agent.md)
and [acceptance record](specs/007-apm-agent-context-and-profiles/acceptance.md).

### Component safety feedback (008, fixture demonstrations)

Increment 008 checks native component FMEA/DFA documents against a profile pinned to the S-CORE
process, templates and metamodel, loops unresolved mitigations back to requirement/AoU and
architecture review, and keeps design acceptance separate from closure:

```bash
uv run --frozen score-fabric safety check  --request CHECK.yaml  --out REPORT.json --json
uv run --frozen score-fabric safety packet --request PACKET.yaml --out PACKET.json --json
uv run --frozen score-fabric safety gate   --request GATE.yaml   --out GATES.json  --json
```

Every fault model and DFA initiator must be analysed, excluded with rationale, or (platform-scope
initiators) allocated to a resolvable platform DFA. `sufficient: yes`/`status: valid` promotions by
agents are refused; decisions count only from reproduced 005 assessments bound to the exact file
digests, so the fixture demos stop at `awaiting_decision`. Checklist answers stay with the human
reviewer. See the [008 contract](specs/008-component-safety-feedback/contracts/safety.md) and
[acceptance record](specs/008-component-safety-feedback/acceptance.md).

## Spec Kit

Managed assets were initialized with official Spec Kit v1.0.12, commit
`e77daa9021d20db26b878f7dfa5640fe5a42d04e`, using Codex skills. Reinstallation:

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@e77daa9021d20db26b878f7dfa5640fe5a42d04e
specify version
```

The session instead installed into `/tmp/s-core-foundation/{tools,bin}` to preserve
the pre-existing global 0.14.0. Put the pinned CLI on PATH when using scripts.
Do not reinitialize existing managed files without reviewing the changes.
Supported chat invocations include `$speckit-constitution`, `$speckit-specify`,
`$speckit-clarify`, `$speckit-plan`, `$speckit-checklist`, `$speckit-tasks`,
`$speckit-analyze`, `$speckit-implement` and `$speckit-converge`.
These are agent instructions, not shell commands.

## Boundaries

Reference clones are read-only. Native documentation builds need disposable copies;
one pinned process hook writes a local virtual environment and generated portals.
Runtime selection is unresolved: the inspected stable Fabro release lacks the newer
workflow registry API, and the nightly candidate used for 006 remains `candidate_only`. The pinned process baseline and module_template passed disposable `needs_json` and
`docs_check` builds.
See the locks and capability matrix.

No test result, analyzer report or Fabro run can automatically imply safety acceptance,
release readiness, certification or deployment suitability.

**Invariant:** If Fabro disappeared tomorrow, all authoritative S-CORE engineering
artifacts would remain valid and understandable.

## Native artifact traceability (Increment 004)

The artifact adapter indexes source-qualified native RST, creates isolated template/scoped-edit
candidates, evaluates expected trace obligations, and reports semantic differences, direct drift,
and conservative impact. Public commands are `score-fabric artifact index|candidate|validate|trace|diff|drift`.
Exit 0 means success/equivalent/clean, exit 1 means a domain failure or detected change, and exit 2
means malformed, unsafe, unsupported, or unavailable input. Candidate and index publication is
atomic; blocked trace reports remain reviewable. A candidate with an explicit trace-profile
reference attaches a report over its edited index and retains the same unevaluated capability
boundary. Production target mutation, approval, evidence
trust, readiness, registration, execution, release, and deployment remain outside Increment 004.

Checked-in profiles retain pending production review. Licensed fixture profiles use an explicit
fixture-only review override. See the [004 quickstart](specs/004-native-artifact-traceability/quickstart.md)
and [acceptance record](specs/004-native-artifact-traceability/acceptance.md).
