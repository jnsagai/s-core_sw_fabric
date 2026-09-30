# Research: trusted evidence and authenticated human gates

This design uses the completed 002/004 identities, the proposed forward contracts in
`specs/001-native-process-catalog/contracts/forward-boundaries.md`, ADRs 0007/0012/0013,
and the pinned runtime source review. External guidance is informative, not a replacement for
S-CORE process or owner policy. No protected production issuer or identity provider is selected.

## Verify origin separately from content integrity

**Decision:** Use a versioned signed receipt envelope over canonical evidence or decision bytes.
A verifier accepts only an exact issuer key and role from an independently supplied, reviewed trust
profile; it checks signature, payload kind, domain, subject, scope, policy, and validity. SHA-256
self-digests and file paths check integrity and location only. The fabric contains public-key
verification, never production signing keys or a signing endpoint. Ed25519 is the version-1
signature algorithm; the implementation phase pins a compatible `cryptography` release and lock.

**Rationale:** [ADR 0007](../../docs/architecture/0007-trusted-evidence-and-authenticated-human-decisions.md)
explicitly rejects signed-looking YAML and actor strings as proof. The official
[cryptography Ed25519 API](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/ed25519/)
provides public-key verification. [SLSA verification guidance](https://slsa.dev/spec/v1.2/verifying-artifacts)
likewise separates signature verification from matching the authenticated builder and actual
subject against policy. This is an inference for the fabric design, not a SLSA compliance claim.

**Alternatives considered:** A hash or HMAC in the agent workspace cannot establish an independent
origin. A Fabro interview answer is run data. A generic shell verifier adds an unbounded executable
boundary. Hard-coding an identity provider would invent production authority.

**Selected implementation pin:** `cryptography==50.0.1` (Python >=3.9, license expression
`Apache-2.0 OR BSD-3-Clause`) and its CFFI/pycparser transitive dependencies are locked in
`uv.lock`. `uv sync --frozen --offline` resolved all 18 packages from the local cache on
2026-09-29. This only validates dependency availability, not protected issuer deployment.

## Keep fixture trust in a separate domain

**Decision:** Every trust profile and receipt carries an exact `assurance_domain` of
`fixture_contract` or `production`. The checked-in test key is only permitted in
`fixture_contract`; a result produced there may demonstrate a passing gate algorithmically but
cannot satisfy a `production` predicate or be relabelled. A production profile requires
owner-supplied trust roots, issuer scope, role assignments, identity assurance and protected
collector/submission topology before any real pass. Missing inputs block.

**Rationale:** The current workspace is agent-writable. It cannot prove an independent protected
runner or human identity. This domain separation makes FAB-020 and FAB-023 enforceable while
allowing deterministic contract tests. [NIST SP 800-53 AC-5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final)
describes defined separated duties and access authorizations; owner policy must name the actual
duties and principals here.

**Alternatives considered:** Calling a local developer signature a production approval would be
misleading. Blocking all fixture passes would make positive gate logic untestable. Auto/replay
Fabro actor metadata is explicitly untrusted per `docs/discovery/runtime-source-review.md`.

## Bind one immutable subject closure without approval cycles

**Decision:** Construct a `SubjectManifest` from the sealed 002 plan and exact 004
candidate/report/snapshot/profile/validator identities plus their declared file and obligation
closure. Include source, process, toolchain, artifact/template/metamodel, trace, policy, and trust
profile identities where applicable. Hash canonical bytes excluding the manifest's digest,
evidence, and decisions. Evidence and decisions reference the resulting subject digest plus their
own precise scope. Gate evaluations bind evidence and decision digests separately.

**Rationale:** This prevents approval self-reference while ensuring every relevant baseline can
invalidate current use. A candidate with `trace_validation: not_requested` or a missing report
remains a complete structural subject but cannot satisfy a gate requiring trace evidence.

**Alternatives considered:** Names, paths, or a single repository commit omit tool/policy changes.
Including approvals in the subject hash creates a digest cycle. Trusting embedded 004 capability
flags would promote structural validation into acceptance.

## Treat 002 decision references as claims, not authenticated decisions

**Decision:** `schemas/decision-references.schema.json` and 002 planning references remain
unverified inputs. The 005 decision contract requires a separate authenticated receipt and
reviewed role/independence policy. A protected issuer attests an actor identifier and
authentication method; the fabric checks the issuer's policy authority, not a mere `claimed_actor`
field. Revocation, expiry, supersession, conflict, and conditional outcomes are evaluated at use.

**Rationale:** 002 reports `AUTHORITY_UNVERIFIED`. [ADR 0007](../../docs/architecture/0007-trusted-evidence-and-authenticated-human-decisions.md)
requires the approval channel to be unavailable to engineering agents. Human identity, role,
independence and issuer authority must be checked independently of a workflow's text fields.

**Alternatives considered:** Treating CODEOWNERS, repository write access, a recorded display name,
or an interview as approval would bypass explicit authority and independence.

## Separate observation, eligibility, and gate outcome

**Decision:** A signed result can be authentic yet ineligible because its subject, scope, policy,
issuer, transformation, freshness, tool, or obligation binding is wrong. Record those checks
individually. `fail` is a measured unmet predicate; `blocked` is missing or unusable authority/input;
`not_evaluated` means no evaluation; `stale` describes prior results on a changed baseline;
`not_applicable` requires an eligible scoped tailoring decision; `pass` requires a non-empty
complete expected set with all mandatory predicates eligible and satisfied. A deterministic
technical success cannot substitute for human semantic review.

**Rationale:** The distinctions come from the 001 forward contract and constitution. Negative and
unknown conditions need actionable reasons rather than implicit success. A gate result is scoped
and does not grant module/platform readiness or release.

**Alternatives considered:** A boolean result loses missing/timeout/stale meaning. Counting only
observed evidence makes an empty set pass. Treating signature validity as evidence adequacy would
skip policy and engineering review.

## Use fixed assessment time and retain immutable history

**Decision:** Historical evaluation uses an explicit `as_of` instant and stores the authenticated
time basis. The portable verifier can reproduce that historical outcome. A *current* production
pass additionally requires a protected evaluator time receipt or equivalent trusted time source;
agent-supplied time cannot extend validity. Changed subject/policy/trust root/decision/evidence
identity makes prior gate output stale for current use without changing its historical bytes.
Unknown dependencies widen review or block.

**Rationale:** An expiry check based only on a user-supplied clock can be rolled back. A moving
wall clock inside semantic JSON also breaks relocation and deterministic replay. This follows
[ADR 0012](../../docs/architecture/0012-baseline-hashes-impact-and-invalidation.md).

**Alternatives considered:** Rewriting prior records destroys audit history. Silently reusing a
previous pass ignores changed baselines. Treating no known dependency edge as no impact is unsafe.

## Export an independently verifiable record

**Decision:** Publish canonical JSON plus a readable report with exact receipts, source closures,
policy, trust roots or immutable trust-root identities, raw-result digests, predicate matrix,
reasons, limitations and history references. Referenced external bytes must be content-addressed
and available to the verifier; absent bytes block. Keep the verifier independent of Fabro. Signed
receipts remain immutable inputs; evaluation output is a derived record, not a newly signed origin.

**Rationale:** A reviewer must be able to rerun policy checks and distinguish factual receipts from
fabric interpretation. [SLSA VSA](https://slsa.dev/spec/v1.2/verification_summary) is an
informative example of binding verifier, policy and input attestations, not an adopted format or
compliance claim.

**Alternatives considered:** A link to a temporary CI page lacks durable bytes. A report that says
`trusted: true` without its verification inputs cannot be independently checked. A Fabro database
export would make the engineering record depend on runtime access.

## Explicit unresolved production dependencies

Owner-controlled production inputs are the selected identity provider, protected collector and
human-submission service, role/independence assignments, trust-root lifecycle, permitted import
issuers, retention, time source, target-specific gate policy, and review of authority/profile
sources. These are not product ambiguities to fill by guesswork. The 005 contract and fixture-domain
implementation can be built and tested now; real production approval remains blocked until these
inputs exist. This is a design limitation, not a waived acceptance gate.
