# Proposed planning contract v1

Status: design only; implement and test in 002. This contract narrows the brief's proposed
CLI and the 001 forward-boundary proposal. It does not create a native S-CORE API.

## CLI and result semantics

Proposed interface:

~~~text
score-fabric plan --input INTAKE.yaml --out PLAN.json [--json]
~~~

`--out` is one JSON file beneath the intake's explicit local output directory. It must also
be beneath the intake directory and outside every declared source/reference root. Do not
create native documents, launch a workflow or execute provider configuration from the intake.
`--json` prints a bounded diagnostic summary, output location and plan digest, not a second
uncontrolled copy of every native field.

| Exit | Result | Output behavior |
| --- | --- | --- |
| 0 | Complete draft within the declared planning bounds | Write sealed plan; readiness stays not_evaluated |
| 1 | Valid inputs generated a blocked draft: unknown applicability, coverage/source conflict, unsupported profile, pending decision or incomplete closure | Write explicitly blocked plan with retained candidates/findings; summary repeats blocked status |
| 2 | Invalid/unavailable input, corrupt catalogue, malformed mapping/topology, unsafe output or infrastructure failure | Emit diagnostic; preserve previous output and every input/source |

A blocked draft is useful review evidence and cannot be consumed as an executable or accepted
plan. Future consumers must check status, closure completeness, digest and their own authority
requirements rather than only file existence. Domain blockers must not be relabelled successful
because generation worked.

## Input documents and trust

All envelopes are version 1 and reject unknown normative fields. Intake references a sealed
catalogue and separate profile, mapping, inventory and decision-reference documents by local
path and SHA-256. It additionally selects the exact catalogue semantic digest. These input
hashes bind chosen bytes; none authenticates authority. Operational root paths are supplied
only in `local_paths`; source/content, repository identity, logical native paths and baseline
bindings remain semantic data.

Intake carries the fields described in [data model](../data-model.md), including per-scope
facts and an explicit set of affected scope/interaction refs. Omission of optional context
must have a defined unknown state; omission of mandatory envelope fields is an input error.
A declared unknown classification is a domain blocker, not a parse error. Unknown enum values
or unsupported schema syntax are input errors; a well-formed but unsupported profile combination
is a domain blocker. A declared existing artifact cannot claim an unchanged commit if its
provided content binding differs; classify that record as stale/inconsistent.

The loaded catalogue is validated independently of its caller: exact supported envelope,
finite values, unique qualified entity keys, known native types/sources, consistent source
references and valid resolved relation endpoints. Verify `digest` against SHA-256 of existing
001 `canonical(payload_without_digest)` and against the intake-selected expected digest;
validate transport SHA-256 as well. A resealed alteration must fail the selected-baseline check.
Retain raw non-normative metadata; do not reinterpret native status or template examples.

Preserved SourceRefs are evidence of local mapping/content inspection, not proof of a Git
signature, accepted native content or exact directive-line verification. A JSON schema and
TypedDict alone do not implement the semantic checks above.

## Mapping grammar and coverage

The first mapping supports only a finite declarative grammar:

- Native refs are explicit `(source_id, native_id, native_version)` keys resolving to the
  expected type; no latest-version fallback, regex ID discovery or implicit namespace lookup.
- `scope_selector` is one of `self`, `owning_module`, `owning_platform`,
  `affected_components`, `affected_features`. Selection uses declared scope relations;
  zero/multiple owners where one is required is an explicit finding.
- `when` is a conjunction of typed `eq` or `in` predicates on whitelisted facts:
  scope kind, development origin, requested language/environment, safety classification,
  security relevance, reuse route, presence of subcomponents and relevant interactions.
  Empty conjunction means unconditional inclusion only when the rule has a source basis.
  Multiple alternatives use separate rules; no Python, Jinja, shell, XPath or arbitrary code.
- Purposes, template refs, native role/checklist refs and dependency selectors are explicit
  arrays; their semantics are checked, not inferred from descriptive strings.
- Every rule records origin (`upstream`, `project_configuration`, `human_decision`), exact
  source/decision references, rationale and review status. A locally claimed review status
  does not bypass the decision boundary.

Evaluate true/false/unknown conservatively. Unknown input or missing authority does not become
false. An affirmative declared fact may add candidate obligations; an unverified fact must
not justify removing a potential obligation. Source-backed structural scope/development-origin
rules may identify unrelated candidates; classification/tailoring-based reductions need authority.
When that authority is unavailable in 002, retain the potential obligation as unresolved.
Conjunction is false if a genuinely established structural predicate is false; otherwise it
is unknown when any required predicate is unknown, and true only when all are established.

