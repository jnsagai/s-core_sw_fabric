# Dependency roadmap

Status is indexed from per-increment tasks, not a second task database. Increments 000 and 001
are implemented for review; human owner review remains pending. Increment 001 retains fresh
minimal-consumer native build evidence. Increment 002 is implemented and validated as a bounded draft planner. Increment 003 is implemented with real pinned Fabro conformance; its production execution mapping remains pending owner review. The pinned module_template needs_json and docs_check builds now pass in disposable workspaces.

| Increment | Dependencies | Exit evidence | Current state |
| --- | --- | --- | --- |
| [000 bootstrap-and-discovery](../../specs/000-bootstrap-and-discovery/spec.md) | None | Spec Kit setup, constitution, upstream inventory and compatible locks | Partial: implementation complete, owner review pending |
| [001 native-process-catalog](../../specs/001-native-process-catalog/spec.md) | 000 | Typed native catalogue and source references | Implementation complete for pinned minimal consumer; owner review pending |
| [002 applicability-and-work-product-plan](../../specs/002-applicability-and-work-product-plan/spec.md) | 001 | Required instance plan with justified dispositions | Implementation complete; owner/profile review and source-conflict resolution pending |
| [003 deterministic-workflow-compiler](../../specs/003-deterministic-workflow-compiler/spec.md) | 001, 002 | Generated Fabro graph, source map, invariant tests | Implementation complete; production mapping owner review pending |
| [004 native-artifacts-and-traceability](../../specs/004-native-artifact-traceability/spec.md) | 001, 002 | Native document validation and expected-set trace/impact reports | Implementation complete for fixture profiles; production profiles and full target-owner review pending |
| [005 trusted-evidence-and-human-gates](../../specs/005-trusted-evidence-and-human-gates/spec.md) | 002, 004 | Evidence contracts, approval binding, fail-closed evaluations | Fixture-domain CLI and public old/new offline replay pass 689 tests; 41/42 tasks complete; protected production trust-root pin and owner authority pending |
| [006 fabro-runtime-integration](../../specs/006-fabro-runtime-integration/spec.md) | 003, 005 | Real workflow registration/run/inspect/resume/export | In progress; 39/40 tasks complete; disposable candidate register/run/status/wait/cancel/export/offline verify executed; same-run checkpoint resume unavailable on candidate (T025 open); runtime selection and 005 production authority pending |
| [007 apm-agent-context-and-profiles](../../specs/007-apm-agent-context-and-profiles/spec.md) | 000, 004, 006 | Pinned context/tool integration and bounded role execution | Implemented for disposable use; 21/22 tasks; real pinned MCP discovery/setup/context/check and catalogue-based admission; owner review of lock and draft role/model/budget profiles pending (T022); no live model call |
| [008 component-safety-feedback](../../specs/008-component-safety-feedback/spec.md) | 004, 005, 006, 007 | Real component FMEA/DFA draft/review/mitigation loop | Implemented for fixture demonstrations; 19/20 tasks; DEMO-02/03 checks, feedback loop, packet and separate gates; no eligible human decision (005 T009); owner review of safety profile and analyst roles pending (T020); no model call |
| [009 design-implementation-and-unit-verification](../../specs/009-design-implementation-and-unit-verification/spec.md) | 004, 005, 006, 007, 008 | C++17 demo design/source/tests with baseline-bound local results | Implemented for fixture demonstration; 17/18 tasks; owner review of verification and local toolchain profiles pending; protected 005 evidence unavailable |
| [010 misra-quality-and-deviations](../../specs/010-misra-quality-and-deviations/spec.md) | 005, 009 | Real quality-tool adapter, extraction checks, reviewed deviation route | Clang-Tidy slice implemented; 6 scoped tasks complete, 32 broader tasks unchecked; genuine defect/fix runs; other adapters, native prerequisites and owner acceptance open |
| 011 change-impact-and-freshness | 004, 005, 008, 009, 010 | Transitive impact, stale-evidence rejection, bounded re-analysis | Backlog |
| 012 feature-and-component-integration | 008, 009, 010, 011 | Multi-component feature chain and integration evidence | Backlog |
| 013 security-lifecycle | 005, 007, 011, 012 | Applicable security branch and cross-domain impact | Backlog |
| 014 module-evidence-and-readiness | 010, 011, 012, 013 | Module reports/packages/manuals and scoped readiness | Backlog |
| 015 platform-integration-readiness | 014 | Reference integration baseline and platform evidence boundary | Backlog |
| 016 overnight-and-recovery-hardening | 006, 007, 011, 014 | Restart/budget/idempotency/terminal-handoff scenarios | Backlog |
| 017 assurance-and-portable-validation | 010–016 | Negative-test suite, end-to-end evidence, Fabro-free verification | Backlog |
| 018 upstream-packaging-and-handoff | 015, 016, 017 | Installable package, supported-version documentation, upstream proposal | Backlog |

Milestones: M0=000; M1=001–005; M2=006–009; M3=010–011; M4=012–014; M5=015–018.
M2 is a component slice, not release readiness. Native export proof belongs to 001;
Fabro version selection must resolve before 003/006; protected approvals before 005 live
acceptance; model capability/budgets before 007 live work; CodeQL eligibility before 010.

Architecture: [ADRs](../architecture/README.md). Requirements: [FAB index](requirements-index.md).
