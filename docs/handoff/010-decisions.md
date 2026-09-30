# Handoff: 010 independent disposition decision replay

2026-09-30. [Validation](../../specs/010-misra-quality-and-deviations/decision-acceptance.md),
[contract](../../specs/010-misra-quality-and-deviations/contracts/decisions.md),
[tasks](../../specs/010-misra-quality-and-deviations/tasks.md).

The authorized T020/T022 slice adds `quality decision-subject` and `quality decision`.
Preparation revalidates a selected draft without analyzer execution, freezes exact current
source/tool/config/profile/assets and category policy, and emits a deterministic binding
for the 005 file closure. Decision evaluation independently reproduces 005, verifies that
exact closure, reevaluates every gate predicate at current fixture time and reclassifies
and reconciles signed decisions. Expiry, revoked/expired keys or roles, scope drift,
unknown/prohibited categories, conflicts and withdrawals remain unresolved.

Positive examples use synthetic public-key fixture authority only. Existing version 1
draft/correction reviews, original native provenance, source IDs and license notices remain
intact. Results are never eligible engineering evidence. Production stays blocked while
005 T009 and adopted category policy are unavailable; no signing service was added.

T020/T022 and T053–T056 are complete: 56 tasks, 31 complete and 25 original tasks open.

Next useful implementation work is the guideline coverage matrix (T023/T025), preserving
unknown denominator, unsupported mechanisms and pending manual review. A later packet and
compliance evaluator must retain this decision result and every unresolved original/history.
The default candidate profile still has unknown mapping/category policy.

CodeQL eligibility/source-build/reporting prerequisites, 009 T018, human 010 T032 and
protected authority remain open. This handoff proposes the next slice; it does not authorize
coverage implementation, broader 010, 011, paid calls, publishing, merging or deployment.
