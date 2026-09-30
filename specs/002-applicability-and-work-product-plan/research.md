# 002 research and decisions

Date: 2026-09-27. Research complete for the bounded design; this is not target
classification, mapping approval or engineering acceptance. File hashes and pinned
commit comparisons are in [source-review.json](evidence/source-review.json).

## Native applicability needs an explicit mapping

**Decision:** Build a versioned project mapping over source-qualified native definitions;
record coverage for every native work-product/scope pair. The saved 001 export contains
74 work products among 1,251 entities. Native types and links provide references and
constraints, but no general machine-readable applicability rule.

**Evidence:** Process safety guidance, lines 92–112 and 129–135, distinguishes new work,
modifications, changed environment, platform planning and module planning. Lines 234–265
(`gd_guidl__saf_tailored`) require justification confirmed in project safety/security/quality
plans. [Pinned guidance](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/process/process_areas/safety_management/guidance/guideline_safety_management.rst).

**Rationale:** Reading native prose as an executable condition would hide agent policy.
A source-cited mapping exposes interpretation for review. A coverage ledger makes missing
rules visible, including work products added by a new process version.

**Alternatives:** A hardcoded brief seed is incomplete; blindly walking all links conflates
standards references, workflow inputs/outputs and applicability; an LLM decision at runtime
would be nondeterministic and unauditable. None is used.

## Scope cardinality and purpose are explicit

**Decision:** Separate stable instance identity from native revision and baseline bindings.
Model containment and feature/component membership explicitly; use named selectors for
self, owning module/platform and declared affected members. Require an explicit purpose
for every generated instance, including a profile-defined `primary` for a singleton.

**Evidence:** Module safety plan lines 101–114 use `wp__fdr_reports` for plan, package and
analysis reviews. Feature template lines 20–27 realizes `wp__platform_safety_plan` while
listing feature work products at 58–104. This does not define a new feature-safety-plan
work product. [Module plan](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/docs/module/safety_mgt/module_safety_plan.rst),
[feature template](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/docs/features/safety_planning/index.rst).

**Alternatives:** One row per native ID loses reviews; putting the baseline in logical
identity loses continuity. Inferring parents from paths or names produces false ownership.

## Reuse classification preserves human judgment

**Decision:** Require component/version, development origin, allocated classification,
classification record and decision references. Preserve Q/QR/NQ routes from the selected
source; do not infer P or C from metrics and do not automate their qualitative judgments.
An optional final C/P lookup consistency check is unnecessary for the initial 002 scope;
source-backed supplied classification validation is sufficient.

**Evidence:** `wp__sw_component_class` specifies the record at process safety work-products
lines 141–157; workflow `wf__cr_comp_class`, lines 38–49, requires Safety Manager approval.
The module template uses qualitative process/complexity labels, leaves the C++ metrics table
TBD at lines 110–112, supplies a C/P lookup at 166–181, and conditions plan adaptation on an
accepted change request at 194–197. Q requires qualification, QR follows the pre-existing
architectural-element route, and NQ cannot be used in a safety context.
[Work product](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/process/process_areas/safety_management/safety_management_workproducts.rst),
[workflow](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/process/process_areas/safety_management/safety_management_workflow.rst),
[classification template](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/score/component_example/docs/component_classification.rst).

**Alternatives:** `oss: true` is insufficient classification; treating new components as
reused creates false obligations; guessing risk thresholds would invent native policy.

## Authority verification remains a declared dependency

**Decision:** 002 records requested/effective dispositions separately. Production 002 cannot
promote an unverified decision reference to accepted authority. Proposed reuse/tailoring
retains the expected obligation with effective `unresolved` and an authority blocker.
The later protected verifier in 005 may support promotion after checking the bound subject.
Do not add an `approved: true` bypass, fixture CLI mode, or self-signed decision service.

**Evidence:** Native `wp__safety_tailoring` at safety work-products lines 159–173 is a work
product belonging to the safety plan, not a decision credential. Module/feature template
sections 66–78 / 37–44 require additional contextual justification. The project's constitution
and brief §§14.3, 20.9 place authenticated decisions in 005.

**Rationale:** This breaks no implementation dependency: 002 can compute conservative draft
obligations, explain proposals and test expected blocked outcomes without fabricating trust.

**Alternatives:** Trusting a local status string is unsafe; implementing 005 here expands
scope; waiting for 005 would prevent useful structural planning. Decision refs are data,
not executable adapters; the production verifier is deliberately unavailable in 002.

## Security has a real source conflict

**Decision:** Preserve the two source facts and block conflicting template binding. The
process-native security review ID stays `wp__fdr_reports_security`; a safety review is never
silently relabelled. Unknown security relevance and interaction obligations remain visible.

**Evidence:** Process security work-products lines 79–88 define that ID; module security plan
lines 86–101 and the plan-FDR header at 20–26 use `wp__fdr_reports`. Process security audit
lines 94–102 defines `wp__audit_report_security` as valid but says tailoring needs discussion.
[Process definitions](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/process/process_areas/security_management/security_management_workproducts.rst),
[module plan](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/docs/module/security_mgt/module_security_plan.rst),
[module review template](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/docs/module/security_mgt/module_security_plan_fdr.rst).

Security-analysis definitions at lines 51–52 and 75–80 include interactions between relevant
and non-relevant elements. Requirement/architecture security attributes are element-level
facts, not permission for blanket target exclusion. [Analysis definitions](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/process/process_areas/security_analysis/security_analysis_workproducts.rst).

**Alternatives:** Trusting native `valid` as applicability conflates concepts; choosing whichever
template is convenient hides a conflict; a global security:NO skip drops independent duties.

## Cross-scope coverage is evidence, not identity collapse

**Decision:** A component proposal to reuse feature analysis binds both distinct instances,
the exact covered subject and a rationale; pending authority leaves component coverage unresolved.

**Evidence:** Safety analysis concept lines 41–44 and security concept lines 52–57 describe
reuse for components without subcomponents with explanation in their analysis documents.
[Safety concept](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/process/process_areas/safety_analysis/safety_analysis_concept.rst),
[security concept](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/process/process_areas/security_analysis/security_analysis_concept.rst).

## The 001 consumer boundary needs validation

**Decision:** Add a bounded persisted-catalogue reader in 002. Verify canonical self-digest,
caller-selected expected baseline digest, structural shape, unique qualified identities,
source consistency and relation endpoints before planning. Reuse existing bounded parsers
and canonical encoding; do not treat the descriptive JSON schema or TypedDict as runtime validation.

**Evidence:** Current `catalog/export.py` seals output, but no persisted-catalogue loader exists.
The serialized catalogue includes a digest absent from the producer TypedDict; raw native
metadata intentionally remains open. A self-consistent digest establishes integrity, not
trusted provenance. Existing source-location verification checks mounted path and bytes,
not authentication of the source Git commit or native declaration line.

**Prerequisite repair:** Review reproduced output overwrites of a schema, an RST and a new
source-tree file in disposable copies. The 001 writer now protects all declared source roots
and the metamodel schema. Three regression tests require exit 2 and unchanged source bytes.
The new planner writer must additionally protect its own intake/profile/mapping/inventory inputs.

## Clarification outcome

No product question requires guessing target authority: unsupported profiles, missing
classification and unverified decisions are specified blocked outcomes. Actual target ASIL,
review identities, classifier judgments and native source-conflict resolution remain target
inputs or future adoption decisions, not unresolved design questions. The draft profile must
state its support limits; no live engineering qualification is asserted.
