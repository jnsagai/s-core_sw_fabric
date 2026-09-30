# Feature Specification: Component safety feedback

**Feature Branch**: `008-component-safety-feedback`

**Created**: 2026-09-30

**Status**: Implemented for fixture demonstrations (19/20 tasks; T020 owner review open). Results
are in [acceptance](acceptance.md). No live model call, production human decision or safety
acceptance is authorized. Owner review of the safety-analysis profile, its platform-allocation
policy and the FMEA/DFA role profiles is pending.

**Input**: Continue from the [007 handoff](../../docs/handoff/007-to-008.md). Specify brief §11
and §20.11, ADR 0008 and FAB-031/FAB-032: separate FMEA and DFA roles bound to the pinned native
templates, coverage and applicability reports, mitigation feedback to requirements/AoUs and
architecture, re-analysis, a safety review packet, and separate design-acceptance and closure
gates. The demonstration uses the brief's telemetry freshness guard (DEMO-02, DEMO-03) as
fixture native artifacts.

## User Scenarios & Testing

### User Story 1 — Check a native FMEA or DFA against the pinned process (Priority: P1)

A safety engineer submits the component's native requirements, architecture and FMEA or DFA
documents. The fabric checks that every native fault model or failure initiator is either
analysed or explicitly excluded with rationale, that every analysis item has the native mandatory
fields and links to real architecture elements, and that each item's mitigation state follows the
native attribute rules. It reports what is missing without inventing engineering content.

**Why this priority**: Coverage and mitigation gaps must be visible before anyone reviews or
accepts an analysis.

**Independent Test**: Check the fixture FMEA with one applicable fault model lacking a mitigation,
then remove one table row, break one link and add one placeholder.

**Acceptance Scenarios**:

1. **Given** a native FMEA or DFA, **when** checked, **then** each catalogue ID is reported as
   analysed, excluded with rationale, or uncovered, and each applicable ID has at least one
   analysis item. (AC008-01)
2. **Given** an item with missing mandatory fields, unresolved or wrongly typed links,
   placeholders, or `sufficient: yes`/`status: valid` without `mitigated_by`, **when** checked,
   **then** the violation is named with its native rule. (AC008-02)
3. **Given** an applicable item without mitigation or with an open mitigation issue, **when**
   checked, **then** it is reported as an unresolved mitigation. (AC008-03)
4. **Given** a component DFA that omits platform-scope initiators, **when** checked, **then** the
   omission is accepted only with a resolvable higher-level allocation; otherwise it blocks.
   (AC008-04)

---

### User Story 2 — Loop unresolved mitigations back through review and re-analysis (Priority: P1)

For each unresolved mitigation the fabric emits a feedback proposal routed to requirement/AoU
and architecture review, bounded by an iteration budget. When the requirements or architecture
change, analyses that reference changed or new elements are marked for re-analysis and earlier
acceptance no longer applies.

**Why this priority**: DEMO-02 requires the loop, and an unresolved mitigation must block the
next acceptance state.

**Independent Test**: Check v1 (gap), then v2 (new requirement, changed architecture, updated
FMEA) against v1; exhaust the iteration budget in a third case.

**Acceptance Scenarios**:

1. **Given** unresolved mitigations, **when** checked, **then** a feedback proposal per item names
   the review route and the design-acceptance state is blocked. (AC008-05)
2. **Given** a changed or newly introduced architecture element or mitigation requirement,
   **when** a new baseline is checked against the old one, **then** affected items require
   re-analysis and a decision bound to the old baseline is stale. (AC008-06)
3. **Given** an item still unresolved after the iteration budget, **when** checked, **then** it is
   escalated to a human instead of looping again. (AC008-07)
4. **Given** mitigations that move an internal failure only to an AoU, **when** checked, **then**
   the transfer is flagged for explicit review. (AC008-08)

---

### User Story 3 — Keep sufficiency and validity behind human review (Priority: P1)

An agent may draft analysis items and recommendations, but `sufficient: yes` and `status: valid`
change only through the configured review path. A promotion by an agent, or any unreviewed
promotion, is refused.

**Why this priority**: A model recommendation must not promote sufficiency or validity through an
untrusted path.

**Independent Test**: Compare a baseline analysis with an agent candidate that sets
`sufficient: yes`; repeat with a human edit that has no bound decision.

**Acceptance Scenarios**:

1. **Given** an agent-changed analysis that promotes `sufficient` or `status`, **when** checked,
   **then** the promotion is refused as untrusted. (AC008-09)
2. **Given** a promotion without a verified decision bound to the exact analysis bytes, **when**
   checked, **then** it is unreviewed and blocks. (AC008-10)
3. **Given** FMEA and DFA role profiles, **when** checked, **then** they are separate roles whose
   write scopes are disjoint, cover only their analysis documents, and forbid promotion
   decisions. (AC008-11)

---

### User Story 4 — Review packet and two separate gates (Priority: P1)

The fabric builds a safety review packet stating the analysis diff, coverage, affected
requirements and architecture, mitigation changes, verification evidence and what is missing,
uncertainties, the native checklist with answers left to the reviewer, and the exact scope of
each possible approval. Design acceptance and closure are evaluated separately.

