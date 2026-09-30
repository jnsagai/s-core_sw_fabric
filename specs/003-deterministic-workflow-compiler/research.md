# 003 research and decisions

Date: 2026-09-27. Research covers the deterministic compiler boundary and the
Fabro conformance candidate pinned at commit
`1b4fb15281ebb724426f9e480dce48d0100ff79b`. It does not select the production
runtime, approve the execution mapping, or establish engineering readiness.

## Compile through a typed intermediate representation

**Decision:** Parse the sealed 002 plan and reviewed execution mapping into a typed,
immutable execution IR. Validate the IR before rendering DOT or support files. The IR,
not rendered text, is the authority for graph checks, source mapping, package identity,
semantic diff, and drift analysis.

**Rationale:** Required checks concern meaning: review dominance, complete outcome
partitions, bounded cycles, exact fan-in, permissions, and provenance. Re-parsing DOT
would lose reviewed source bindings and make presentation syntax an authority source.

**Alternatives considered:** Direct string-template generation is difficult to validate
and trace. Treating Fabro's parsed graph as the only model cannot express all fabric
invariants. Neither is used.

## Use the pinned Fabro source as a conformance baseline

**Decision:** Define a validator profile for the exact inspected commit. A successful
compile requires both fabric semantic validation and a real native `fabro validate`
receipt from a binary whose identity matches that profile. Native validation is run on a
disposable materialization of the package and must not register or execute a workflow.

The inspected command builds a run manifest and reports `workflow_name`, `nodes`,
`edges`, `valid`, and diagnostics in JSON mode. The validator may consult Fabro settings
and an environment catalogue, so the profile must bind an isolated configuration and
record the command, binary digest/version evidence, exit, and structured result.

**Rationale:** Source review alone cannot prove that emitted files are accepted by the
real parser and manifest builder. Binding an exact validator prevents a different local
installation from silently changing acceptance.

**Alternatives considered:** Reimplementing the parser would drift. Selecting an
unversioned PATH executable is irreproducible. Adopting this nightly source as the
production runtime would decide increment 006 prematurely.

## Emit a conservative explicit Fabro subset

**Decision:** Version 1 emits an explicit `digraph` with exactly one start and one exit.
Every node declares `type`; allowed generated types are `start`, `exit`, `agent`,
`prompt`, `command`, `human`, `conditional`, `parallel`, and `parallel.fan_in` only when
the execution rule explicitly selects them. The profile prohibits implicit type inference,
random selection, `on_failure=succeed`, success-producing timeout defaults, automatic or
replayed approval, unbounded visits, and partial success for mandatory fan-in.

The compiler keeps `deterministic_check` as a distinct internal action type and renders it as a
native `command`. The action must name a deterministic local tool profile, use an explicit
non-model capability binding, and preserve every result through typed outcome edges. This avoids
mistaking a check for a conditional chosen from prose or presentation syntax.

Graph-level failure behavior is `on_failure=route`. Mandatory mappings use
`allow_partial=false`. Every fallible node has explicit typed outcome edges, and every
retry/feedback route has a positive finite bound plus an exhausted destination.

**Rationale:** Fabro accepts features that are valid runtime behavior but unsafe for the
fabric contract. A small, explicit subset makes compiler meaning reviewable and stable.

**Alternatives considered:** Allowing all native syntax expands the semantic proof
surface. Inferring behavior from shape, label, or filename violates explicit-policy rules.

## Bind complete bounded action policy

**Decision:** Every executable action declares allowed inputs and paths, expected outputs, logical
data destinations, write scope, a versioned tool/permission profile, a model-capability profile or
explicit non-model binding, and a finite execution budget. The budget contains positive wall-time,
attempt, and tool-call ceilings plus model input-token, output-token, and cost ceilings where a
model is allowed. Non-model actions declare zero model-token/cost fields; no field may be null or
unlimited, and every applicable value must remain within the compiler profile.

**Rationale:** Constitution Principle IX requires paths, tools, model capabilities, data
destinations, budgets, and retry limits to be explicit. Carrying them in the IR and package lets
later runtime work enforce reviewed policy without inventing defaults.

**Alternatives considered:** Treating permissions as an implicit budget leaves time, token, cost,
and tool-call exposure unbounded. Deferring these fields to runtime would let operational settings
silently become execution policy.

## Package one canonical closed bundle

**Decision:** Write one canonical JSON workflow-package bundle. It contains the native
`entrypoint` and text `files` map compatible with the inspected workflow-version request,
plus the typed semantic manifest, source map, compile report, normalized input bindings,
validator receipt, per-file digests, and overall package digest. The registrable files map
is self-contained and uses package-relative POSIX paths.

For native validation, materialize only the declared files into a new disposable directory,
invoke the profiled validator on the declared entrypoint, capture the receipt, and remove
the directory. Later runtime work may submit the same `entrypoint`/`files` map after
revalidation; 003 does not register it.

**Rationale:** A single protected output is atomically replaceable, portable, and easy to
integrity-check. The contained native map preserves the candidate registry boundary without
making a registry call.

**Alternatives considered:** Publishing a mutable directory makes atomic replacement and
undeclared-file detection harder. A ZIP adds archive path and metadata variability without
helping the initial local CLI contract.

## Respect native source-package limits

**Decision:** The conformance profile enforces the candidate registry limits: at most 512
files, 512 KiB per individual text file, and 2 MiB total source bytes. The containing JSON
bundle is limited to 64 MiB. Inputs retain the existing 64 MiB per-file bound. Version 1 also
limits a plan to 10,000 instances and 100,000 dependencies; the compiler profile limits the
IR to 50,000 nodes, 200,000 edges, 50,000 mapping rules, and 10,000 cyclic components.
Limits apply before or during expansion, with deterministic diagnostics.

