# Proposed deterministic workflow compiler contract v1

Status: design only; implement and test in increment 003. This is a local CLI/package
contract. It does not create a native S-CORE API or a Fabro runtime registration API.

## Commands

```text
score-fabric workflow compile --request REQUEST.yaml --out PACKAGE.json [--json]
score-fabric workflow validate --package PACKAGE.json --validator PROFILE.yaml [--json]
score-fabric workflow diff --before PACKAGE.json --after PACKAGE.json [--json]
score-fabric workflow drift --request REQUEST.yaml --package PACKAGE.json [--json]
```

`compile` is the only write operation. It validates the complete IR and native package before
atomically replacing `--out`. `validate`, `diff`, and `drift` are read-only. JSON console output
is a bounded command receipt and never substitutes for the sealed package or structured result.

### Exit semantics

| Command | Exit 0 | Exit 1 | Exit 2 |
| --- | --- | --- | --- |
| compile | Package passed semantic and profiled native validation and was published | Validly parsed inputs failed compiler semantics or native acceptance; prior output preserved | Malformed, corrupt, unsupported, unsafe, unavailable, or infrastructure failure; prior output preserved |
| validate | Package integrity, fabric semantics, closure, validator identity, and native validation pass | Package is well-formed but a validation predicate fails | Package/profile unreadable, malformed, unsafe, validator unavailable, or invocation invalid |
| diff | Packages are semantically equivalent | One or more semantic categories differ | Either package is malformed, corrupt, or unsupported |
| drift | Package integrity and recompilation identity are clean | Direct package drift or reviewed-source divergence exists | Request/package invalid, required source unavailable, or validator/compiler baseline unavailable |

Native rejection is exit 1 when a matching validator ran and rejected generated semantics. A
missing, mismatched, or unusable validator is exit 2. No nonzero result publishes a new package.

## Compilation request

The YAML request is strict and bounded. Its semantic form is equivalent to:

```yaml
schema_version: 1
inputs:
  plan:
    path: path/to/plan.json
    sha256: <64 lowercase hex>
    semantic_digest: <declared plan digest>
  execution_mapping:
    path: path/to/execution-mapping.yaml
    sha256: <64 lowercase hex>
    semantic_digest: <declared mapping digest>
  compiler_profile:
    path: profiles/compiler-v1.yaml
    sha256: <64 lowercase hex>
    semantic_digest: <declared profile digest>
  validator_profile:
    path: profiles/fabro-conformance-1b4fb152-v1.yaml
    sha256: <64 lowercase hex>
    semantic_digest: <declared profile digest>
local_paths:
  output_root: path/to/compiler-output
  protected_roots:
    - path/to/native-or-target-source
```

Paths resolve from the request file. Each input is at most 64 MiB. Transport digests are checked
before parsing. Normative mappings and profiles reject unknown fields. Boolean values are not
accepted as integer schema versions or limits. `local_paths` is excluded from semantic identity,
while every selected input semantic digest remains bound.

The output must be under `output_root`, outside input/protected roots, and distinct from every
input by canonical path and file identity. Symlink parents, hardlink aliases, traversal, and
case-ambiguous paths fail before any write.

## Accepted plan boundary

The compiler accepts only the exact supported 002 work-product-plan schema. It verifies the plan
self-digest and selected semantic digest, then requires:

- `planning_status` is `complete` and `closure_complete` is true;
- every retained instance has known applicability and a supported effective disposition;
- no blocker, unresolved source conflict, dangling dependency, unknown mandatory applicability,
  or unresolved external obligation remains;
- every dependency endpoint is present and every instance identity agrees with its tuple;
- compiler and mapping profiles select the exact catalogue, process, target baseline, and plan
  bindings declared by the package request.

The compiler does not reinterpret the catalogue, repair a blocked plan, or infer ordering from
native process links. A complete draft remains engineering-readiness `not_evaluated`.

## Execution mapping contract