Start coverage from all catalogue `workproduct` entities crossed with all declared scopes.
For each pair record selected/outside_scope/unresolved and all relevant rules, sources and
expanded instance keys. Outside-scope requires a source-backed structural reason or the explicit revision-selection
reason defined below; there is no
implicit default exclusion. An unmatched pair yields `MAPPING_COVERAGE_GAP`. Profile support
cannot be defined by silently dropping unmapped catalogue entities. Limit coverage expansion
before materializing it, and report unsupported/incomplete coverage explicitly.

A catalogue may export multiple native revisions of the same source-qualified work-product ID.
The profile selects one exact active revision per `(source_id, native_id)` across this bounded
plan. A unique available revision may be selected explicitly by the matching profile rule;
multiple available revisions without an exact profile selection yield `PROFILE_REVISION_AMBIGUOUS`.
Never select the greatest revision implicitly. Coverage still includes every exported revision:
non-selected revisions use outside_scope with `REVISION_NOT_SELECTED`, the exact selection ref
and rationale. This is baseline selection, not target tailoring, and does not remove the active
logical obligation. Rules attempting incompatible simultaneous bindings to one logical identity
produce `MAPPING_CONFLICT` and retain the conflicting references. Supporting different active
revisions per scope is outside v1.

A single work-product/scope pair may expand into several required purposes. Missing purpose
rules must be caught by the profile's explicit expected-purpose declarations. Rule/profile
agreement is structural validation, not proof that the source interpretation is approved.
Include the pinned security FDR conflict as an unresolved mapping entry; do not change the
process ID to fit the template. Native audit status `valid` is not an exclusion decision.

## Expected set, dependency closure and inventory

Compute expected instances before consulting artifact inventory. Expand explicit dependency
rules with a worklist keyed by instance identity and evaluated rule. Reaching an existing key
unions origins/requesting scopes; it does not allocate another shared parent obligation.
Finite cycles terminate at a fixed set and are reported as dependencies, not schedule edges.
Malformed/dangling declared rule, purpose or native-reference keys are input errors (exit 2,
no output replacement). Well-formed rules with unavailable parent/member context or conflicting
source-backed bindings produce domain blockers (exit 1, retained draft). Size limits preserve an incomplete,
blocked draft rather than reporting closure. New facts do not appear during expansion.

Inventory matches on the full stable instance tuple, with exact artifact/document bindings.
No title/path substring matching is allowed. Complete inventory absence yields create; partial
inventory absence yields unresolved. An existing changed binding with explicit impact rationale
may yield update. Multiple conflicting inventory bindings for the same instance are an input
error; multi-document instances must declare their document set in one binding.

Missing required dependency instances must be materialized or recorded as unresolved/external,
not silently filtered. An external instance includes owner, interface, evidence owed and release
boundary. It never reports satisfaction in 002. A valid reduced-scope plan cannot certify its
containing module/platform.

## Decision and disposition boundary

The planner validates the shape and subject bindings of references to human decisions. Receipt
paths/URLs are inert data: no network fetch, credential use or command execution. Callers cannot
supply a trusted verification result or set accepted authority with a flag. Production 002 has
no protected verifier; it derives `AUTHORITY_UNVERIFIED` whenever a disposition requires one.

| Requested disposition | Conditions for effective disposition |
| --- | --- |
| create | Required candidate, known complete-inventory absence, usable source references, mandatory templates when the mapping requires them, and no unresolved applicability |
| update | Existing exact binding, explicit impact reason and no unresolved applicability |
| reuse | Exact accepted revision, explicit applicability/coverage rationale, current dependency bindings and verified authority; otherwise unresolved |
| tailored_out | Upstream permission, bound impact analysis, scope-specific rationale/decision, current subject/baseline, replacement refs when required and verified authority; otherwise unresolved |
| external_obligation | Declared external owner/interface/boundary/evidence owed and no ownership ambiguity; satisfaction remains unevaluated |
| unresolved | Any unmet prerequisite, source conflict or unknown required fact |

Safety-tailoring proposals additionally require an exact element-level impact-analysis
reference bound to the affected subject and baseline; absent/stale impact evidence yields
`TAILORING_IMPACT_MISSING` or `TAILORING_IMPACT_STALE`. A rationale is not that evidence.
A Q/QR/NQ route record separately references the classification approval by the native Safety
Manager role and acceptance of the containing change request before module-plan adaptation.
Artifact acceptance, classification approval and change-request acceptance are different
subjects/decision classes; one receipt cannot silently substitute for another. Missing or
unverified refs retain the proposed route and block effective adaptation.

