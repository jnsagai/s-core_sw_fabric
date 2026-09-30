# Proposed assurance contract v1

Status: planning contract for Increment 005. The 002 plan and 004 native candidate/report remain
separate immutable inputs. This contract does not create a production identity provider, collector,
human submission service, Fabro runner, tool qualification, or release authority.

## Public CLI

```text
score-fabric assurance subject --request REQUEST.yaml --out SUBJECT.json [--json]
score-fabric assurance evidence --request REQUEST.yaml --out RESULT.json [--json]
score-fabric assurance decision --request REQUEST.yaml --out RESULT.json [--json]
score-fabric assurance gate --request REQUEST.yaml --out ASSESSMENT.json [--json]
score-fabric assurance verify --assessment ASSESSMENT.json --trust-context CONTEXT.json [--json]
```

Each request carries exact versioned refs, transport SHA-256 and semantic digest where defined,
logical input roots, `output_root`, selected domain and finite limits. `subject` validates 002/004
closure and emits its canonical manifest. `evidence` and `decision` validate one or more signed
receipts and emit classified eligibility reports. `gate` derives the complete expected predicate
set and produces one portable assessment. `verify` replays an assessment from its declared bytes
without Fabro. No command signs a receipt, grants a role, or submits a human decision.

| Exit | Meaning | Output behavior |
| --- | --- | --- |
| 0 | Subject/eligibility operation succeeds; gate outcome is `pass` in its declared domain; or `verify` faithfully reproduces the recorded outcome | Complete validated output published atomically |
| 1 | Well-formed domain input is ineligible or gate outcome is non-pass; `verify` finds a semantic/eligibility/outcome mismatch | Bounded classification or non-pass assessment may be published; prior valid output never replaced by a partial result |
| 2 | Malformed, unsupported, unsafe, integrity-invalid, signature-verifier unavailable, or infrastructure input | No output replacement; bounded diagnostic |

`--json` returns a bounded summary with domain, scope, subject/policy digests, outcome, reasons and
path; it does not echo raw evidence or credentials. `verify` exit 0 means the historical record is
internally reproducible, even when its recorded gate outcome is `blocked` or `fail`. A current
production claim requires a separate current-use evaluation with a trusted time basis.

## Authority order and boundary

1. Pinned native source/process/metamodel and reviewed target policy determine engineering
   obligations, as represented by exact 002 and 004 identities.
2. Owner-provisioned trust roots, protected issuer topology and reviewed role/independence policy
   determine evidence and decision origin eligibility.
3. Exact signed receipts state observations and human acts within their issuer's authority.
4. Derived 005 reports calculate current eligibility and scoped gate outcomes.

A request, agent-writable profile, valid schema, content hash, filename, CI URL, Fabro actor field,
workflow success, or 002 claimed decision reference cannot promote itself to a higher level.
Production trust roots must be provisioned from a protected context independent of the target and
agent workspace; if this precondition cannot be established, a production gate is `blocked`.
Fixture roots and their receipts carry `fixture_contract` and cannot be used in `production`.

## Subject construction

The subject loader revalidates each referenced 002 and 004 version, self-digest, transport hash,
file closure, candidate/index/native-receipt/report binding, selected profiles, source locks and
expected obligation identities. When a report is attached, its trace profile is an explicit
transport- and semantic-digest-bound input; the loader recomputes obligations, coverage,
observed traces, findings, and status from the selected 002 plan, 003 workflow package, 004
native index, and trace profile. All known plan instances and report obligations are included before
any observed evidence is read. It records missing 004 trace evaluation as an explicit limitation.
The subject digest covers canonical identity fields only, excluding its own digest, evidence,
decisions and later gate results. Changing a tool, source, template, metamodel, profile, policy,
trust root, candidate or obligation cannot reuse the same current-use subject.

A 004 `passed` native build, trace report or `not_evaluated` capability does not imply trust or
engineering acceptance. No 004 artifact is rewritten to update its capability fields.

## Signed receipt verification

