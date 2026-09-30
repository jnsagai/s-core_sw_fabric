# 003 proposed data model — v1

These shapes define the compiler contract. They are not Fabro APIs and do not authenticate
human decisions. All normative envelopes reject unknown fields and require exact integer
schema versions. Null, missing, unknown, blocked, failed, and successful states remain distinct.

## Compilation request and input bindings

| Entity | Required content and relationships |
| --- | --- |
| CompilationRequest | `schema_version`, sealed plan reference, execution-mapping reference, compiler-profile reference, validator-profile reference, output root, protected roots, and expected semantic digests |
| InputReference | logical kind, local path, transport SHA-256, expected schema version, and expected semantic digest; local path is operational only |
| NormalizedInputBinding | logical kind, selected identity/version, semantic digest, upstream self-digest, and source/baseline vector included in package identity |
| ProtectedRoot | canonical input/source/reference root and its alias identity used only by output safety validation |

The request is local configuration, not a source of engineering policy. It selects already
reviewed content and exact profiles. The compiler verifies each transport hash before parsing,
then validates self-digests and semantic bindings before deriving an IR. Paths and temporary
locations do not enter semantic identity.

Compilation is allowed only when the 002 plan is sealed, `planning_status=complete`, closure is
complete, readiness is still `not_evaluated`, and every retained instance has a supported effective
disposition. Blocked findings, unresolved applicability/disposition, unsupported external debt,
or plan/profile digest mismatch prevent package generation.

## Execution mapping

| Entity | Required content and validation |
| --- | --- |
| ExecutionMapping | schema version, stable mapping ID/version, exact plan/profile compatibility, review state/reference, rules, semantic digest, source origins, and declared limits |
| ExecutionRule | stable rule ID, selectors over explicit plan fields, one or more action templates, ordering rules, gate rules, merge rules, loop policies, source origins, and rationale |
| ActionTemplate | action purpose, explicit action type, role, allowed inputs/paths, expected outputs, data destinations, write scope, tool/permission profile, model-capability binding, execution budget, completion predicate, evidence expectation, outcomes, prohibited authority, and support-file refs |
| ModelCapabilityBinding | versioned capability-profile ID for model-bearing actions or explicit `none`; required/prohibited capabilities and provider/model selection constraints, without credentials |
| ActionBudget | positive finite wall-time seconds and attempt/tool-call ceilings plus model input-token, output-token, and cost ceilings where applicable; non-applicable model fields are explicit zero, never unlimited/null |
| OrderingRule | predecessor/successor logical action selectors, edge type, condition/outcome where applicable, and exact source/rationale |
| GateRule | gate purpose, subject selector, required actor/role and independence, exclusion policy reference if any, outcomes, timeout behavior, and source/rationale |
| LoopPolicy | loop identity, entry/retry/exhausted outcomes, positive maximum attempts/visits, affected actions, and source/rationale |
| MergeRule | fan-out identity, exact branch identities, required set (`all` or authorized explicit subset), fan-in action, and source/rationale |
| SupportFileTemplate | logical package path, media/semantic kind, canonical content or deterministic renderer selection, origin, and referencing action IDs |

The mapping covers every compilable plan instance exactly once or through agreeing rules.
Selectors are a finite declarative vocabulary; no expression evaluation or embedded command
chooses applicability. Rule overlap is allowed only when all semantic bindings agree and origins
can be unioned. A missing review state/reference, unknown rule, or conflict blocks compilation.

An external obligation can compile only through an explicit external-boundary action that keeps
the evidence owed and cannot reach successful engineering acceptance by itself. A tailored-out
instance needs its already-effective 002 decision binding and an explicit exclusion mapping; 003
does not verify or invent that authority.

## Compiler and validator profiles

