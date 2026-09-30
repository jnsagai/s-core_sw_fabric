# Research and clarification

Decision: official Spec Kit v1.0.12, explicit Codex skills option, isolated tool install.
Rationale: verified latest official release/source and bundled templates; existing global
0.14.0 is preserved. Alternatives: global upgrade or older command spellings rejected.

Decision: consumer-selected docs8.2/process2.1.2; native build proof deferred to 001.
Rationale: matching platform/template declarations. Alternatives: independent latest
pins and mutable hosted exports rejected. Process standalone docs8.0.1 remains a recorded
compatibility risk, not silently resolved.

Decision: no Fabro runtime selected. Stable examined release lacks registry, nightly is
an unvalidated source candidate. Alternative reduced stable API would change the brief;
resolve before 003/006 rather than weaken it during bootstrap.

Decision: current+next detailed tasks only, no 001 implementation. User scope overrides
the brief's continuation instruction and optional Spec Kit workflow suggestions.

See [inventory](../../docs/discovery/upstream-inventory.md), [ADRs](../../docs/architecture/README.md)
and [contracts](../001-native-process-catalog/contracts/README.md). No consequential
foundation decision requires a new owner answer; acceptance review is intentionally pending.