The verifier accepts exactly Ed25519 version-1 receipts. It rejects unknown algorithms, receipt
kinds, domains, fields, key IDs, duplicate IDs, invalid key lengths, malformed base64, unsupported
contract versions and noncanonical payloads. The signed message is a fixed ASCII domain prefix,
receipt schema version, payload kind and canonical receipt fields except the signature/digest;
those fields include the payload digest. The implementation must publish test vectors to prevent
ambiguous encodings or cross-kind replay. Verification checks the actual payload digest, signature,
issuer key, key validity/revocation, permitted kind/scope/domain, required receipt sequence and
protected-origin policy. A valid signature from an unapproved issuer is authentic to that key but
ineligible for the gate.

The trust profile cannot authorize its own key. Production roots, role assignments, revocations and
profile approval are anchored outside agent-writable inputs. For portable review, the assessment
includes the exact public verification material or immutable retrieval identities and evidence of
its protected provenance. Missing root context blocks the relevant conclusion; the verifier never
pretends an embedded key is an independent trust anchor.

## Evidence and import eligibility

A `protected_observed` result must bind the exact subject, inputs, tool executable/version,
process/policy/profile baselines, expected obligations, collector, start/end, termination, raw
output hashes and bounded measurements. Its trusted collector receipt must be valid and permitted.
An `imported_verified` result additionally keeps original issuer receipt, original subject/result,
every transformation and a reviewed import rule for evidence type, scope, age and issuer.
Transformations cannot erase the original class or extend scope. `fixture_replay`, simulated,
model-generated and `agent_assertion` records remain available as context but never satisfy a
production trusted predicate. A timeout, crash, absent or truncated result, missing extraction, or
unknown measurement is blocked rather than success.

Signing keys and approval credentials must be unavailable to engineering agents and target
subprocesses. The 005 verifier checks receipts; deployment of isolated collector/submission
services is an external operational prerequisite. A local single-user run with test keys does not
claim this isolation.

## Human decision eligibility

A decision is eligible only when its receipt authenticates the exact payload through an authorized
human decision issuer and the selected policy resolves actor identity, role assignment, authority
source, required independence, subject/scope/gate/obligation coverage, rationale, conditions,
validity and any later withdrawal/supersession. The decision origin must attest authentication of
the person; a role string inside the signed payload is insufficient unless the issuer is trusted to
assert roles or a separate protected role registry corroborates it. Conflicting live decisions,
unmet conditions, expired or revoked authority, and a withdrawn decision block an unqualified pass.
A rejection or request for changes remains a measured negative decision.

An applicability/tailoring decision must identify the exact obligation and denominator treatment.
It remains visible as `not_applicable`, never deleted from the expected set. A whole-gate
`not_applicable` outcome is allowed only if reviewed policy and authenticated decision explicitly
dispose of that whole gate and scope. Otherwise eligible tailored predicates retain their own
state while the remaining mandatory predicates are evaluated.

## Gate evaluation and precedence

Gate policy names a source-cited, non-empty expected set, selected subject/scope, deterministic
checks, trusted evidence types, human roles/independence, allowed exclusions, and next routes.
The evaluator freezes that set before reading evidence/decisions, evaluates each predicate
independently and records all unmet IDs. A `pass` requires every mandatory predicate satisfied or
explicitly tailored as policy allows, all origin/authority checks eligible, and no unresolved
conflict/condition. Fixture passes are labelled and cannot imply production acceptance.

| Condition | Predicate state | Aggregate treatment |
| --- | --- | --- |
| Never evaluated | `not_evaluated` | `not_evaluated` only when no evaluation began |
| Prior assessment on changed bound identity | `stale` | `stale` when the request is to reuse that result |
| Missing/unknown/untrusted/timeout/unsupported mandatory input | `blocked` | `blocked`; record any independent measured failure too |
| Complete eligible measurement or human rejection fails requirement | `failed` | `fail` if no mandatory predicate is blocked |
| Eligible exact tailoring | `not_applicable` | Remains visible; whole-gate N/A only with whole-gate authority |
| Every mandatory predicate resolved satisfactorily | `satisfied` | `pass` for the exact subject, domain and scope only |

