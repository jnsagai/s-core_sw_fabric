# Handoff: 010 disposition drafts and fresh correction checks

2026-09-30. [Validation](../../specs/010-misra-quality-and-deviations/disposition-acceptance.md),
[exact contract](../../specs/010-misra-quality-and-deviations/contracts/dispositions.md),
[tasks](../../specs/010-misra-quality-and-deviations/tasks.md).

The bounded draft/correction slice adds `quality disposition`. Drafts retain their
original native finding, file/scope/source/tool/policy closure and proposal metadata.
Correction checks execute Clang-Tidy, Cppcheck or a separate ASan/UBSan adapter afresh,
requiring adequate unchanged scope and absence of the original check across the component.
Imported claims cannot establish a correction. Every record stays unprotected/ineligible.

Linked history verifies all ancestors and protects their files against overwrite; later
source drift stales the earlier corrected observation. No names/dates/native status field
is treated as an approval. The implemented construct scope is deliberately the whole file;
AST matching and accepted fixture decisions are not claimed.

Scoped T049–T052 are complete: 52 tasks, 25 complete and 27 original tasks open.
Reuse the strict readers, existing adapters and exact records. Next useful work is scoped
T020/T022: independently replay 005 assessments and bind exact draft/finding/construct/source/
tool/policy, allowed category, scope, authority and validity. Positive paths must remain
fixture_contract while protected production authority (005 T009) is unavailable.
Missing adopted category policy must remain a blocker; agents cannot accept it.

CodeQL execution/source-build/reporting reconciliation, coverage/manual obligations,
009 T018 and human 010 T032 remain unresolved. This handoff proposes the next slice
without authorizing it, broader 010 work, 011, publishing, merging or deployment.
