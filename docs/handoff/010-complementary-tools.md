# Handoff: increment 010 complementary tools

2026-09-30. [Validation and evidence](../../specs/010-misra-quality-and-deviations/complementary-acceptance.md),
[contract](../../specs/010-misra-quality-and-deviations/contracts/complementary-tools.md),
[tasks](../../specs/010-misra-quality-and-deviations/tasks.md).

Clang-Tidy, Cppcheck and separate GCC ASan/UBSan adapters support local capability/run commands
with exact selections, bounded retained outputs, disposable sources and guarded publication.
Cppcheck preserves XML identities and all locations. Sanitizers preserve actual build/runtime
phases, native policy options and binary identity. Probe results are separate from component runs.
Real seeded defects and fresh corrections are retained. Eleven scoped tasks T033–T043 are complete;
original broader T001–T032 remain unchecked.

Native-output import/extraction is now implemented in the subsequent
[native-import handoff](010-native-import.md), reusing bounded readers and source bindings.
The remaining useful work is disposition and guideline coverage interfaces.
CodeQL execution still needs eligible use, source/build reconciliation and reporting prerequisites.
Do not substitute fixtures or local clean output for real readiness or human acceptance.

Owner review of native/tool confidence, 009 T018, 005 T009 protected authority, guideline
denominator/category policy and 010 T032 remains open. Complete host build closure and native
Bazel target compatibility remain unqualified. No automatic 011 continuation is authorized.