This precedence means an incomplete assessment is `blocked` even if a separate measured predicate
failed; the failure remains explicit in the predicate matrix. An incomplete expected denominator
never becomes an empty pass. Each non-pass carries stable reason code, subject/obligation ref and
required action. Policy can make a gate stricter but cannot redefine negative states as success.

## Time, freshness and immutable history

Every evaluation has an explicit `as_of` and time-basis reference. Historical replay checks the
original authenticated time basis and reconstructs the original outcome. A current production pass
requires a protected evaluator time receipt valid for that assessment; agent-supplied time cannot
revive an expired decision or trust key. Changed subject, source, process, tool, profile, trust root,
policy, expected set, evidence, decision, condition or validity makes an affected prior result
stale or ineligible for current use. A `no_impact` decision is permitted only when the selected gate policy names a reviewer role,
authority reference and exact allowed changed paths. Its signed `baseline_change` binds the prior
assessment, old/new subject and policy digests, and the complete sorted changed-path set. The
reviewer must have a corroborated role, identity provider, independence result, exact gate and
obligation scope, and valid receipt and time. A policy digest may change only because each
predicate's `subject_ref` is mechanically rebound from the old subject to the new one; other
policy, trust, evidence, decision, or time changes cannot use this narrow path. The review narrows
impact reporting to the exact changed references but leaves every old subject-bound record
marked for recheck and the prior gate `stale`. The standalone `decision` operation cannot classify
a `no_impact` record as eligible without that old/new freshness context. Unknown dependencies widen the scope or
block. Prior signed receipts and gate reports remain byte-unchanged.

## Portable verification and safe publication

An assessment contains its subject closure, policy/trust identities, evidence/decision records,
receipt and raw-output references, predicate matrix, reasons, limitations and prior-history refs.
External referenced content is identified by immutable digest and must be available to an offline
verifier. Verification recomputes nested digests, checks signatures against independently supplied
trust context, re-evaluates scope/authority/freshness and reproduces the gate outcome. `verify`
requires neither Fabro nor a network service. If a protected root, time receipt, raw result, or
original imported attestation is unavailable, the associated conclusion is blocked. A readable
report explains exactly that limitation.

Every input and output is bounded; local roots are operational transport data. Read-only inputs,
protected source roots and output destination cannot alias by resolved path or inode. Write to a
same-directory temporary file, flush and atomically replace only after complete validation. A
malformed or interrupted operation cannot replace a prior valid assessment.

## Stable reason codes

| Code family | Representative codes | Required action |
| --- | --- | --- |
| Subject/closure | `SUBJECT_MISMATCH`, `CLOSURE_MISSING`, `OBLIGATION_SET_INCOMPLETE` | Restore or rederive exact 002/004 closure |
| Origin/signature | `ORIGIN_UNVERIFIED`, `SIGNATURE_INVALID`, `ISSUER_UNTRUSTED`, `DOMAIN_MISMATCH` | Obtain a protected eligible receipt and trust context |
| Evidence | `EVIDENCE_UNTRUSTED`, `RESULT_UNKNOWN`, `RESULT_TIMEOUT`, `IMPORT_RULE_MISSING` | Run or import an eligible measurement |
| Human authority | `ACTOR_UNAUTHENTICATED`, `ROLE_UNAUTHORIZED`, `INDEPENDENCE_FAILED`, `DECISION_CONFLICT`, `CONDITION_UNMET` | Route to an authorized independent human or resolve conflict |
| Gate/freshness | `PREDICATE_FAILED`, `PREDICATE_BLOCKED`, `ASSESSMENT_STALE`, `TIME_BASIS_UNTRUSTED`, `TAILORING_UNVERIFIED` | Address the named predicate or reassess current baseline |
| Format/limits | `VERSION_UNSUPPORTED`, `FIELD_UNKNOWN`, `LIMIT_EXCEEDED`, `PATH_ESCAPE` | Correct or upgrade the record within declared bounds |

Codes are stable; messages may add context but cannot alter the outcome. The public report always
states gate and assurance domain, exact scope, limitations, and that module/platform readiness and
release remain unevaluated in Increment 005.