Reuse and tailoring rows describe the eventual full contract. In production 002 their authority
prerequisites cannot be satisfied; requests remain visible with effective unresolved. Do not add
a public test/fixture trust switch. Tests can verify blocked production behavior and pure
validation helpers without claiming an accepted human decision. All results have `plan_kind:draft`.

Unknown classification, NQ safety reuse, missing classification approval, unknown security
interaction and stale coverage each carry separate reasons. A syntactically valid native
classification record does not prove classification acceptance. No 002 code chooses ASIL,
converts raw complexity into P/C, or downgrades a requested profile to make planning pass.

## Canonical result and protected output

Use the existing canonical JSON byte convention: UTF-8, sorted keys, compact separators,
finite numbers, no uncontrolled ID normalization and one trailing newline. Sort set-like
arrays by defined keys; preserve arrays whose order is part of a declared subject. Deduplicate
only equal identities with agreeing bindings. Digest excludes only its own field; do not
silently strip unknown semantic fields from a validated input.

The canonical plan binds the exact selected catalogue digest and normalized semantic digests
of profile, mapping, inventory, decision references and intake, plus target/source baseline
vectors, rules, scopes, expected instances, coverage, dependencies and blockers. Transport
file SHA-256 values are verified before parsing but retained only in the CLI validation receipt,
not in canonical plan content. This distinguishes selected input bytes from equivalent semantics.
For normalized intake, exclude only `local_paths` and local file-reference path strings, and
replace configuration-document transport references with their computed semantic digests; retain
the selected catalogue semantic digest. Native source/artifact content hashes remain semantic.
No native repository-relative artifact path, subject, rationale, role, classification or
decision binding is excluded. No generation timestamp is inserted.

Normalization sorts declared set-like collections in every input: scopes, affected refs, rules,
conjunctive predicates, membership operands, purposes, dependency rules, origins and inventory/
decision records. It rejects duplicate conflicting keys; it preserves ordered native/subject
content. Normalize before validation that emits domain findings and before graph traversal;
use stable identity-based diagnostic locations in the sealed plan, not original array indices.
Raw file/index pointers may appear in the unsealed CLI receipt. Visit closure in sorted identity/
rule order so a size-limited blocked result is deterministic too. Reordering equivalent auxiliary
documents changes transport receipts but not the plan. The sealed catalogue is an immutable
selected baseline; changing that selected digest always changes the plan binding.

Validate all input hashes and catalogue integrity before creating output directories. Protect
all supplied input paths and hardlink aliases, the intake file itself, and every declared
source/reference tree. Reject symlink output paths/parents and path traversal; use atomic
replace only after validation. A declared source root equal to the output root makes that
request invalid. Reuse the bounded reader/canonical helpers, not an unmodified writer designed
only for the 001 manifest. Concurrency against hostile filesystem mutation is outside this local
single-owner CLI contract and must not be represented as a hardened multi-tenant service.

## Required finding vocabulary

Minimum stable codes: `CATALOGUE_DIGEST`, `CATALOGUE_BASELINE`, `CATALOGUE_IDENTITY`,
`CATALOGUE_REFERENCE`, `PROFILE_UNSUPPORTED`, `PROFILE_REVISION_AMBIGUOUS`, `SCOPE_CONTEXT_MISSING`,
`MAPPING_COVERAGE_GAP`, `MAPPING_CONFLICT`, `NATIVE_SOURCE_CONFLICT`,
`CLASSIFICATION_UNKNOWN`, `CLASSIFICATION_ROUTE_UNSUPPORTED`, `AUTHORITY_UNVERIFIED`,
`TAILORING_PERMISSION_MISSING`, `TAILORING_IMPACT_MISSING`, `TAILORING_IMPACT_STALE`,
`CLASSIFICATION_APPROVAL_MISSING`, `CHANGE_REQUEST_ACCEPTANCE_MISSING`, `REUSE_BINDING_STALE`, `INVENTORY_INCOMPLETE`,
`EXTERNAL_OWNER_MISSING`, `CLOSURE_LIMIT`, `OUTPUT_SOURCE_ROOT`, `OUTPUT_ALIAS`.
Input syntax/type errors reuse existing conventions where semantically appropriate.
Each includes pointer, affected scope/instance/source refs, explanation and required action.
These codes are diagnostic vocabulary, not native artifact statuses or engineering gate results.
