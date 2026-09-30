# Research: native artifact traceability

This research uses only the pinned local source baseline and completed 001–003 contracts. It does
not change or build a protected reference checkout. Production policy review remains pending.

## Keep native source and native export as a reconciled authority pair

**Decision:** Treat target RST and its pinned configuration as authoritative. Build a derived index
only after exact directive/source spans reconcile with the native Sphinx-Needs `needs.json` export.
Each live wrapper/need must agree on ID, type, version, status, options, relations, source file, and
line. Export-only or source-only live records are failures unless the profile explicitly identifies
a supported imported external need.

**Rationale:** RST preserves prose, comments, layout, and engineering ownership; `needs.json`
provides the native parser's resolved semantic view. Reconciliation detects both scanner loss and
native build/schema behavior without promoting JSON into a second requirements authority.

**Alternatives considered:** Parsing only RST would duplicate Sphinx-Needs semantics. Indexing only
`needs.json` loses exact source text and safe edit spans. Treating JSON as the editable store would
violate native authority and make RST a lossy export.

## Pin the exact metamodel, templates, and build stack

**Decision:** Version 1 binds docs-as-code 8.2.0, process-description 2.1.2, Python 3.12,
Sphinx-Needs 8.3.1, Bazel 8.7.0/Bazelisk 1.29.0, the locked module graph, and metamodel SHA-256
`fe6a3b6af5ea69271e53c57e3a1694dc69d6ff3df16bd1505dc7242db9976290`.
Representative templates come from module-template commit
`c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d`, including component FMEA
`5cf246c79eb28b1bae5960df489856b2759a8d4ef190d7c83caa5c86de9689c2`, component DFA
`182aed5e2cbc7cdf421219f6e913894e271adc2ce854493a22d02278ea2864ad`, and module security plan
`5e1958c1ba01a33e2111e8f6745b14913287a38f197fec64fc426397d1fe6218`.

**Rationale:** Native type/status/link rules and templates evolve together. Exact pins make candidate
identity, build evidence, and later compatibility migrations reviewable.

**Alternatives considered:** Following `main`, accepting any compatible-looking exporter, or using
handwritten generic templates would make semantics time-dependent and could emit unsupported fields.

## Use a bounded lossless scanner rather than a general formatter

**Decision:** Implement a UTF-8, line-preserving scanner for the profiled RST directive subset. It
records byte/line spans, indentation, ordered option spans, content spans, enclosing literal/code
blocks, and original content digests. It never reflows a whole document. Native export/build remains
the final parser and compatibility oracle.

**Rationale:** The brief permits parser-aware or tightly scoped edits and requires unrelated prose,
comments, IDs, decisions, and links to survive. Exact-span replacement gives a provable unchanged
complement without adding or pretending to implement all of docutils/Sphinx.

**Alternatives considered:** A regex-only global replacement can edit examples and comments.
docutils round-trip rendering is not lossless and is not an existing runtime dependency. A complete
RST parser/formatter is unnecessary scope.

## Never treat directives inside literal examples as live needs

**Decision:** The scanner tracks indentation and literal-producing directives such as `code-block`,
`parsed-literal`, and literal blocks introduced by `::`. Need-looking lines inside them remain
opaque content. The native export must contain no corresponding live record.

**Rationale:** Actual FMEA/DFA templates show example `comp_saf_fmea` and `comp_saf_dfa` directives
inside `code-block:: rst`. Indexing or editing them as live needs would fabricate analyses.

**Alternatives considered:** Selecting directives by their text alone creates false artifacts.
Dropping examples loses useful native template guidance.

## Realize explicit content; do not generate engineering semantics

**Decision:** `create_document` copies an exact pinned template and applies only declared,
profile-authorized placeholder/directive operations. `update_directive` targets one source-qualified
native identity and expected preimage digest. Supported edits set an existing option/content, add or
remove a typed link, or insert an explicitly supplied complete need at an exact anchor. Deletion and
free-form search/replace are outside v1. Every value comes from the request and cited policy; the
adapter never calls a model or invents text, classifications, statuses, IDs, or relations.