**Rationale:** Package validation should fail before a later registry would reject the same
closure. Explicit compiler bounds prevent accidental resource amplification.

**Alternatives considered:** Deferring limits to Fabro yields late, environment-dependent
failures. Unbounded graph analysis is inconsistent with the constitution.

## Derive stable logical identifiers from structured identity

**Decision:** Node and edge logical keys are canonical structured tuples including the plan
instance identity, execution-rule identity, action purpose, and branch/outcome role. A DOT-safe
identifier is `n_` or `e_` followed by the lowercase SHA-256 of that tuple. Human labels remain
separate. Bindings such as source revisions, content digests, compiler version, and validator
profile affect package identity without changing a logical ID whose source identity is stable.
Reject collisions after path, case, and identifier normalization.

**Rationale:** Structured keys avoid delimiter ambiguity and relocation-dependent names.
Separating logical identity from revision bindings preserves meaningful diffs.

**Alternatives considered:** Sequential IDs vary with traversal order. Slugified names
collide and leak display text into identity. Full mutable bindings in the ID obscure continuity.

## Validate graph meaning before native syntax

**Decision:** Semantic validation performs these deterministic checks:

1. Exactly one start and one successful exit exist; all nodes and edges are declared,
   reachable as appropriate, and traceable.
2. For each mandatory human gate, removing the gate and its incident traversal requirement
   must not leave a start-to-success path. Any bypass reports a concrete shortest path.
3. Every fallible node has a complete, disjoint outcome partition and no implicit success.
4. Strongly connected components are found with a deterministic Tarjan traversal. Every cyclic
   component has an explicit loop policy, positive limit within profile, and reachable exhausted
   terminal route.
5. Fan-out and fan-in refer to the same non-empty branch set. Mandatory obligations require
   complete fan-in; a reviewed subset is accepted only when its exact authority is mapped.
6. Native semantic relationships do not become schedule edges unless a reviewed rule cites them.
7. Every semantic element has at least one exact source-map origin.

**Rationale:** Native syntax acceptance is necessary but cannot establish process safety or
provenance. These checks implement FAB-014 deterministically.

**Alternatives considered:** Enumerating all paths is exponential. Dominance/reachability and
strongly connected component analysis prove the required properties within declared bounds.

## Make canonical bytes independent of operational context

**Decision:** Canonical JSON uses UTF-8, sorted object keys, compact separators, finite numbers,
and one trailing newline. Set-like collections sort by declared stable keys; semantically ordered
sequences preserve order. DOT rendering uses exact escaping and stable statement ordering.
Timestamps, absolute paths, temporary directories, host state, and original set-like input order
do not enter semantic content.

The package digest binds compiler version, normalized source digests, compiler and validator
profile semantic digests, semantic manifest, source map, report semantics, and every generated
file path and content digest. The digest field excludes only itself. Operational validator
receipt details that vary by location are recorded separately and excluded only where the
contract explicitly says so; validator identity and acceptance result remain bound.

**Rationale:** Relocation and independent compilation must produce the same bytes while still
detecting meaningful policy or baseline changes.

**Alternatives considered:** Hashing raw request files makes key order and local paths semantic.
Excluding validator identity would allow silent baseline drift.

## Treat diff and drift as separate operations

**Decision:** Semantic diff compares validated package models and reports changes by obligation,
node/action, edge/control flow, gate, permission, loop bound, generated file, compiler baseline,
and validator baseline. Drift first verifies package self-integrity and per-file digests, then
recompiles declared normalized sources in memory and compares the derived semantic identity.
Direct package edits are drift; they are never imported as reviewed source.

**Rationale:** Reviewers need meaningful categories, while integrity failures need exact expected
and actual content identities. Combining them would confuse reviewed source changes with tampering.

**Alternatives considered:** Raw text diff exposes formatting noise. Accepting edited output as
input would create a second process authority.

## Protect publication and inputs

**Decision:** Read and validate all inputs, build and validate the complete bundle in memory, and
run native validation before creating or replacing output. Reuse 002 containment and alias rules:
reject traversal, absolute package paths, ambiguous case, symlinks, hardlink aliases to protected
inputs, and output inside any input/reference root. Publish using a sibling temporary file,
flush, and atomic replace. Any malformed input, semantic failure, validator failure, or resource
failure preserves the prior package.

**Rationale:** A failed compile must not publish partial executable policy or damage its sources.

**Alternatives considered:** Incremental directory writes expose incomplete state. Overwriting
before native validation violates the acceptance boundary.

## Keep the implementation inside the existing package

**Decision:** Add a `score_sw_fabric.compiler` package and extend the existing CLI. Use Python
3.12, the standard library, and pinned PyYAML; add no runtime dependency. Tests use pytest with
Ruff and strict mypy. An external-validator integration group uses `SCORE_FABRO_BIN` and the
pinned validator profile. Unlike ordinary optional local integrations, actual matching-validator
evidence is required before increment 003 is marked complete.

**Rationale:** The current package already provides bounded readers, canonical JSON, protected
output patterns, and CLI conventions. A separate service or scheduler would expand scope and
conflict with the one-runtime principle.

**Alternatives considered:** A Rust compiler duplicates the current integration stack and adds a
second build boundary. Embedding Fabro as a Python parser is unsupported.

## Clarification outcome

No product clarification remains. The production Fabro runtime version, mapping owner approval,
authenticated human decisions, evidence trust, and workflow registration are deliberately later
decisions. For 003, their absence is a stated boundary or a blocked input, not a value the compiler
may infer.
