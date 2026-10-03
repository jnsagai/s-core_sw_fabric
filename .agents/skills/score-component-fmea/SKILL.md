---
name: score-component-fmea
description: Draft component FMEA changes from affected functions/failure modes.
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

1. Retain native failure-mode identifiers and current mitigation links.
2. Propose effects, causes and mitigation requirements within the affected component.
3. Flag missing evidence and allocation; stop before safety closure.

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