**Rationale:** This makes edit authority and review scope finite. Exact preimages prevent stale-base
updates and stable identities prevent title/path heuristics.

**Alternatives considered:** Templating an entire target tree risks uncontrolled substitution.
Arbitrary patches are hard to constrain and source-map. Model-authored content belongs behind later
bounded workflows and human review, not inside this deterministic adapter.

## Model candidate output as a sealed overlay on an immutable snapshot

**Decision:** A candidate package contains every new/changed UTF-8 native file, unchanged file
records for the complete target snapshot, edit records, source map, derived index/report, native
validation receipt, and canonical self-digest. Trace and impact reports are attached only when their
explicit operations run; candidate creation records `trace_validation: not_requested` otherwise. The base snapshot binds repository/commit, relative
paths, byte counts, and hashes. Materialization copies the bounded snapshot to a disposable tree and
applies the overlay; production apply/merge is outside 004.

**Rationale:** An overlay is portable with immutable base references, keeps native RST exact, avoids
copying unrelated binary assets into JSON, and cleanly distinguishes generated drift from reviewed
source/profile changes.

**Alternatives considered:** Mutating the target violates scope. Publishing a mutable directory has
weak replacement semantics. Storing only patches makes review and hashing dependent on patch tools;
storing only a derived JSON model loses native bytes.

## Validate with an isolated locked native build and fresh export

**Decision:** Copy only the declared target/build closure to a fresh directory, apply the overlay,
invoke fixed argv for locked `needs_json` and `docs_check` targets with isolated HOME/cache, cap
time/output, hash the fresh export/logs, then re-index and reconcile. Require both native commands and
stricter fabric checks to pass before candidate publication.

**Rationale:** The pinned toolchain has already produced a genuine process export in increment 001.
Native success proves actual syntax/metamodel compatibility; the fabric layer still enforces
expected obligations, source authority, safe edits, and preserved content that native syntax alone
does not prove.

**Alternatives considered:** Fixture-only parsing is not native evidence. Building protected source
creates side effects. Trusting a pre-existing export would miss candidate changes.

## Derive obligations through reviewed mappings, never filenames or workflow shape

**Decision:** Establish artifact obligations from every applicable sealed-plan instance. A reviewed
artifact mapping binds native work-product/purpose/scope to required wrapper/need classes, templates,
and identity policy. A reviewed trace profile classifies every 003 action `expected_output` and data
destination as native artifact, non-native record, or external boundary and binds applicable native
trace paths. Missing or conflicting classification blocks the expected set.

**Rationale:** Package output strings are obligations/boundaries, not proof or self-describing native
IDs. Explicit rules retain the upstream/configuration/human origin required by the constitution.

**Alternatives considered:** Treating every output path as a native artifact overcounts. Ignoring
package outputs loses declared obligations. Inferring native identity from workflow node IDs or prose
would transfer execution representation into native authority.

## Compute coverage from the expected set

**Decision:** Freeze the expected set before inspecting target relations. Each metric reports the
full denominator, satisfied numerator, exclusions with authority, mismatches, and unresolved items.
Absent artifacts/links remain denominator items. Mandatory unresolved or mismatched obligations make
trace validation fail; partial verification is reported distinctly and satisfies only rules that
explicitly permit it.

**Rationale:** Deleting an artifact or link must lower coverage rather than improve it. Explicit
partial/exclusion semantics avoid percentage manipulation.

**Alternatives considered:** Link-discovered denominators reward deletion. A single global percentage
hides scope/path gaps. Counting wrong-type or partial links as complete produces false closure.

## Take native relation semantics from the pinned metamodel

**Decision:** Trace rules name exact native fields and permitted source/target types from the pinned
metamodel. Version 1 exercises `realizes`, `derived_from`, `satisfied_by`, `belongs_to`, `fulfils`,
`violates`, `mitigated_by`, `fully_verifies`, `partially_verifies`, `contains`, `evidence`, and
`covers` only where the selected type declares them. Direction and exact version selector are
preserved; narrative `:need:` roles do not become normative links.

