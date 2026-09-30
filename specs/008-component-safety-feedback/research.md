# Increment 008 safety research

**Source baseline:** Read-only inspection of the 000-locked references in
`/tmp/s-core-foundation/references` (all clean at their pins): `process_description`
`98d1d5f42dad412a09a888ea25e59c62fa6371ce`, `module_template`
`c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d`, `docs-as-code`
`d5f3de608cdfc034952c57d40979c78d8cd35957`. No model call or native build was run.

## Decision 1 — Take catalogues and rules from pinned native sources

**Decision:** The profile carries the FMEA fault models from `gd_guidl__fault_models`
(`fault_models_guideline.rst`, 15 IDs: `MF_01_01…07`, `CO_01_01…02`, `EX_01_01…06`) and the DFA
initiators from `gd_guidl__dfa_failure_initiators` (`dfa_failure_initiators.rst`, 35 IDs in five
groups). File digests: fault models `c24713773b…6b18`, initiators `74a39c6fdc…bfaa`, process
requirements `6f7a7c0502…86ec1e87`. An env-gated test re-derives the IDs from the checkout.

**Rationale:** The template tables are examples; the component DFA template omits `SI_01_01`
(also absent natively) and all shared-resource rows. Native IDs, not template rows, define the
denominator.

## Decision 2 — Respect native scope of DFA initiator groups

**Decision:** Groups `SR` ("DFA shared resources (used for Platform DFA)") and `SC` ("DFA
development failure initiators (Platform DFA)", only for diverse development) are platform scope.
A component DFA may omit them only when the check request names a platform allocation that
resolves to a native need or document in the checked file set; otherwise `ALLOCATION_UNRESOLVED`
blocks. `CO`, `SI`, `UI` are component scope and must each be accounted for.

**Rationale:** The component template's sentence "shared resources will be considered in the
platform DFA" is an example (brief §11.5, ADR 0008); the native heading provides the scope, and a
resolvable allocation provides the project-specific link. This allocation rule is a fabric policy
labelled `fabric_policy_pending_owner_review`.

## Decision 3 — Enforce metamodel fields and native attribute rules exactly

**Decision:** From `metamodel.yaml` (`fe6a3b6a…6290`): `comp_saf_fmea` needs `fault_id`,
`failure_effect`, `sufficient` (`yes|no`), `status` (`valid|invalid`), non-empty content, and
`violates` to `comp_arc_dyn`/`comp_arc_sta`; `comp_saf_dfa` needs `failure_id` and `violates` to
`comp_arc_sta` only; optional `mitigated_by` to `comp_req`/`aou_req`; `mitigation_issue` must match
`^https://github\.com/[^/]+/[^/]+/issues/\d+$`. From `safety_analysis_process_reqs.rst`:
`gd_req__saf_attr_sufficient` (sufficient only with a linked mitigation),
`gd_req__saf_attr_mitigated_by` (valid requires `mitigated_by`), and
`gd_req__saf_attr_mitigation_issue` (a needed mitigation links an issue and keeps
`sufficient == no`).

**Consequence:** A draft item must carry `sufficient: no` and `status: invalid` because both are
mandatory; blank values are violations, not unknowns. No RPN/occurrence ranking exists natively,
so none is computed.

## Decision 4 — Mitigation states are derived, not declared

**Decision:** Per applicable item: `missing` (no `mitigated_by`, no issue), `proposed` (issue, no
`mitigated_by`), `linked_pending_review` (`mitigated_by`, `sufficient: no` or `status: invalid`),
`claimed_sufficient` (`sufficient: yes` and `status: valid`). Only `claimed_sufficient` backed by
a verified decision covering the exact bytes is reviewed. `missing` and `proposed` are unresolved
and block design acceptance.

## Decision 5 — Promotions need a verified decision; agent promotions are untrusted

**Decision:** Comparing a baseline with the current analysis, any `sufficient` no→yes or `status`
invalid→valid transition (or a new item already promoted) is a promotion. If a 007
`agent_output_check` lists the file as agent-changed, it is `UNTRUSTED_PROMOTION`; otherwise it is
`PROMOTION_UNREVIEWED` until a verified decision binds it. Both block.

## Decision 6 — Decisions only via verified 005 assessments

**Decision:** `safety gate` accepts 005 portable assessments with their trust contexts, replays
them with `verify_assessment`, and counts one only if it reproduces, its gate outcome is `pass`,
its gate ID is the profile's design or closure gate ID, and every packet file digest appears in
the assessment subject's file closure. The production domain is not eligible while 005 T009 is
open. Fixture-domain decisions are labelled `fixture_contract`.

**Consequence:** No verified decision covers the 008 fixture files, so the demos stop at
`awaiting_decision`. The design-accepted → closure-blocked path is tested at the evaluator with
verified-decision summaries.

## Decision 7 — Re-analysis on changed, removed or new referenced elements

**Decision:** Each need's digest is the SHA-256 of its raw directive bytes. Items whose `violates`
or `mitigated_by` targets changed, disappeared or are new since the baseline require re-analysis;
new architecture elements not referenced by any item are reported as uncovered elements. Any
decision bound to baseline digests is stale.

## Decision 8 — Bounded loop and AoU transfer flag

**Decision:** Each check carries an iteration number; the profile sets the maximum (3). An item
unresolved at the maximum yields `ESCALATE_TO_HUMAN` instead of another proposal. An item for an
internal fault (`EX_*`, `UI_*`) whose `mitigated_by` targets are only `aou_req` gets
`AOU_TRANSFER_REVIEW` (non-blocking, reviewer attention).

## Decision 9 — Checklist stays unanswered

**Decision:** The packet lists the six general checklist items from
`module_safety_analysis_fdr.rst` (`84789ff7…c7b6`) with `answer: pending_human` and, where
relevant, a structural support note. Structural results never answer an adequacy question.

## Implementation findings

- The native fault-model table lists `Element | ID | …`; the extractor resolves the `ID` column
  from the header instead of assuming the first column.
- The re-analysis check caught an error in the first v2 fixture: an unchanged item referencing the
  changed `evaluate` element had not been re-analysed. The fixture was corrected; the unchanged
  case remains as a test.
- 005 replay rejects a resealed forged gate result outright (`SUBJECT_MISMATCH`), before any
  binding is considered.

## Remaining unknowns

- Feature/platform propagation, and feature-level `feat_saf_*` checks (later increments).
- Native `needs_json`/`docs_check` builds of the fixture files (004 has the build path; not run).
- Real human decisions, implementation evidence and closure (005 T009, 009+).
