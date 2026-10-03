# Architecture decisions

All records are foundation design decisions or proposals, internally checked against
the brief and inspected sources. Owner review is pending; none claims upstream adoption
or validated runtime implementation. See [contracts](../../specs/001-native-process-catalog/contracts/README.md).

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-workspace-and-authority-boundaries.md) | Workspace and authority boundaries | Selected foundation boundary |
| [0002](0002-structured-native-import-and-baseline.md) | Structured native import and baseline | Proposed; validate in 001 |
| [0003](0003-types-catalogue-entities-and-scoped-instances.md) | Types, catalogue entities and scoped instances | Proposed; catalogue in 001, planning in 002 |
| [0004](0004-applicability-and-supported-profiles.md) | Applicability and supported profiles | Proposed; implement in 002 |
| [0005](0005-derived-execution-representation-and-deterministic-compiler.md) | Derived execution representation and deterministic compiler | Proposed; implement in 003 |
| [0006](0006-native-artifact-ownership-and-traceability.md) | Native artifact ownership and traceability | Proposed; catalogue in 001, edits in 004 |
| [0007](0007-trusted-evidence-and-authenticated-human-decisions.md) | Trusted evidence and authenticated human decisions | Proposed; enforce in 005 |
| [0008](0008-safety-design-acceptance-versus-implemented-closure.md) | Safety design acceptance versus implemented closure | Proposed; implement in 008 |
| [0009](0009-verification-and-misra-integration.md) | Verification and MISRA integration | Proposed; implement in 010 |
| [0010](0010-apm-and-mcp-integration-boundary.md) | APM and MCP integration boundary | Proposed; implement in 007 |
| [0011](0011-providers-budgets-and-unattended-operation.md) | Providers, budgets and unattended operation | Proposed; implement in 007/016 |
| [0012](0012-baseline-hashes-impact-and-invalidation.md) | Baseline hashes, impact and invalidation | Proposed; implement in 005/011/016 |
| [0013](0013-scoped-readiness-portable-evidence-and-upstream-boundary.md) | Scoped readiness, portable evidence and upstream boundary | Proposed; implement in 014–018 |

| [0014](0014-bounded-context-and-procedures.md) | Bounded context and lazy procedural Skills | Proposed; local 011 implementation, operational qualification pending |