The execution mapping is reviewed project configuration. It declares exact plan compatibility,
its own pending/accepted mapping review record, and finite rules. Production compilation accepts
only the profile-defined reviewed state with a source reference; a boolean `approved` or `trusted`
field is invalid.

Each compilable plan instance must match a rule that explicitly supplies:

- action purpose and type;
- role and subject;
- allowed inputs/paths, expected outputs, and explicit logical data destinations;
- write scope and tool/permission profile;
- versioned model-capability profile or explicit non-model binding;
- positive finite wall-time, attempt, tool-call, token, and cost ceilings as applicable, all within the compiler profile;
- completion predicate and evidence expectation;
- all success and non-success outcomes;
- prohibited authority;
- source/rule origins and rationale.

Ordering exists only through mapping rules. A native dependency may be cited as origin, but it is
not executable ordering until a reviewed rule selects its exact endpoints and rationale. Rule
overlap must be semantically identical; disagreement is `MAPPING_CONFLICT`.

Gate deduplication uses the exact tuple `(subject set, purpose, authority requirement, actor/role,
independence, bindings, outcome policy)`. Agreeing gates merge origins. A difference in any tuple
field preserves separate gates or causes an explicit mapping conflict; purpose is never discarded.

## IR semantic rules

Before rendering, the compiler enforces:

1. One start, one successful exit, unique logical IDs, valid endpoints, and deterministic
   reachability. No undeclared or unreachable action may remain.
2. Every generated semantic element has at least one verified origin and source-map projection.
3. Each required human gate dominates every successful path for its bound subjects. An authorized
   exclusion must name the exact gate purpose/subject and remain visible. A failure reports a
   concrete start-to-success bypass path.
4. Every fallible action has a complete and disjoint explicit outcome partition. Failure, blocked,
   timeout, unknown, malformed, infrastructure, and exhaustion outcomes cannot default to success.
5. Each cyclic strongly connected component has exactly one compatible declared loop policy,
   a positive finite profile-bounded limit, and a reachable explicit exhausted destination.
6. Parallel branch sets are non-empty and agree at fan-out and fan-in. Mandatory obligations
   require all branches unless an exact reviewed subset policy is bound.
7. Generated human nodes prohibit automatic approval, replayed approval, approval credentials,
   and success-producing timeout defaults.
8. Agent and command nodes cannot receive protected evidence-collector or decision-approval
   credentials. Their allowed paths, data destinations, and write scope stay within the mapped
   target boundary for later runs.
9. Every node has a known capability binding and finite profile-bounded budget. Model-bearing
   nodes select an allowed model-capability profile; other nodes declare `none`. Missing, zero where
   positive is required, unlimited, unknown, or above-profile values fail semantic validation.

Semantic validation is stricter than native validation and always has precedence.

## Rendering contract

The native source set includes an entrypoint TOML and a DOT graph:

```toml
_version = 1

[workflow]
graph = "workflow.fabro"
```

The DOT document declares a `digraph`, graph-level `on_failure=route`, explicit node types, and
all outcome/control-flow edges. It has one `start` node and one `exit` node. Rendered node types
are limited by the profile. A mandatory mapping cannot render `allow_partial=true`; visit/retry
bounds cannot be zero; selection cannot be random; no failure setting may convert failure to
success.

The internal `deterministic_check` action always renders as native `command`. Its deterministic
tool profile, declared inputs/paths, outputs/destinations, finite budget, completion predicate, and
typed success/non-success edges remain bound in the manifest and source map.

Generated identifiers use type prefixes plus canonical logical-key SHA-256. Labels are escaped
display strings and do not determine identity or semantics. Node and edge statements are sorted
by logical ID. Renderer behavior and escaping rules are versioned in the compiler profile.

Referenced prompts, schemas, scripts, policies, and configuration are materialized as UTF-8 text
files in the native source map. A reference to an absent or undeclared file, an extra file, an
absolute path, traversal, duplicate normalized path, case collision, or content mismatch fails
closure validation.

