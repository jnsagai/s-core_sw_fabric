---
name: score-implementation
description: Implement a scoped source change with supplied constraints and tests.
metadata:
  version: "1.0.0"
---

# Required input

Use the supplied baseline-bound Context Manifest, task envelope, compiled obligations,
allowed paths/tools, output contract and bounded evidence/trace references. Missing native
IDs or required scope are unresolved inputs; do not invent aliases or reinterpret the process.

# Procedure

Read only selected L1 content. Request related L2 material or native evidence through the
bounded service when needed. Preserve exact source/status/license references.

1. Preserve interface, failure handling and supplied safety mitigation invariants.
2. Change only manifest/write-scope paths; keep implementation and regression trace linked.
3. Request fresh deterministic checks; report self-checks only as assertions.

# Output

Return the supplied structured agent_result contract with changed paths, native IDs,
evidence references, unresolved assumptions and proposed next action. Self-reported checks
are assertions. Required engineering rationale belongs in the draft artifact. Do not narrate
execution or repeat full evidence. Read [output binding](references/output.md) only when the
output/baseline boundary needs clarification.

# Prohibited decisions and stops

Do not approve engineering gates, safety closure, deviations, release/readiness or evidence
trust. Do not derive applicability or mandatory checks from this procedure. Stop at a human
gate, stale/missing binding, exhausted budget or repeated failure/no progress. Runtime loop
control belongs to Fabro. Codex discovery does not establish Fabro runtime availability.
