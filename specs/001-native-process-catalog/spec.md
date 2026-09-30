# Feature Specification: Native process catalogue

**Feature Branch**: 001-native-process-catalog
**Created**: 2026-09-27
**Status**: Implemented for pinned minimal consumer; owner review pending.
**Input**: Brief §20.4, FAB-006/FAB-007, ADRs 0002/0003/0006.

## User Scenarios & Testing

### US1 — Inspect native obligations with provenance (P1)
An integration developer imports pinned native export(s) and metamodel rules, then
reads work-product/workflow/role/guidance/template references and source locations.
Independent test: a genuine Sphinx-Needs8.3.1 defaults-removed export plus its metamodel
and export manifest yields a catalogue with native IDs and resolvable source identity.

1. Feature/component FMEA/DFA and safety formal-review work products resolve to native
   definitions; wrapper instances and template/example documents remain distinguishable.
2. Both raw native relation target and parsed ID/version selector survive ingestion.
3. Two repositories using the same native ID remain distinct by namespace; ambiguous
   unqualified references fail, rather than choosing an arbitrary source.
4. Source docname, mounted path, source path and rendered URL are distinct. Missing
   optional line information is explicit; missing required source identity is an error.

### US2 — Reject unsupported or inconsistent input (P1)
A developer receives actionable typed diagnostics and no usable catalogue when required
schema/source/reference integrity cannot be established.
Independent test: negative fixtures below produce nonzero exits and precise record paths.

1. Unsupported creator/envelope/schema, duplicate JSON keys/record identities, wrong
   types, count inconsistencies, missing required defaults schema and tampered hashes fail.
2. Version mismatch, unsupported selector and mandatory unresolved external target fail.
3. Import does not fetch remote URLs, execute a Sphinx conf.py, evaluate selectors with
   Python eval, write source repositories, or traverse outside declared source roots.

### US3 — Rebuild the same catalogue (P2)
A reviewer can rebuild and compare semantic outputs independent of input iteration
order, checkout location or wall-clock time.
Independent test: same normalized sources yield byte-identical canonical catalogue
and digest; changed semantic source/mapping/schema content changes the digest.

## Requirements

- FAB-006: Every imported native type, workflow, template and work product retains
  source references. Preserve unknown non-normative native metadata losslessly.
- FAB-007: Unsupported schemas and unresolved mandatory references block downstream
  compilation. A malformed input may produce a diagnostic report but no success artifact.
- 001-R1: Support only the explicitly verified Sphinx-Needs8.3.1 envelope and pinned
  docs metamodel. Restore defaults per export version schema, never by global guesses.
- 001-R2: Import metamodel definitions and exported native entities separately; keep
  forward links/backlinks/narrative references separate. No applicability or scheduling.
- 001-R3: Preserve export-version key, export dictionary key, native ID and native need
  revision separately; supported selector syntax initially `[version==N]` only, with
  plain native IDs also allowed. Discover any additional real syntax before widening.
- 001-R4: Provenance manifest binds repository commit, content/schema/export digests,
  namespace, build command/toolchain and mount mapping; paths are relative logical paths.
- 001-R5: CLI diagnostic errors include stable code, source, JSON pointer/native ID,
  explanation and next action. Invalid input returns 2, semantic integrity failure 1;
  success 0 means catalogue generation only, never engineering acceptance.

## Edge Cases and Acceptance Scenarios

AC001-01 genuine minimal native fixture and fresh export build proof; AC001-02 native
FMEA/DFA/FDR definitions; AC001-03 sparse defaults including booleans/empty links;
AC001-04 qualified versions success/mismatch/unsupported syntax; AC001-05 external
namespace collision/dangling link; AC001-06 malformed schema/duplicate keys/IDs;
AC001-07 source hash mismatch/path escape/symlink; AC001-08 byte/digest determinism and
semantic-change sensitivity; AC001-09 template code blocks not imported as instances;
AC001-10 exact source locations or explicit unavailability, mounted docs and empty
bundle URL; AC001-11 unknown metadata retained but unknown normative schema rejected;
AC001-12 representative native build failures stay visible and prevent compatibility claim.

## Success Criteria

All AC001 scenarios have actual outcomes and logs. A source-qualified native catalogue
is produced reproducibly with complete references for the selected baseline closure.
At least one fresh native export plus a licensed minimal fixture is exercised; parser
fixtures alone cannot establish full baseline compatibility. No runtime is needed.

## Non-goals and Assumptions

Do not implement applicability/instance planning, artifact editing, compiler, agents,
workflow runs, engineering gate evaluation, approvals or evidence packaging. Evidence
and instance contracts are forward design constraints only. Inspect export key/selector
behavior using the real build before finalizing models. The 8.2.0/2.1.2
minimal-consumer build is verified in acceptance.md. Full score/module_template
documentation builds remain unverified; do not extend the
compatibility claim to them or use a mutable hosted export or invented fixture.
