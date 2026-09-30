# 002 proposed data model — v1

These shapes are design contracts, not implemented schemas or upstream APIs. Exact native
fields remain owned by the pinned catalogue. All normative envelopes reject unknown fields;
versions use exact integer checks. A missing value is represented explicitly and is never
converted to a default safety/security judgment.

## Intake and scope

| Entity | Required content and relationships |
| --- | --- |
| Intake | schema_version, target_namespace, change id/intent, target repository baselines, scopes, affected scopes/interfaces, constraints, assessment intent, profile/catalogue/mapping/inventory/decision file refs, role assignments, planning output boundary |
| RepositoryBaseline | repository namespace, canonical repository identity, full commit, declared snapshot/content binding where applicable; dirty/untracked content cannot masquerade as the commit |
| ScopeNode | stable scope key, kind, id, owning target namespace, parent/context refs, affected-member refs, development origin, language/toolchain/environment and per-scope classification facts |
| DeclaredFact | value or null, state known/unknown, rationale and source/decision refs; presence of a value does not establish accepted authority |
| RoleAssignment | native role ref, declared person/external authority ref, scope, independence constraints; assignments are proposals until verified |
| LocalPaths | operational input locations, declared reference roots and output root; excluded from semantic digest, always containment-validated |

Scope key is `(target_namespace, scope_kind, scope_id)`. Kinds are feature, component,
module and platform. Module/platform ownership is explicit and acyclic, with at most one
owning parent per containment level. Feature membership is a separate relation and may span
components in several modules. Membership must not be inferred from directory layout.
A missing required parent is a blocker; an external parent must be declared with owner and
boundary. Conflicting or cyclic ownership is malformed input.

Development origin distinguishes `new`, `reused`, `modified_reused`, `unknown`; an OSS
attribute supplements origin and does not replace classification. Native Q/QR/NQ values are
version-specific reuse-route facts with separate classification record, Safety Manager approval
and accepted containing change-request references; each binds its own exact subject/baseline. Safety classification and security relevance are distinct.
Required facts can differ by scope; no automatic child inheritance may lower obligations.

## Profile, mapping and coverage

| Entity | Required content and validation |
| --- | --- |
| PlanningProfile | id/version, exact catalogue/metamodel/process bindings, native revision selections, supported language/toolchain/environment and classification combinations, normalized mapping digest, limits, coverage and review status, source refs |
| MappingRule | stable rule id, native workproduct ref/version, source origin+rationale, applicable scope kinds, named target selector, finite predicates, explicit purpose definitions, dependency rules, template/review refs |
| CoverageEntry | native workproduct ref plus scope key, considered rule IDs, selected/outside_scope/unresolved result, source-backed reason, instance keys and blockers |
| DependencyRule | owning rule/purpose, required rule/purpose and named target-scope selector, origin; no executable selector or scheduling semantics |

Profile support describes tested planning coverage, not engineering qualification. The initial
review-draft profile must retain pending review and unsupported combinations. A profile cannot
claim its own approval with a boolean. Mapping completeness is measured against all native
entities of type `workproduct` and all declared scopes, not just rules that happen to exist.

`outside_scope` is a coverage result for a native scope/structural condition or explicit
non-selected native revision, with a cited reason. Revision selection does not remove the
active logical obligation. It is not `tailored_out`. A target-specific exception must stay in the expected-instance
set with a tailoring proposal, even when a future authorized decision resolves it.

## Instance and bindings

Logical identity is the tuple:

~~~text
(target_namespace, native_source_id, native_work_product_id, scope_kind, scope_id, purpose)
~~~

Use canonical structured serialization of the tuple. A convenience instance ID is SHA-256
of that canonical encoding; store the tuple as well and reject any key/tuple disagreement.
Native version, source commit, source namespace-to-repository binding and target/catalogue
baselines belong in bindings. A changed native revision preserves logical identity but changes
plan content. Rebinding a namespace to another repository requires explicit migration review.

| Entity | Required content and validation |
| --- | --- |
| InstanceBinding | exact native source/ID/version, catalogue digest, SourceRef, target baseline vector, rule/profile binding and subject/artifact refs |
| WorkProductInstance | identity, bindings, requesting scopes/origins, applicability, requested/effective disposition, rationale, template refs, required verification/reviews, inventory bindings, dependency keys and blockers |
| ReviewRequirement | native role/workflow/checklist refs where available, subject instance keys, purpose and independence; missing required information remains unresolved |
| ExternalObligation | stable instance key, named owner, interface, evidence owed, boundary and rationale; satisfaction is always not_evaluated in 002 |

Purpose is always explicit. `primary` is allowed only where the mapping defines a singleton;
review purposes such as plan, package, FMEA and DFA cannot be silently merged. When different
rules expand to one shared instance, bindings must agree and origins/requesting scopes are
unioned deterministically. A disagreement produces a mapping conflict, not last-rule-wins.

## Inventory, decisions and dispositions

| Entity | Required content and validation |
| --- | --- |
| ArtifactInventory | schema_version, declared scope/baseline coverage and complete/partial state, artifact records; missing entries in a partial inventory do not prove absence |
| ArtifactBinding | exact instance tuple, native document refs, target repository/path, commit/content digest, declared change/impact rationale, claimed acceptance refs and dependency bindings |
| DecisionReference | decision class, claimed actor/role/outcome, rationale, exact subject/scope, source/process/target bindings, permission basis, tailoring impact-analysis ref when applicable, receipt ref and origin; no caller-set trusted flag |
| DecisionAssessment | derived availability/verification state and reason; production 002 yields unverified/unavailable, never accepted from a local declaration |
| Applicability | required/unresolved for instances, with rationale/origins; coverage separately uses selected/outside_scope/unresolved; target tailoring remains an instance proposal |
| Disposition | requested and effective values from create/update/reuse/tailored_out/external_obligation/unresolved, plus unmet prerequisites |

Creation needs known absence in complete inventory; update needs an existing exact binding
and explicit change reason. Neither operation marks an artifact accepted. Unchanged existing
work cannot silently become reuse: exact accepted revision, applicability and freshness are
required. `modified_reused` retains reassessment. Pending reuse/tailoring requests keep effective
`unresolved`; the 005 verifier is a future integration, not implemented here. External work
remains owed even when ownership is known.

## Plan result and diagnostics

PlanResult contains schema_version, normalized semantic input bindings (transport file hashes live only in the CLI receipt),
profile/mapping/catalogue identities, scope set, coverage, sorted instances/dependency edges, findings, closure_complete,
planning_status (`complete` or `blocked`), plan_kind (`draft`), engineering_readiness
(`not_evaluated`) and digest. `complete` means only the bounded draft planning predicates have
no unresolved findings; it never changes plan_kind or readiness. Source conflicts, unknown
classification or pending authority make affected planning blocked.

Each finding carries stable code, affected scopes/instance keys/native refs, input pointer,
reason, source/decision refs and required action. Where expansion cannot produce an instance,
its coverage finding must still exist. Do not represent an empty partial result as complete.

## State changes

Each invocation derives a new immutable result; there is no workflow/run state machine.
An inventory change may change create/update/requested reuse; baseline changes alter bindings.
Neither a successful invocation nor a changed status string advances human acceptance. Historic
plan files are immutable inputs if selected; replacement of the chosen output path is atomic.