**Why this priority**: Reviewers must see precisely what they accept and which implementation
evidence remains pending.

**Independent Test**: Build packets for DEMO-02 and DEMO-03; evaluate gates with no decision,
with a decision bound to other bytes, and (at the evaluator) with a verified design decision.

**Acceptance Scenarios**:

1. **Given** a checked analysis, **when** a packet is built, **then** it lists every section above
   and, for design acceptance and closure, the exact subject and what remains pending. (AC008-12)
2. **Given** no verified human decision, **when** gates are evaluated, **then** they await a
   decision; agent text or unverified records never count. (AC008-13)
3. **Given** an accepted design decision, **when** closure is evaluated without trusted
   implementation and verification evidence, **then** closure is blocked with
   `MITIGATION_EVIDENCE_MISSING`. (AC008-14)
4. **Given** the DFA shared-dependency scenario, **when** the packet is built, **then** the
   dependency concern and its pending disposition are explicit. (AC008-15)

### Edge Cases

- An applicability row says `yes` but no item carries that fault or initiator ID.
- A row or item uses an ID absent from the native catalogue.
- A template placeholder (`<yes | no>`, `<Component architecture>`) remains.
- A `mitigation_issue` is not a GitHub issue URL as the metamodel requires.
- An example in a `code-block` must not count as an analysis item.
- The same need ID is defined twice across files.

## Requirements

### Functional Requirements

- **008-R01 / FAB-031**: The native catalogue (FMEA fault models, DFA initiators with native scope),
  field rules and review checklist MUST come from pinned process/template/metamodel sources with
  recorded digests. (AC008-01/02)
- **008-R02 / FAB-031**: Coverage MUST account for every catalogue ID per analysis; applicable IDs
  need items and exclusions need rationale; platform-scope DFA initiators omitted at component
  level need a resolvable allocation. (AC008-01/04)
- **008-R03 / FAB-031**: Item checks MUST enforce native mandatory fields, link targets and types,
  placeholders, and the native attribute rules for `sufficient`, `status`, `mitigated_by` and
  `mitigation_issue`. (AC008-02/03)
- **008-R04 / FAB-032**: Unresolved mitigations MUST produce feedback proposals to requirement/AoU
  and architecture review and MUST block design acceptance. (AC008-05)
- **008-R05 / FAB-032**: Baseline comparison MUST mark items referencing changed, removed or new
  architecture/requirement elements for re-analysis and MUST stale prior decisions. (AC008-06)
- **008-R06 / FAB-032**: The loop MUST be bounded with human escalation, and AoU-only mitigations
  of internal failures MUST be flagged. (AC008-07/08)
- **008-R07 / FAB-031**: Promotions of `sufficient`/`status` MUST be refused unless a verified
  human decision binds the exact analysis bytes; agent-origin promotions are untrusted.
  (AC008-09/10)
- **008-R08 / FAB-031**: FMEA and DFA role profiles MUST be separate, disjoint and unable to make
  promotion decisions. (AC008-11)
- **008-R09 / FAB-032**: The review packet MUST contain the sections of brief §11.9, the native
  checklist unanswered, and the precise scope of each gate. (AC008-12/15)
- **008-R10 / FAB-032**: Design acceptance and closure MUST be separate; decisions count only from a
  verified 005 assessment bound to the packet's exact file digests; closure needs trusted
  implementation/verification evidence. (AC008-13/14)
- **008-R11**: Commands MUST give stable 0/1/2 outcomes, preserve prior outputs on error, make no
  model call and write no native file.

### Key Entities

- **Safety analysis profile**: Pinned sources, catalogues, field rules, checklist, loop budget.
- **Native analysis set**: Requirements, architecture and FMEA/DFA files with digests.
- **Analysis report**: Coverage, item checks, mitigation states, promotions, re-analysis,
  feedback proposals and gate prerequisites.
- **Review packet**: Reviewer-facing sections and gate scopes.
- **Gate evaluation**: Design-acceptance and closure states with decision and evidence bindings.

## Success Criteria

### Measurable Outcomes

- **SC008-01**: 100% of the 15 fault models and all component-scope DFA initiators are accounted
  for in each fixture analysis report. (AC008-01/04)
- **SC008-02**: The DEMO-02 gap blocks design acceptance, produces one feedback proposal, and after
  the v2 change the affected items are marked for re-analysis. (AC008-05/06)
- **SC008-03**: Every agent or unreviewed promotion in the fixtures is refused; zero promotions
  pass without a verified decision. (AC008-09/10)
- **SC008-04**: Each packet names both gate scopes, and closure never passes while implementation
  evidence is missing. (AC008-12–14)
- **SC008-05**: Zero model calls and zero native file writes by the commands.

## Assumptions

- Native sources: `process_description` `98d1d5f`, `module_template` `c4d4ad0`, `docs-as-code`
  `d5f3de6` as locked in 000. Their component templates define `comp_saf_fmea`/`comp_saf_dfa`.
- No production human decision exists (005 T009 pending); fixture demos stop at an awaiting
  decision. The positive gate path is exercised at the evaluator with verified-decision summaries.
- The telemetry freshness guard files are synthetic fixtures, not S-CORE engineering content.
- Live FMEA/DFA drafting by a model needs separate cost authority and is out of scope.