**Rationale:** The metamodel already distinguishes allocation, realization, mitigation, and
verification. Native names must not be invented or normalized into generic edges.

**Alternatives considered:** A proprietary relation vocabulary would need lossy translation. Treating
backlinks, prose references, and forward links as interchangeable breaks direction and type checks.

## Validate wrappers and contained needs independently and together

**Decision:** A profile declares which artifact classes require exactly one `document` wrapper per
managed file. Containment is the reconciled native document/source association, not RST indentation.
The wrapper validates its own `draft|valid|invalid` status and `realizes` link; every contained need
validates its exact type-specific fields, links, and status. A wrapper cannot override child results.

**Rationale:** The pinned metamodel permits `draft` for `document`, but feature/component requirements
and FMEA/DFA needs accept only `valid|invalid`. Actual templates contain draft wrappers and literal
example children, so validation must keep these concepts separate.

**Alternatives considered:** Propagating wrapper status to children writes illegal values. Treating a
document build as proof that all child analysis is valid masks unresolved work.

## Propagate impact conservatively without rewriting history

**Decision:** Diff indexes by stable source-qualified identity and semantic fingerprint. Traverse
reverse native dependencies, then apply source-cited profile rules for shared resources, allocations,
interfaces, assumptions, analysis coverage, template/metamodel changes, and newly expected subjects.
Unknown dependencies and new unlinked subjects expand review scope or block. Prior accepted revision
facts remain immutable; staleness belongs to the candidate assessment.

**Rationale:** Link traversal alone cannot find a new missing relationship. Conservative rules satisfy
the constitution's transitive/new-dependency requirement while keeping acceptance human-owned.

**Alternatives considered:** Only direct neighbors miss transitive effects. Mutating old statuses
falsifies historical decisions. Treating no link as no impact is unsafe.

## Separate semantic diff from direct drift

**Decision:** Semantic diff compares two valid indexes/candidates by categories: baseline, wrapper,
need, option/status/classification, content, relation, containment, obligation, coverage, impact,
template/profile, and native-validator identity. Drift verifies package/file hashes and optionally
rederives the candidate from its exact request/snapshot. A changed generated file is never adopted as
source authority.

**Rationale:** Reviewers need meaningful changes without formatting noise, while integrity checks must
still expose any byte edit.

**Alternatives considered:** Raw text diff alone obscures meaning. Semantic comparison alone can miss
tampering in non-semantic text. Accepting drift creates a parallel edit route.

## Use measured finite limits and canonical identity

**Decision:** Version 1 limits are those recorded in the plan: 64 MiB control/package and declared
target content, 10,000 files, 2 MiB text file, 100,000 native entities, 500,000 relations, 100,000
obligations, 10,000 edits, 20,000 findings, 8 MiB native output, and 1,800-second native validation.
Canonical JSON uses sorted keys, compact finite values, explicit nulls, defined set ordering, and one
newline. Digest excludes only itself and operational local paths.

**Rationale:** The pinned S-CORE docs baseline is 436 files/13.9 MiB with 1,576 directive starts, so
these ceilings leave growth headroom while bounding hostile inputs and acceptance tests.

**Alternatives considered:** Unlimited inputs are unsafe. Limits based only on small fixtures would
not cover the inspected target. Host paths/timestamps/random IDs would break relocation equivalence.

## Expose explicit CLI results and preserve prior outputs

**Decision:** Provide `artifact index`, `candidate`, `validate`, `trace`, `diff`, and `drift` commands.
Exit 0 means the requested structural/coverage operation succeeded, exit 1 means well-formed domain
content failed semantic/coverage/drift checks or a comparison found change, and exit 2 means malformed,
unsupported, unsafe, or unavailable input/infrastructure. Blocked trace reports may be published for
review; invalid candidate/index outputs never replace prior valid files.

**Rationale:** This matches established catalogue/planner/compiler conventions while preserving useful
gap reports and keeping candidate publication fail-closed.

**Alternatives considered:** One exit code hides user-correctable domain failures versus tooling/input
errors. Always writing candidates makes file existence look like validity. Suppressing blocked trace
reports makes gaps hard to review.