| Entity | Required content and validation |
| --- | --- |
| CompilerProfile | profile ID/version, supported request/plan/mapping versions, canonicalization version, identifier version, semantic-rule version, allowed action/node types, allowed model-capability profiles, action-budget ceilings, structural bounds, output contract, and semantic digest |
| CompilerLimits | input bytes, plan instances/dependencies, mapping rules, IR nodes/edges/cyclic components, bundle bytes, native file count, per-file bytes, total native source bytes, and finite per-action time/attempt/tool-call/token/cost ceilings |
| ValidatorProfile | profile ID/version, exact Fabro source commit, source-file hashes, license, accepted native syntax subset, invocation contract, environment isolation contract, binary identity requirements, and semantic digest |
| ValidatorInvocation | executable reference, arguments, JSON-output mode, clean working/config directories, allowed environment keys, timeout/resource bounds, and forbidden subcommands/effects |
| ValidatorIdentity | selected profile, source commit, executable content digest, reported version/build evidence, and compatibility assessment |

Version 1 binds candidate commit `1b4fb15281ebb724426f9e480dce48d0100ff79b`.
The validator profile is conformance evidence only. The compiler refuses an executable whose
identity cannot be matched to the profile. It invokes validation only; registration, execution,
resume, cancellation, provider calls, and model calls are forbidden.

## Typed execution IR

| Entity | Required content and validation |
| --- | --- |
| ExecutionGraph | graph ID/version, one start, one success exit, nodes, edges, gate obligations, fan groups, loop policies, and origins |
| ExecutionNode | stable logical key/ID, explicit internal action type and native node type, action purpose, bound plan instances, role, inputs/allowed paths, outputs/data destinations, write scope, permission profile, model-capability binding, execution budget, completion predicate, evidence expectation, failure behavior, prohibited authority, support refs, and origins |
| ExecutionEdge | stable logical key/ID, source node, target node, edge type, outcome/condition/branch role, loop ID when applicable, and origins |
| GateObligation | gate node ID, exact subject instances, purpose, actor/role, independence, authority requirement, allowed exclusion ref, and origins |
| FanGroup | fan-out ID, non-empty exact branch-start/branch-end set, fan-in ID, required branch set, partial-policy authority if selected, and origins |
| CycleComponent | sorted member node/edge IDs, loop policy ID, maximum visits/attempts, retry target, exhausted destination, and origins |
| Origin | kind (`upstream_process`, `reviewed_project_configuration`, or `authorized_human_decision`), source reference, source pointer, decision reference where applicable, and transformation rationale |

### Node and edge types

Compiler action types are `start`, `exit`, `agent`, `prompt`, `command`,
`deterministic_check`, `human`, `conditional`, `parallel`, and `parallel_fan_in`. Renderers map
`parallel_fan_in` to native `parallel.fan_in` and `deterministic_check` to native `command`.
The latter must use a deterministic local tool profile, an explicit non-model capability binding,
and typed outcome edges that retain the check result. Each type has an explicit allowed-field
contract. Titles, shapes, filenames, or prose never choose type.

Every executable node declares allowed paths and logical data destinations. Model-bearing nodes
select one allowed capability profile; every other node declares the explicit `none` binding.
Applicable budget values are positive finite integers within profile ceilings. Model token/cost
fields are zero only for non-model nodes; zero wall-time, zero attempts, negative values, null,
`unlimited`, unknown capability IDs, or any value above profile blocks compilation.

Edge types are `prerequisite`, `success`, `failure`, `blocked`, `timeout`, `unknown`,
`malformed`, `infrastructure`, `exhausted`, `condition`, `branch`, `merge`, `retry`, and
`feedback`. A rule may narrow the allowed outcomes but cannot omit any outcome its node can
produce. Conditions in one partition are complete and disjoint under the supported finite
predicate vocabulary.

### Logical identity

A node logical key is a canonical JSON tuple containing:

```text
(plan_instance_ids, execution_rule_id, action_purpose, action_role)
```

An edge logical key contains:

```text
(source_node_key, target_node_key, edge_type, outcome_or_branch, loop_id_or_null)
```

Plan instance IDs are sorted because their set is semantic. IDs are a type prefix plus SHA-256
of the canonical tuple. Full logical keys stay in the package so collisions can be detected,
not assumed impossible. Display labels and mutable revision bindings are not identity fields.

## Semantic validation result