## Package envelope and canonical identity

The JSON package has this top-level shape:

```json
{
  "schema_version": 1,
  "manifest": {},
  "entrypoint": "workflow.toml",
  "files": {"workflow.fabro": "...", "workflow.toml": "..."},
  "source_map": [],
  "compile_report": {},
  "semantic_validation": {},
  "native_validation": {},
  "digest": "sha256:..."
}
```

The exact schemas will live under `schemas/`; this contract governs their behavior. Canonical JSON
is UTF-8 with sorted keys, compact separators, finite numbers, and one trailing newline. Set-like
arrays sort by declared keys. Ordered action/predicate content preserves declared semantic order.

The `files` map is compatible with the inspected candidate workflow-version request and must obey:

- no more than 512 files;
- no individual file above 512 KiB;
- no more than 2 MiB total UTF-8 file bytes;
- entrypoint exists in the map;
- every path is normalized and package-relative.

The whole package is at most 64 MiB. Its digest binds the canonical content excluding only the
`digest` field. The manifest separately binds compiler/version, canonicalization and semantic-rule
versions, input semantic digests, validator profile and identity, IR digest, every file digest,
source-map digest, and report semantic digest.

## Native validator contract

The validator profile binds:

- Fabro source commit `1b4fb15281ebb724426f9e480dce48d0100ff79b`;
- hashes of the inspected root manifests, DOT reference, run-configuration reference, CLI
  argument definition, validate implementation, and candidate workflow-version implementation;
- MIT license identification;
- exact validation arguments/JSON mode and isolated environment contract;
- how executable digest/build identity is established;
- accepted diagnostic schema and resource/timeout bounds.

Compilation materializes the `files` map in a new disposable directory, creates an isolated
configuration location, invokes validation on the entrypoint, captures bounded stdout/stderr and
structured output, and removes the directory. The command must resolve no undeclared package file.
The profile may name required static environment-catalogue fixtures by digest. Host default
settings are not accepted as semantic configuration.

The native receipt records semantic identity and acceptance without binding temporary paths,
timestamps, or process IDs. The compiler never invokes register, run, resume, cancel, model,
provider, Git mutation, or target-edit operations.

## Diff contract

`workflow diff` verifies both package self-digests before comparison. It emits ordered changes in
these categories:

```text
obligation
node_action
edge_control_flow
gate
permission
loop_bound
fan_group
generated_file
compiler_baseline
validator_baseline
```

Each change includes a stable subject key, before/after semantic bindings, source origins, and
affected logical IDs. A raw formatting diff is never the sole result. Equivalent validated
packages produce exit 0 even when their operational input paths differed.

## Drift contract

`workflow drift` verifies the stored package digest, every generated file digest, closure, and
source-map consistency. It then recompiles the request through validation in memory and compares
the expected package semantic identity. It reports exact expected/actual identities and paths.

A direct edit, deleted file-map entry, undeclared added entry, changed source, profile change, or
validator change produces exit 1 when it can be classified. Drift never reseals or overwrites the
package. Regeneration from reviewed sources is the only way to publish a changed package.

## Protected publication

`compile` performs no output mutation until all validation passes. It writes canonical bytes to a
new sibling file opened without following symlinks, flushes and syncs as supported, then atomically
replaces the selected package. It must re-check relevant output/input identities at publication.
Any error removes only its own temporary file and preserves the previous package and all inputs.

Concurrent hostile filesystem mutation is outside this local single-owner contract, but ordinary
path aliasing and time-of-check replacement defenses used by the existing project remain required.

## Required report boundary

Every successful compile report states that the package is compiled and accepted by the selected
conformance validator only. Workflow registration/execution, runtime selection, model behavior,
trusted evidence, human decision authentication, engineering acceptance/readiness, release, and
deployment are `not_evaluated` and remain outside increment 003.