| Entity | Required content and validation |
| --- | --- |
| ValidationFinding | stable code, severity, phase, message, affected logical IDs, source pointers, bypass/cycle path where applicable, and required action |
| SemanticValidation | ruleset version, graph counts, source-map coverage, ordered findings, and `valid` |
| NativeValidationReceipt | validator identity, profiled invocation identity, native result summary, bounded diagnostics, materialized file-set digest, exit class, and `accepted` |

Fabric semantic validation always runs before rendering and native validation. Native acceptance
cannot override a fabric finding. Operational path names, invocation timestamps, process IDs, and
temporary directory names are not semantic receipt fields.

Minimum finding families include input/profile mismatch, incomplete plan, mapping gap/conflict,
unsupported type, dangling/unreachable graph element, missing origin, gate bypass, outcome gap or
overlap, unbounded cycle, missing exhaustion, fan mismatch/partial mandatory merge, prohibited
approval behavior, unsafe path/alias, closure limit, renderer failure, validator identity mismatch,
and native rejection/unavailability.

## Generated file closure

| Entity | Required content and validation |
| --- | --- |
| PackageFile | normalized relative POSIX path, UTF-8 text content, byte count, SHA-256, semantic kind, referencing element IDs, and origins |
| NativeSourceSet | `entrypoint` plus path-to-text `files` map; at most 512 files, 512 KiB each, and 2 MiB total under profile v1 |
| PackageManifest | schema version, package identity, compiler/profile/validator bindings, normalized input bindings, IR semantic digest, generated file records, source-map/report digests, and limitations |
| SourceMapEntry | generated semantic kind/ID, output file and optional location, plan instance IDs, rule/policy IDs, source/decision refs, transformation rationale, and content binding |
| CompileReport | compilation status, semantic/native validation summaries, counts, package identity, bounded diagnostics, and explicit unevaluated capabilities/readiness |
| WorkflowPackage | manifest, native source set, source map, compile report, semantic validation receipt, native validation receipt, and self-digest |

Required native files include `workflow.fabro` and `workflow.toml`; referenced prompt, schema,
configuration, policy, and script text is included under a deterministic logical path. The TOML
uses `_version = 1` and a relative `[workflow] graph = "workflow.fabro"` binding. Every map path
must be normalized, unique under case folding, non-empty, relative, free of traversal, and present
in file records. Symlinks and hardlinks do not exist inside the logical map and are prohibited
during materialization.

The source map covers every IR node, edge, gate, loop, fan group, generated file, and material
renderer decision. Multiple agreeing origins are allowed and sorted. An element with no origin or
a source-map entry for an absent element makes the package invalid.

## Semantic diff and drift

| Entity | Required content and validation |
| --- | --- |
| SemanticChange | category, change kind (`added`, `removed`, `modified`), stable subject key, before/after bindings, origins, and affected logical IDs |
| SemanticDiff | schema/ruleset versions, before/after package identities, ordered changes grouped by category, summary counts, and `equivalent` |
| DriftEntry | package path or semantic subject, expected digest/binding, actual digest/binding, drift class, origins, and required action |
| DriftResult | declared package identity, integrity status, reproducibility status, ordered entries, reconstructed identity when available, and `clean` |

Diff categories are obligation, node/action, edge/control flow, gate, permission, loop bound,
fan group, generated file, compiler baseline, and validator baseline. Formatting-only changes
cannot appear because both inputs are validated canonical packages.

Drift classes distinguish self-digest mismatch, file-content mismatch, undeclared/missing file,
source-binding mismatch, compiler/profile change, and validator-profile change. Drift never updates
the selected package or its declared source.

## State transitions

Compilation is a pure derivation followed by guarded publication:

```text
request received
  -> inputs verified
  -> IR derived
  -> semantic validation passed
  -> files rendered and closure validated
  -> native validator accepted
  -> package sealed
  -> package atomically published
```

Any failure before publication ends with no replacement. A successful package remains
`compiled_and_validated`; it never transitions to registered, running, approved, accepted,
ready, released, or deployed in increment 003. Diff and drift are read-only derivations and
do not change either package.
