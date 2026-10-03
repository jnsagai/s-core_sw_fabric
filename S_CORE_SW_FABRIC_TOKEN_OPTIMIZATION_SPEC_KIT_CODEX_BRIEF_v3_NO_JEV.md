# S-CORE SW Fabric — Token, Cost, Skills & Spec Kit Optimization Implementation Brief

**Repository:** `jnsagai/s-core_sw_fabric`  
**Purpose:** Execution-ready implementation brief for Codex, implemented through Spec Kit  
**Primary goal:** Reduce LLM token consumption and cost substantially without weakening deterministic verification, traceability, safety boundaries, evidence integrity, human authority, reproducibility, or native S-CORE ownership.  
**Delivery rule:** Every implementation slice in this brief must be specified, planned, decomposed, analyzed, implemented, and converged through the repository's Spec Kit workflow.

---

## 1. Executive objective

The current S-CORE SW Fabric has matured into an assurance-oriented engineering process engine with:

- native S-CORE process/catalog import;
- applicability and work-product planning;
- deterministic workflow compilation;
- native artifact traceability;
- trusted evidence and human gates;
- Fabro runtime integration;
- bounded agent roles;
- safety feedback;
- unit verification;
- quality/MISRA tooling;
- impact/freshness primitives.

The next optimization target is **LLM efficiency**.

The Fabric shall evolve from:

> broad context + generous token budgets + repeated agent inspection

to:

> deterministic task classification + minimal scoped context + bounded agent execution + deterministic validation + conditional escalation

The intended steady-state behavior is:

> **one cheap agent call + deterministic verification for the majority of routine engineering tasks.**

The optimization must not reduce the rigor of the assurance model.


## 1.1 Mandatory delivery method: Spec Kit

All changes described in this brief shall be implemented through the repository's existing Spec Kit lifecycle.

Codex must not treat this Markdown file as a substitute for the native Spec Kit work products.

The required control flow is:

```text
this implementation brief
        |
        v
inspect constitution + roadmap + active increment
        |
        v
$speckit-constitution
only if a required global principle is missing
        |
        v
$speckit-specify
        |
        v
$speckit-clarify
when the generated specification contains material ambiguity
        |
        v
$speckit-plan
        |
        v
$speckit-checklist
        |
        v
$speckit-tasks
        |
        v
$speckit-analyze
        |
        v
$speckit-implement
        |
        v
deterministic validation
        |
        v
$speckit-converge
        |
        v
roadmap / requirements index / ADR / acceptance reconciliation
```

`$speckit-taskstoissues` may be used after `tasks.md` is stable if GitHub issue tracking is useful, but it must not become a second authoritative backlog.

### Spec Kit source-of-truth rule

The relationship shall be:

```text
Implementation brief
    = owner intent / optimization epic

Spec Kit spec.md
    = normative feature requirements

Spec Kit plan.md
    = implementation architecture and sequencing

Spec Kit tasks.md
    = authoritative implementation backlog for the increment

S-CORE native process
    = authoritative target engineering semantics

Fabro
    = execution runtime

Skills
    = lazy procedural guidance for engineering activities
```

Do not encode S-CORE process semantics only in prompts or Skills.

### Increment strategy

Do **not** renumber existing roadmap increments 012–018 merely to insert token optimization.

The preferred implementation strategy is to extend/create:

```text
specs/011-change-impact-and-freshness/
```

through Spec Kit and make token/context optimization part of the existing **bounded re-analysis** objective because the Context Manifest depends directly on change impact and freshness.

Increment 011 should therefore contain explicit user stories for:

1. transitive impact and freshness;
2. deterministic task classification;
3. Context Manifest generation;
4. L0/L1/L2 context loading;
5. Skills selection and bounded loading;
6. token accounting and Token Governor;
7. tool-result summarization;
8. conditional critic/model escalation;
9. progress/no-progress detection;
10. delta/correction/verification-only/evidence-refresh execution modes;
11. before/after efficiency benchmarks.

If this makes 011 materially unreviewable, Codex may propose a follow-on optimization increment **without renumbering existing roadmap items**, but must record that proposal in `plan.md`/ADR and leave the final roadmap change for owner review.

## 1.2 Required Spec Kit work products

For the optimization work, the active Spec Kit feature must contain at minimum:

```text
spec.md
plan.md
tasks.md
quickstart.md
acceptance.md
contracts/
schemas/
```

Where useful, also create:

```text
research.md
data-model.md
checklists/
```

The specification must define measurable success criteria, including token/cost reduction and unchanged deterministic acceptance behavior.

The plan must identify:

- affected existing modules;
- new optimization modules;
- Skill structure;
- compatibility boundaries;
- migration strategy for current role/model profiles;
- benchmark strategy;
- rollback/fail-closed behavior.

The tasks must distinguish:

- deterministic implementation;
- LLM/Skill integration;
- tests;
- benchmarks;
- documentation;
- human-owned reviews.

Human-owned tasks must remain visibly human-owned and must not be automatically checked off by agents.

---


# 1A. Live-run P0 finding: raw tool output is the immediate token emergency

A reviewed S-CORE run demonstrated a concrete token-amplification failure mode that must be treated as P0.

Observed behavior:

```text
agent needs a small subset of CodeQL/MISRA evidence
        |
        v
generic grep/read against minified SARIF/JSON
        |
        v
single matching line contains a very large structured payload
        |
        v
tool result reaches roughly 262k tokens
        |
        v
multiple similar queries are launched
        |
        v
large outputs enter conversation history
        |
        v
subsequent model turns resend accumulated history
```

The same run also showed avoidable execution narration such as:

```text
"Let me be careful..."
"I have enough..."
"Let me verify..."
"Good to know..."
```

These are two separate problems:

1. **execution narration waste**;
2. **raw structured-evidence ingestion**, which can be orders of magnitude more expensive.

The second is the higher-priority problem.

## 1A.1 Silent Execution Principle

Factory agents shall not narrate their execution process. They shall use bounded tools, produce the requested artifact, and return the required structured result.

They shall not emit planning chatter such as:

```text
"I will now..."
"Let me inspect..."
"I think..."
"I have enough..."
"I want to be careful..."
```

unless the output contract explicitly requires a human-facing explanation.

Engineering rationale is still allowed when it is itself an authoritative work-product field, such as a deviation rationale, safety rationale, review-finding rationale, or disposition rationale.

> **Rationale belongs in the engineering artifact that requires it. Execution narration is forbidden.**

## 1A.2 Structured Evidence Query Principle

Agents must not inspect large raw structured-analysis artifacts through generic `grep`, `cat`, unrestricted `read_file`, `read_many_files`, or shell pipelines that print raw SARIF/JSON.

This applies especially to:

```text
*.sarif
*.sarif.json
CodeQL result.json
large minified JSON
large JSONL records
large compiler/static-analysis report blobs
```

Instead, large structured evidence must be accessed through bounded deterministic adapters that return:

```text
normalized subset
summary
stable evidence reference
raw artifact digest
```

The raw evidence remains retained unchanged.

## 1A.3 Collector-normalized evidence

Collectors should emit both:

```text
raw authoritative evidence
+
bounded agent-facing normalized summary
```

Example:

```yaml
tool: codeql_misra
status: completed

findings:
  total: 1842
  project_findings: 31
  dependency_findings: 1811

by_file:
  score/socom/impl/string_registry.cpp:
    - rule: cpp/misra/unnecessary-write-to-local-object
      lines: [23, 35]

excluded_or_external_context:
  .llm_tmp/googletest:
    count: 1760

raw_evidence:
  path: result.sarif
  sha256: ...
```

Agents should consume `summary.json` or an equivalent normalized record by default.

## 1A.4 Bounded evidence-query tools

Introduce deterministic query primitives such as:

```text
sarif_summary
sarif_find_rule
sarif_find_file
sarif_find_location
sarif_count_by_rule
sarif_count_by_path
finding_get
finding_list
evidence_summary
```

A bounded query should return a compact structure such as:

```json
{
  "total": 2,
  "findings": [
    {"rule": "cpp/misra/unnecessary-write-to-local-object", "line": 23},
    {"rule": "cpp/misra/unnecessary-write-to-local-object", "line": 35}
  ]
}
```

rather than exposing the containing raw SARIF line.

## 1A.5 Pre-tool-use output firewall

The pre-tool-use/admission boundary should reject unsafe raw structured-evidence reads.

Conceptually:

```python
if structured_file and estimated_raw_output > allowed_limit:
    deny(
        "RAW_STRUCTURED_EVIDENCE_FORBIDDEN",
        "Use bounded evidence-query tooling."
    )
```

At minimum detect:

```text
large SARIF
minified JSON with extreme line length
large CodeQL result files
large machine-generated report blobs
```

The denial should tell the agent which bounded query tool to use.

## 1A.6 Per-tool output ceilings

Introduce configurable result ceilings. Suggested starting values:

```yaml
tool_output_policy:
  default:
    max_chars: 12000

  grep:
    max_chars: 8000
    max_results: 30

  read_file:
    max_chars: 16000
    max_lines: 250

  shell:
    max_chars: 16000
    strategy: head_tail

  structured_evidence:
    raw_access: false
```

Exact values must be tuned from measurements.

The complete raw result is retained in evidence storage. The model receives only a bounded preview/summary plus artifact reference and digest.

## 1A.7 Per-stage aggregate tool-context budget

Individual result limits are insufficient. Add a total tool-result context budget per agent stage.

Suggested starting point:

```yaml
agent_context_budget:
  tool_results:
    max_total_tokens: 20000

  single_result:
    max_tokens: 5000
```

For routine drafting/classification stages, use a smaller default such as:

```yaml
tool_results:
  max_total_tokens: 12000
```

If more data is needed, the agent must issue a narrower bounded query rather than consume another raw payload.

## 1A.8 Normalize before model interpretation

Do not use an LLM to rediscover what a deterministic collector has already extracted.

Bad:

```text
Collect CodeQL
   -> raw SARIF
   -> agent greps SARIF
   -> agent manually reconstructs findings
```

Preferred:

```text
Collect CodeQL
   -> raw SARIF retained
   -> deterministic normalization/index
   -> bounded finding records
   -> agent drafts disposition/deviation only
```

For a `deviation drafts` stage, the model input should already contain:

```text
normalized finding set
applicable policy
prior disposition history
relevant native IDs
```

The agent should draft; it should not perform forensic discovery over raw analyzer output.

## 1A.9 Minimal factory-stage prompt style

Use a common prompt contract:

```text
Execution style:

- Do not narrate your reasoning.
- Do not explain your plan before acting.
- Do not describe what you are about to inspect.
- Do not repeat evidence already present in the input.
- Use bounded tools directly when information is required.
- Return only the requested artifact or structured stage result.
- Keep prose to the minimum required by the output schema.
- Do not provide a chronological account of your work.
- Do not inspect raw SARIF or large machine-generated JSON.
- Use bounded evidence-query tools for structured evidence.
```

For drafting stages:

```text
Do not output rationale unless the output schema explicitly requires a rationale field.
```

## 1A.10 Structured stage completion

Intermediate autonomous nodes should return structured results instead of verbose completion prose.

Example:

```json
{
  "status": "completed",
  "artifact": ".llm_tmp/overnight/reports/finding_classification.md",
  "changed_paths": [
    ".llm_tmp/overnight/reports/finding_classification.md"
  ],
  "unresolved": [
    "clang_tidy_not_executed",
    "human_review_pending"
  ],
  "next_action": "continue"
}
```

Human-readable explanations should be generated once at terminal review/handoff rather than at every intermediate node.


# 2. Non-negotiable invariants

Codex must preserve the following architectural principles.

## 2.1 Deterministic-first principle

If a result can be computed deterministically, an LLM must not be used to compute it.

Examples that must remain deterministic:

- hashing;
- schema validation;
- trace traversal;
- dependency analysis;
- impact propagation;
- evidence freshness;
- build execution;
- test execution;
- coverage extraction;
- static-analysis execution;
- MISRA/CodeQL extraction;
- evidence packaging;
- gate state evaluation;
- diff generation;
- work-product status;
- task status;
- baseline comparison.

LLMs may be used for:

- engineering reasoning;
- requirement drafting;
- architecture proposals;
- source-code implementation;
- safety-analysis hypothesis generation;
- review/critique;
- ambiguity resolution proposals.

## 2.2 Human authority remains authoritative

Agents must never:

- approve engineering gates;
- accept safety closure;
- waive deviations;
- impersonate reviewers;
- answer human gates;
- establish engineering readiness;
- declare module/platform/release readiness.

Existing assurance boundaries must remain intact.

## 2.3 Evidence is not prompt context

Full logs, reports, SARIF, compiler output, test logs, coverage data, and historical evidence must remain stored as evidence artifacts.

The LLM should receive only:

- a structured summary;
- relevant excerpts;
- stable evidence references;
- digests when required.

Full evidence should only be loaded into agent context on explicit demand.

## 2.4 Native S-CORE artifacts remain authoritative

Fabro and LLM context must remain derived execution mechanisms.

Preserve the invariant:

> If Fabro disappeared tomorrow, all authoritative S-CORE engineering artifacts would remain valid and understandable.


## 2.5 Optimization must be measurable

Do not claim optimization based on intuition.

Before and after measurements must include:

- total input tokens;
- uncached input tokens;
- cached input tokens;
- output tokens;
- reasoning tokens when available;
- model calls;
- tool calls;
- cost;
- wall time;
- correction visits;
- escalation count;
- deterministic gate result;
- final accepted/rejected outcome.

---


## 2.6 Skills are procedural knowledge, not engineering authority

Skills may teach an agent **how to perform** an engineering activity.

Skills must not decide:

- applicability;
- required work products;
- traceability truth;
- evidence freshness;
- gate state;
- test pass/fail;
- safety acceptance;
- deviation acceptance;
- engineering readiness;
- release readiness.

Those decisions remain in deterministic engines and authorized human gates.

A Skill may produce a proposal or structured draft that is later checked by deterministic mechanisms.

## 2.7 Skills must be lazy and narrow

A Skill should cover one engineering activity, not the entire S-CORE process.

Preferred size for a `SKILL.md` is approximately **1–3k tokens**.

Detailed background must be placed in supporting `references/`, deterministic helpers in `scripts/`, and templates/assets separately.

Do not create a monolithic `score-s-core-engineering` Skill that recreates the original context problem.


## 2.8 Large raw machine evidence is never model context by default

Raw SARIF, compiler databases, minified machine JSON, and other large analyzer artifacts remain evidence artifacts. They are not normal agent context.

Agents receive normalized summaries and bounded query results. Generic tools must not be allowed to bypass this rule.

## 2.9 Execution narration is not a work product

Model planning chatter and chronological self-commentary are not engineering deliverables.

The Fabric should optimize for:

```text
minimal execution narration
minimal free-form assistant prose
maximum structured artifact output
```

without suppressing rationale fields explicitly required by an engineering work product.


# 3. Current token-cost risks to address

The current repository permits very large operational envelopes.

Examples currently visible in the role/model profiles include:

### Developer

```yaml
budget:
  cost_microusd: 500000
  input_tokens: 2000000
  output_tokens: 200000
  wall_seconds: 3600
  calls: 6

loopback:
  max_correction_visits: 2

retry_limit: 1
```

### Independent critic

```yaml
budget:
  cost_microusd: 300000
  input_tokens: 1000000
  output_tokens: 64000
  wall_seconds: 1800
  calls: 2
```

### Model profiles

The current model profiles allow up to approximately:

```yaml
max_output_tokens: 32000
```

per call.

These limits are reasonable as hard safety ceilings but are too permissive as normal operational defaults.

The current context mechanism also permits broad readable scopes such as:

```yaml
allowed_inputs:
  - docs/**
  - src/**
  - tests/**
  - score-context/**
```

and observation handling supports very large bounded stores.

This creates a risk that agents repeatedly rediscover context that deterministic machinery already knows.

---

# 4. Target architecture

Implement the following optimization pipeline.

```text
                      SPEC KIT
       specification / plan / tasks / convergence
                           |
                           v
                   CHANGE / OBLIGATION
                           |
                           v
                Deterministic Classifier
                           |
                           v
                    Impact Analysis
                           |
                           v
                    Context Manifest
                           |
                           v
                      Token Governor
                    /       |       \
                   /        |        \
             context      skills     model
             L0/L1/L2   required /   route
                         on-demand
                   \        |        /
                    \       |       /
                     +------+------+
                            |
                            v
                     Agent Execution
                            |
                            v
                  Deterministic Validation
                            |
                     +------+------+
                     |             |
                    PASS          FAIL
                     |             |
                    done      one correction
                                   |
                                   v
                          conditional escalation
```

The critical design principle is:

> **The deterministic Fabric decides what the model needs to know, what procedural Skill it may use, which model may execute it, and how much budget it receives. The model must not rediscover the process or repository scope from scratch.**

## 4.1 Context Manifest and Skill are different abstractions

Keep the distinction explicit:

```text
Context Manifest = WHAT the agent needs to know
Skill            = HOW the agent should perform the activity
Token Governor   = HOW MUCH context/budget and WHICH model/skills are allowed
```

Do not merge them into one large prompt.

## 4.2 Initial S-CORE Skills

Create an initial small Skill set under:

```text
.agents/skills/
```

Recommended initial Skills:

```text
score-requirements/
score-architecture/
score-component-fmea/
score-dfa/
score-implementation/
score-verification/
score-quality-review/
score-change-impact/
```

Do not create dozens of micro-skills in the first iteration.

Each Skill must have:

```text
SKILL.md
references/      optional
scripts/         optional
templates/       optional
```

A Skill must define:

- when it applies;
- required inputs;
- procedure;
- expected structured output;
- prohibited decisions;
- stop conditions;
- which reference files may be loaded on demand.

## 4.3 Example Skill structure

Example:

```text
.agents/skills/score-component-fmea/
├── SKILL.md
├── references/
│   ├── score-fmea-rules.md
│   └── native-types.md
└── templates/
    └── component-fmea.rst
```

Example intent for `SKILL.md`:

```markdown
---
name: score-component-fmea
description: Analyze or update an S-CORE component FMEA when a task affects
  component behavior, failure modes, mitigations or safety requirements.
---

# Procedure

1. Read the supplied Context Manifest.
2. Resolve only the affected architecture and requirement IDs.
3. Inspect existing failure modes before proposing new ones.
4. Draft candidate failure modes/effects/mitigations.
5. Bind mitigations to native requirements or AoUs.
6. Report missing mitigation or ambiguous ownership.
7. Produce the required structured result.
8. Stop before safety acceptance.

# Prohibited

- Do not accept safety closure.
- Do not waive a safety finding.
- Do not declare evidence trustworthy.
- Do not modify unrelated native artifacts.
```

## 4.4 Skills must use progressive disclosure

The normal loading sequence shall be:

```text
skill name + short description
        |
        v
selected SKILL.md only
        |
        v
specific reference/template/script only if required
```

Do not inject all Skill bodies or all reference files into every call.

## 4.5 Add a deterministic Skill Selection Record

Create a bounded, baseline-bound record such as:

```yaml
schema_version: 1
kind: skill_selection
task_id: CR-142
task_class: S1

required:
  - id: score-implementation
    digest: ...

available_on_demand:
  - id: score-verification
    digest: ...

forbidden:
  - id: score-component-fmea
    reason: no_safety_artifact_in_impact_scope

selection_basis:
  - obligation_type
  - impacted_work_products
  - task_class
```

Suggested module:

```text
src/score_sw_fabric/optimization/skill_selection.py
```

Skill selection should be deterministic whenever the obligation/work-product type is known.

Unknown mappings must fail closed or widen to an explicitly reviewed set.

## 4.6 Codex Skills and Fabro runtime Skills are not automatically the same thing

The repository already uses `.agents/skills` for Codex/Spec Kit behavior.

Do **not** assume that a Fabro runtime agent automatically inherits Codex Skills.

Implement a clear boundary:

```text
.agents/skills/
       |
       | source procedure
       v
Skill registry / digest
       |
       v
Skill selection
       |
       v
bounded runtime renderer / retrieval
       |
       v
Fabro agent context
```

Unless verified native Fabro Skill support exists and is pinned, runtime use must explicitly render or retrieve only the selected Skill content.

The rendered Skill must be:

- digest-bound;
- versioned;
- included in context accounting;
- subject to the Token Governor;
- excluded from authority decisions.



# 5. Create a first-class task classification model

Introduce a deterministic task classifier.

Suggested task classes:

```text
S0 — mechanical / metadata
S1 — localized implementation
S2 — component-level engineering
S3 — architecture/safety-sensitive change
S4 — cross-component or exceptional investigation
```

Suggested semantics:

| Class | Typical examples |
|---|---|
| S0 | metadata correction, formatting, generated index update |
| S1 | localized source/test correction |
| S2 | component feature, requirement + implementation change |
| S3 | architecture, safety, interface, cross-artifact change |
| S4 | broad investigation or exceptional unresolved change |

The classifier must rely on deterministic inputs where possible:

- changed paths;
- affected native IDs;
- work-product types;
- safety relevance;
- dependency fan-out;
- number of impacted modules;
- number of impacted requirements;
- unresolved dependency state;
- whether architecture/safety/security work products are implicated.

Do not use an LLM for the initial classification unless deterministic classification explicitly returns `unknown`.

Suggested module:

```text
src/score_sw_fabric/optimization/task_classification.py
```

Suggested record:

```yaml
schema_version: 1
kind: task_classification
task_id: CR-142
class: S1
reasons:
  - one component affected
  - no architecture work product changed
  - no safety artifact affected
  - two source files and one test impacted
confidence: deterministic
```

---

# 6. Add operational token envelopes by task class

Introduce normal operational budgets separate from hard absolute ceilings.

Initial recommended defaults:

| Class | Input tokens | Output tokens | Calls |
|---|---:|---:|---:|
| S0 | 20k–40k | 2k–4k | 1 |
| S1 | 80k–150k | 8k–12k | 2 |
| S2 | 150k–300k | 12k–24k | 2–3 |
| S3 | 300k–600k | 20k–32k | 3 |
| S4 | explicit authorization | explicit | explicit |

Initial developer operational target:

```yaml
budget:
  input_tokens: 200000
  output_tokens: 24000
  calls: 3

loopback:
  max_correction_visits: 1

retry_limit: 1
```

Initial critic operational target:

```yaml
budget:
  input_tokens: 120000
  output_tokens: 12000
  calls: 1
```

Do not necessarily remove the larger global ceilings.

Instead implement two levels:

```text
absolute_ceiling
operational_budget
```

The operational budget should normally govern execution.

Suggested changes:

```text
src/score_sw_fabric/agents/admission.py
src/score_sw_fabric/agents/roles.py
profiles/agent-model-profiles-draft-v1.yaml
profiles/agent-role-*.yaml
```

Add tests verifying that:

- S0/S1 tasks cannot silently consume S3/S4 budgets;
- escalation requires an explicit rule;
- unknown token usage blocks further uncontrolled escalation;
- a task cannot silently switch to an unlimited profile.

---

# 7. Implement Context Manifest

This is the highest-value token optimization.

Create a deterministic **Context Manifest** describing exactly what an agent needs.

Example:

```yaml
schema_version: 1
kind: context_manifest
task_id: CR-142
baseline: <commit>

primary:
  - src/socom/runtime.cpp
  - src/socom/runtime.hpp

requirements:
  - COMP_REQ_034
  - COMP_REQ_035

architecture:
  - ARCH_COMP_012

tests:
  - tests/runtime_tests.cpp

safety:
  - FMEA_019

related:
  - src/socom/service.cpp

evidence_refs:
  - EV-2026-00452

excluded:
  - scope: other modules
    reason: no transitive dependency from current change
```

Suggested module:

```text
src/score_sw_fabric/optimization/context_manifest.py
```

The Context Manifest must be generated from:

- native traceability;
- impact analysis;
- work-product plan;
- affected IDs;
- current baseline;
- task class.

The manifest must be deterministic and digestible.

The agent must not receive repository-wide context when a bounded manifest exists.

---

# 8. Introduce L0 / L1 / L2 context loading

Context must become lazy.

## L0 — task envelope

Always injected.

Target size:

```text
~1k–3k tokens
```

Contents:

- role;
- task;
- baseline;
- task class;
- constraints;
- affected IDs;
- output contract;
- prohibited decisions;
- token budget.

## L1 — relevant engineering context

Automatically produced by the Context Manifest.

Target size:

```text
~5k–20k tokens
```

Contents:

- directly relevant requirements;
- directly relevant architecture;
- relevant interfaces;
- relevant tests;
- relevant FMEA/DFA items;
- current relevant source excerpts.

## L2 — extended context

Not preloaded.

Available only through bounded retrieval tools.

Examples:

- related components;
- broader architecture;
- historical evidence;
- process documents;
- extended test logs;
- full native work products.

Suggested implementation points:

```text
src/score_sw_fabric/agents/context.py
src/score_sw_fabric/agents/roles.py
src/score_sw_fabric/agents/mcp.py
```

Acceptance criterion:

> A routine S1 task must be executable without giving the model the whole `docs/**`, `src/**`, or `tests/**` trees as prompt context.

Access permissions may remain broad for security purposes, but actual context injection must be manifest-scoped.

---

# 9. Observation context must be lazy

Current observation infrastructure is bounded but potentially expensive.

Change default behavior to:

```yaml
observations:
  include_text: false
```

The base context should provide only an observation index:

```text
OBS-14 architecture
OBS-31 previous failure
OBS-48 implementation
OBS-52 tooling
```

The agent should explicitly retrieve an observation only when needed.

Implement deterministic relevance selection where possible.

Recommended default:

```text
top 5–20 potentially relevant observations
```

Do not preload thousands of observation texts.

Suggested changes:

```text
src/score_sw_fabric/agents/context.py
```

Add:

- maximum injected observation-token budget;
- relevance filtering;
- explicit retrieval-by-ID;
- stale/current baseline preference;
- deterministic omission records.

Preserve all original observation records outside model context.

---

# 10. Introduce token-aware context accounting

Every generated context bundle should record:

```yaml
context_accounting:
  estimated_tokens:
    l0: 1800
    l1: 9400
    observations: 800
    tool_schema: 2200
    total: 14200

  limits:
    context_budget: 24000
```

Refuse or trim deterministically when the context exceeds its allowed envelope.

Trimming order should be explicit.

Suggested priority:

```text
1. task + safety constraints       NEVER DROP
2. output contract                 NEVER DROP
3. direct requirements             KEEP
4. direct architecture             KEEP
5. directly affected source        KEEP
6. directly affected tests         KEEP
7. related context                 DROP FIRST
8. historical observations         DROP
9. broad process prose             DO NOT PRELOAD
```

Do not allow arbitrary LLM-generated context summarization to silently become authoritative.

---

# 11. Do not inject the complete S-CORE process into agents

The Fabric already has a deterministic process engine.

Agents should receive the **compiled obligation**, not the entire process.

Desired transformation:

```text
S-CORE native process
        |
        v
Process / Obligation Engine
        |
        v
minimal executable obligation
        |
        v
agent
```

Example agent input:

```yaml
obligation: component_detailed_design

must:
  - satisfy COMP_REQ_034
  - preserve IF_12
  - preserve FMEA mitigation FM_7

output:
  path: docs/design/runtime.rst
  schema: score_component_design

validation:
  - docs_check
  - traceability_gate
```

The agent should not repeatedly interpret the entire S-CORE process documentation.

---

# 12. Add delta workflows

Do not run the complete Spec Kit lifecycle for every engineering change.

Introduce deterministic workflow modes:

```text
full
delta
correction
verification-only
evidence-refresh
```

Suggested behavior:

## Full

```text
specify
plan
tasks
implement
verify
```

Use for substantial new features.

## Delta

```text
impact
plan delta
tasks delta
implement
verify
```

Use for bounded changes to existing engineering items.

## Correction

```text
implement correction
verify
```

Use when deterministic validation identifies a localized defect.

## Verification-only

```text
verify
package evidence
```

No agent unless interpretation is necessary.

## Evidence-refresh

```text
re-run deterministic collectors
freshness check
repackage evidence
```

No implementation agent.

Suggested integration points:

```text
.specify/workflows/
src/score_sw_fabric/compiler/
src/score_sw_fabric/planning/
```

Do not delete the existing full workflow.

Add specialized modes alongside it.

---

# 13. Add conditional model routing

Current architecture already defines model profiles.

Extend this into a deterministic capability/cost router.

Desired routing:

```text
S0/S1
  -> routine/cheap model

S2
  -> routine model first
  -> stronger model only on defined escalation

S3
  -> stronger reasoning profile where justified

S4
  -> explicit approval/supervision
```

Escalation must be conditional.

Do not implement:

```text
cheap model
 -> strong reviewer
 -> premium supervisor
```

for every task.

Instead:

```text
routine model
     |
 deterministic validation
     |
  +--+--+
  |     |
PASS   FAIL
        |
   classify failure
        |
   +----+-----+
   |          |
simple      ambiguous
   |          |
same model   stronger model
               |
          unresolved?
               |
          supervisor
```

Suggested target distribution:

```text
80–90% calls  routine model
10–20% calls  stronger model
<5% calls     premium supervisor
```

These are directional targets, not compliance claims.

Suggested module:

```text
src/score_sw_fabric/optimization/model_router.py
```

---

# 14. Make critic invocation conditional

The independent critic should not review every successful routine change automatically.

Invoke critic only when defined conditions are met.

Possible triggers:

- S2/S3 task;
- safety-relevant change;
- architecture change;
- public interface change;
- unresolved assumption;
- deterministic gate failure after one correction;
- large diff;
- reviewer-required work product;
- explicit owner policy.

For S0/S1 with clean deterministic verification, critic may be skipped if policy allows.

Every skipped critic must have a deterministic reason recorded.

Example:

```yaml
critic:
  required: false
  reason: S1_local_change_all_deterministic_gates_passed
```

---

# 15. Critic receives a Review Pack, not the whole repository

Create a deterministic review package.

Example:

```yaml
kind: review_pack

task:
  id: CR-142
  intent: ...

invariants:
  - preserve COMP_REQ_034
  - preserve FM_7

changed_artifacts:
  - runtime.cpp
  - runtime_tests.cpp

diff_ref: ...
diff_summary: ...

verification:
  build: PASS
  tests: PASS
  traceability: PASS

unresolved_assumptions: []

evidence_refs:
  - EV-...
```

The critic should review:

```text
task intent
+
relevant invariants
+
diff
+
changed work products
+
verification summaries
+
unresolved assumptions
```

not:

```text
entire docs tree
entire source tree
entire test tree
full process history
```

Suggested module:

```text
src/score_sw_fabric/optimization/review_pack.py
```

---

# 16. Compress tool results before returning them to LLMs

Large tool results are a major token multiplier because subsequent agent turns may carry previous results.

Implement structured summaries.

Bad:

```text
10,000-line compiler/test/SARIF output
```

Preferred:

```yaml
kind: test_summary
status: failed
total: 342
failed: 2
first_failures:
  - test: RuntimeTest.Timeout
    file: runtime_tests.cpp
    line: 142
    message: expected 100ms, got 0ms

full_log:
  evidence_ref: EV-8391
  sha256: ...
```

The complete output must still be retained unchanged in evidence storage.

Add output limits for:

- grep;
- file reads;
- compiler stdout/stderr;
- pytest/gtest;
- Bazel;
- static analysis;
- SARIF;
- CodeQL;
- coverage tools.

Suggested principle:

> Every LLM-facing tool result must be a bounded summary plus stable references to full evidence.

---

# 17. Add bounded retrieval primitives

Provide tools that allow agents to request precise context rather than reading broad files.

Examples:

```text
get_requirement(ID)
get_architecture_item(ID)
get_safety_item(ID)
get_test(ID)
get_source_excerpt(path, start, end)
get_trace_neighborhood(ID, depth)
get_evidence_summary(ID)
get_observation(ID)
get_diff(path)
```

Prefer semantic IDs over arbitrary repository scanning.

This should reduce repeated `grep/read_many_files` loops.

---

# 18. Optimize prompt layout for provider caching

Where providers support prefix caching, prompts should maximize stable prefixes.

Prompt order should be:

```text
1. static role instructions
2. static safety/authority constraints
3. stable tool contract
4. stable component context
5. dynamic task
6. dynamic diff/current results
```

Avoid interleaving dynamic content before stable reusable content.

Record cache statistics when providers expose them.

Suggested ledger extension:

```yaml
usage:
  input_tokens: ...
  cached_input_tokens: ...
  uncached_input_tokens: ...
  output_tokens: ...
  reasoning_tokens: ...
  cost_microusd: ...
```

Do not record unavailable usage as zero.

Use `null` / unknown consistently with current assurance philosophy.

---

# 19. Extend the budget ledger

The budget ledger should become a cost-observability subsystem.

Track per:

- call;
- task;
- role;
- model;
- workflow;
- increment;
- accepted work product.

Required metrics:

```text
input_tokens
cached_input_tokens
uncached_input_tokens
output_tokens
reasoning_tokens
tool_calls
model_calls
correction_visits
fallbacks
cost
wall_time
```

Derived metrics:

```text
cost / accepted work product
uncached tokens / accepted work product
tokens / changed LOC
tokens / verified requirement
calls / accepted task
corrections / task
escalation rate
critic invocation rate
```

Do not over-optimize `tokens / LOC` for documentation/safety work; use it only as one diagnostic metric.

---

# 20. Implement Token Governor

Build on `agents/admission.py`.

Suggested module:

```text
src/score_sw_fabric/optimization/token_governor.py
```

Inputs:

```text
task classification
impact scope
context manifest
current ledger
model catalogue
role profile
cache availability
safety relevance
```

Outputs:

```yaml
kind: token_governor_decision

task_class: S1

context:
  level: L1
  max_tokens: 24000

model:
  primary: model.routine.deepseek-v4-flash

limits:
  max_turns: 8
  max_input_tokens: 80000
  max_output_tokens: 10000
  max_tool_result_tokens: 20000
  correction_visits: 1

critic:
  required: false

escalation:
  to_stronger_model:
    allowed_on:
      - deterministic_failure_after_correction
      - ambiguity_unresolved
      - safety_relevant_conflict

  to_supervisor:
    allowed_on:
      - reviewer_disagreement
      - unresolved_architecture
      - explicit_owner_request
```

The Token Governor must never grant more than role/absolute ceilings.

It only narrows execution.

---

# 21. Add hard stop conditions

Terminate an agent loop when any condition is met:

- token budget reached;
- output budget reached;
- tool-result budget reached;
- repeated identical tool query;
- repeated identical failure;
- no changed workspace state after correction;
- no reduction in blocking findings;
- correction visit limit reached;
- unknown provider usage prevents safe admission;
- human gate reached.

Record an explicit reason.

Example:

```yaml
stop_reason: NO_PROGRESS_AFTER_CORRECTION
```

Do not allow agents to continue merely because context window remains available.

---

# 22. Add progress detection

Implement deterministic progress indicators.

Possible signals:

```text
changed source digest
reduced failing tests
reduced diagnostics
reduced unresolved obligations
new valid trace link
new valid native work product
changed diff
```

If an agent consumes another call without measurable progress, stop or escalate according to policy.

This is especially important for overnight operation.

---

# 23. Integrate with Increment 011

Do not build token optimization independently of change-impact work.

Increment 011 should become the primary source for:

- changed IDs;
- dependency fan-out;
- impacted requirements;
- impacted architecture;
- affected safety items;
- stale evidence;
- stale decisions;
- re-analysis scope.

Use that output directly to construct the Context Manifest.

Desired relationship:

```text
Increment 011
    |
    +-- impact graph
    +-- stale evidence
    +-- affected obligations
    |
    v
Context Manifest
    |
    v
Token Governor
```

This makes 011 both:

- an assurance feature;
- a cost optimization feature.

---

# 24. Implement the optimization as a Spec Kit-controlled Increment 011 workstream

The current roadmap already reserves Increment 011 for:

```text
change-impact-and-freshness
```

That is the correct anchor for context minimization because the Context Manifest should be derived from impact and freshness results.

Codex shall first create or extend the Increment 011 Spec Kit feature.

Suggested Spec Kit specification title:

> **Change Impact, Freshness, Context and Token-Efficient Re-analysis**

Suggested user-story decomposition:

```text
US1  Transitive change impact
US2  Evidence/decision freshness
US3  Deterministic task classification
US4  Context Manifest
US5  L0/L1/L2 lazy context
US6  Skill selection and progressive disclosure
US7  Token/cost accounting
US8  Token Governor and model routing
US9  Bounded tool summaries and retrieval
US10 Conditional critic and escalation
US11 Progress/no-progress control
US12 Delta/correction/verification/evidence-refresh workflows
US13 Benchmark and equivalence evidence
```

Spec Kit shall convert these into requirements, acceptance scenarios and tasks.

Do not use this brief as the only backlog.

## 24.1 Mandatory Spec Kit commands/order

Codex should execute the repository-native workflow in this order:

```text
$speckit-constitution
```

Only if inspection shows the constitution does not already cover these global principles:

- deterministic-first execution;
- minimum-sufficient context;
- evidence/context separation;
- lazy Skills;
- operational budget vs hard ceiling;
- conditional model escalation;
- measurable token efficiency.

Then:

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

Use `$speckit-clarify` only for material ambiguity; do not ask the owner questions already resolved in this brief.

Run `$speckit-analyze` before implementation and again after material scope changes.

Run `$speckit-converge` after each major implementation phase and at final handoff.

## 24.2 Suggested Spec Kit specification seed

Use this intent as the initial `speckit-specify` seed, adapted to the repository state discovered at execution time:

> Extend Increment 011 so the S-CORE SW Fabric deterministically computes transitive change impact and evidence freshness, then uses that result to minimize LLM work. Add task classification, Context Manifests, L0/L1/L2 lazy context, deterministic Skill selection, progressive Skill loading, operational token budgets, token/cost/cache telemetry, a Token Governor, conditional model/critic escalation, bounded tool-result summaries, progress detection, and delta/correction/verification-only/evidence-refresh workflows. Preserve native S-CORE authority, existing assurance/human gates, historical evidence, fail-closed behavior, and Fabro-independent artifact validity. Establish before/after benchmarks and demonstrate materially lower uncached input tokens with equivalent deterministic engineering outcomes.

## 24.3 Spec Kit acceptance checklist categories

The generated checklist should include at least:

```text
[ ] Deterministic process semantics preserved
[ ] Human authority preserved
[ ] Historical evidence preserved
[ ] Context Manifest baseline-bound
[ ] Skill selection deterministic/bounded
[ ] Skill content digest-bound
[ ] Runtime Skill boundary explicit
[ ] No monolithic always-loaded Skill
[ ] L0 required context never trimmed
[ ] Safety-critical context never silently dropped
[ ] Tool output full evidence retained
[ ] LLM-facing tool output bounded
[ ] Unknown usage never treated as zero
[ ] Operational budget cannot exceed hard ceiling
[ ] Premium model requires explicit trigger
[ ] Critic skip has deterministic rationale
[ ] Correction loop has finite stop condition
[ ] No-progress detection tested
[ ] Delta workflows cannot bypass required obligations
[ ] Baseline and optimized benchmarks retained
[ ] Equivalent deterministic acceptance demonstrated
[ ] Roadmap/tasks/ADRs/acceptance reconciled
```



# 25. Proposed optimization package structure

Recommended:

```text
src/score_sw_fabric/optimization/
├── __init__.py
├── task_classification.py
├── context_manifest.py
├── context_budget.py
├── skill_selection.py
├── skill_registry.py
├── token_governor.py
├── model_router.py
├── review_pack.py
├── tool_summary.py
├── evidence_query.py
├── evidence_normalize.py
├── tool_output_policy.py
├── progress.py
└── metrics.py

.agents/skills/
├── score-requirements/
├── score-architecture/
├── score-component-fmea/
├── score-dfa/
├── score-implementation/
├── score-verification/
├── score-quality-review/
└── score-change-impact/
```

Avoid creating abstractions until contracts and tests justify them.

---

# 26. Schemas to add

Recommended records:

```text
task-classification-v1
context-manifest-v1
context-accounting-v1
skill-registry-v1
skill-selection-v1
token-governor-decision-v1
review-pack-v1
tool-summary-v1
evidence-query-result-v1
normalized-finding-index-v1
tool-output-policy-v1
optimization-metrics-v1
```

Every record should be:

- versioned;
- deterministic where applicable;
- bounded;
- digestible;
- explicit about unknown values;
- baseline-bound where required.

---

# 27. Tests required

Use negative-first development.

## Task classification

Test:

- S0;
- S1;
- S2;
- S3;
- unknown;
- safety escalation;
- architecture escalation;
- high dependency fan-out;
- unresolved dependencies.

## Context manifest

Test:

- exact affected subset;
- transitive context;
- stale baseline rejection;
- unknown dependency widening;
- deterministic ordering;
- digest stability;
- bounded size.

## Context budgeting

Test:

- L0 cannot be dropped;
- required safety context cannot be trimmed;
- optional context drops first;
- oversized manifests fail closed;
- no arbitrary silent truncation.

## Skills

Test:

- deterministic mapping from obligation/work-product type to Skill;
- stable Skill digest;
- modified Skill invalidates prior selection;
- only selected Skill body is loaded;
- unselected Skill reference material is not injected;
- Skill references are loaded only on demand;
- oversized Skill is rejected or explicitly bounded;
- Skill cannot grant approval/decision authority;
- missing Skill produces explicit blocked/unsupported state;
- runtime rendering is byte/digest bound;
- Codex Skill presence does not imply Fabro runtime availability.

## Raw evidence / tool-output firewall

Test:

- raw SARIF grep is rejected above configured size/line threshold;
- bounded SARIF query returns only requested fields;
- raw evidence digest/path is retained;
- normalized summary preserves exact rule/path/line identity;
- oversized minified JSON cannot enter LLM context through generic `read_file`;
- grep result byte/token ceiling is enforced;
- per-stage total tool-result budget is enforced;
- truncation is explicit and references complete evidence;
- repeated broad query is refused with narrower-tool guidance;
- collector-generated summary is deterministic and digest-stable;
- raw evidence remains available for deterministic verification and human inspection.

## Silent execution

Test:

- stage prompts contain the no-narration rule;
- routine stage output validates against structured schema;
- no required rationale field is lost;
- human-facing summary is deferred to terminal package;
- stage completion can occur with no free-form explanatory prose.

## Token governor

Test:

- class budget enforcement;
- absolute ceiling preservation;
- unknown usage blocks unsafe continuation;
- correction visit limit;
- escalation conditions;
- critic conditions;
- premium model refusal without trigger.

## Tool summaries

Test:

- full logs preserved;
- summary bounded;
- first failure retained;
- evidence ref valid;
- truncation explicitly reported;
- malicious/huge output bounded.

## Progress detection

Test:

- changed source;
- fewer findings;
- no progress;
- repeated identical failure;
- changed evidence but no source change;
- correction loop cutoff.

## Workflow modes

Test:

- full;
- delta;
- correction;
- verification-only;
- evidence-refresh.

---

# 28. Benchmark design

Before changing defaults, capture baseline runs.

Select at least five representative tasks:

```text
B1 — metadata/mechanical
B2 — localized C++ correction
B3 — unit-test correction
B4 — component feature
B5 — safety/architecture-sensitive change
```

For each task, record:

```yaml
baseline:
  input_tokens:
  cached_input_tokens:
  uncached_input_tokens:
  output_tokens:
  reasoning_tokens:
  model_calls:
  tool_calls:
  cost:
  wall_time:
  corrections:
  critic_calls:
  escalations:
  deterministic_result:
  final_result:
```

Repeat after optimization.

Compare equivalent engineering outcomes.

---

# 29. Initial optimization targets

Use these as engineering targets, not release claims.

Primary target:

> Reduce uncached LLM input tokens by **60–80%** for routine/localized tasks while preserving the same deterministic acceptance outcome.

Secondary targets:

- reduce routine model calls;
- reduce critic calls;
- reduce correction loops;
- reduce full-process workflow use;
- preserve or improve wall time;
- zero loss of required traceability;
- zero loss of evidence;
- zero reduction in deterministic checks;
- zero autonomous human/safety decisions.

Do not accept token savings that weaken assurance.

---

# 30. Recommended Spec Kit implementation sequence

Every phase below must be represented in the active Increment 011 `tasks.md`.

## Phase 0 — Spec Kit control plane

Before implementation:

1. inspect `.specify/memory/constitution.md`;
2. inspect roadmap/requirements index/ADRs;
3. inspect any existing Increment 011 material;
4. use `$speckit-constitution` only if required global principles are missing;
5. run `$speckit-specify`;
6. run `$speckit-clarify` for material unresolved ambiguity;
7. run `$speckit-plan`;
8. run `$speckit-checklist`;
9. run `$speckit-tasks`;
10. run `$speckit-analyze`.

Do not begin broad implementation before the analysis identifies a consistent spec/plan/task set.

## Phase 0A — Emergency tool-output containment

Implement before broader context/model optimization:

- structured-evidence raw-access policy;
- pre-tool-use rejection of unsafe SARIF/minified-JSON reads;
- bounded evidence-query primitives;
- collector-normalized summaries;
- per-tool output ceilings;
- per-stage aggregate tool-result budget;
- silent-execution common prompt contract;
- structured stage completion output.

Add a regression fixture reproducing a single-line SARIF/JSON match that would otherwise return an extremely large line.

The test must demonstrate bounded model-facing output while preserving complete raw evidence.

Run `$speckit-converge`.

## Phase 1 — Measure first

Implement:

- usage metrics;
- cached/uncached accounting;
- per-task aggregation;
- benchmark fixtures;
- baseline benchmark records.

Do not tune budgets before baseline metrics exist.

Run `$speckit-converge` for this phase.

## Phase 2 — Impact-driven Context Manifest

Implement:

- Increment 011 transitive impact/freshness;
- task classification;
- affected-scope derivation;
- Context Manifest;
- L0/L1/L2 context.

This should produce the largest savings.

Run the relevant contract/integration tests and `$speckit-converge`.

## Phase 3 — Skills

Implement:

- Skill registry;
- deterministic Skill selection;
- the initial 6–8 narrow S-CORE Skills;
- progressive disclosure;
- digest binding;
- explicit Codex/Fabro runtime boundary;
- bounded runtime Skill rendering/retrieval.

Do not embed complete process documents in Skill bodies.

Run `$speckit-analyze` again if Skill introduction changes interfaces or assumptions.

## Phase 4 — Tool-result compression

Implement:

- bounded summaries;
- evidence refs;
- result token ceilings;
- precise retrieval primitives.

Run `$speckit-converge`.

## Phase 5 — Token Governor

Implement:

- operational budgets;
- context budget;
- Skill budget;
- model routing;
- correction limits;
- stop conditions;
- unknown-usage handling.

Run `$speckit-converge`.

## Phase 6 — Conditional critic / escalation

Implement:

- deterministic critic trigger;
- stronger-model trigger;
- supervisor trigger;
- Review Pack.

Run `$speckit-converge`.

## Phase 7 — Delta workflows

Implement:

- full;
- delta;
- correction;
- verification-only;
- evidence-refresh.

Ensure no mode can omit a mandatory S-CORE obligation.

Run `$speckit-analyze` and `$speckit-converge`.

## Phase 8 — Benchmark and tune

Measure all representative tasks.

Only then adjust default budgets.

Retain original baseline evidence.

Update acceptance criteria with measured results.

## Phase 9 — Final Spec Kit reconciliation

Before claiming completion:

```text
$speckit-analyze
$speckit-converge
```

Then reconcile:

```text
spec.md
plan.md
tasks.md
checklists
acceptance.md
requirements index
ADRs
roadmap
profiles/policies
README / operator guidance
```

No task may be checked solely because code exists; required validation and acceptance evidence must exist too.



# 31. Codex execution constraints

Codex shall:

1. inspect the current repository before modifying anything;
2. use the repository's Spec Kit workflow as the implementation control plane for every optimization slice;
3. not implement broad changes before `spec.md`, `plan.md`, `tasks.md`, the relevant checklist(s), and `$speckit-analyze` are coherent;
4. preserve all existing user work;
5. preserve historical evidence;
6. never rewrite historical evidence to make results look cleaner;
7. write tests before or alongside implementation;
8. preserve current public CLI behavior unless a specification explicitly changes it;
9. avoid altering protected native reference repositories;
10. use disposable copies for native builds;
11. not enable live model calls without explicit existing authorization;
12. not create or infer human approvals;
13. not mark human-owned tasks complete;
14. preserve fail-closed behavior;
15. keep Skills narrow, lazy, versioned and procedural;
16. never encode authoritative applicability, gate, verification, safety or release decisions only in Skills or prompts;
17. bind selected Skill versions/digests to the execution context;
18. never assume Codex Skills are automatically available to Fabro runtime agents;
19. update ADRs, roadmap, requirements index, tasks and acceptance records when implementation state changes;
20. run the full relevant regression suite before claiming completion;
21. preserve existing evidence of failed, skipped or unavailable native executions;
22. treat unknown token/cost/cache usage as unknown, never as zero;
23. never reduce required deterministic checks solely to save tokens;
24. run `$speckit-converge` after each major phase and at final handoff.


# 32. Self-consistency requirement

Because this project is itself a process-assurance engine, implementation status must not drift from documentation.

Add or extend a self-audit that checks consistency between:

```text
spec
tasks
implementation
tests
acceptance
ADRs
roadmap
profiles/policies
```

Token optimization must not create another layer of undocumented behavior.

---

# 33. Suggested new ADRs

Consider adding:

## ADR — Structured evidence is not conversational context

Decision:

> Large machine-generated evidence remains immutable raw evidence and is queried through bounded deterministic adapters. Generic tools may not inject unbounded SARIF/JSON/log payloads into model conversation history.

## ADR — Silent autonomous execution

Decision:

> Autonomous factory agents do not narrate their execution process. They return schema-required artifacts/results; explanatory rationale is emitted only where required by an engineering work product.

## ADR — Tool-result context budget

Decision:

> Every model stage has both per-result and aggregate tool-result context ceilings. Complete outputs are retained by reference rather than copied into model history.

## ADR — Deterministic-first token optimization

Decision:

> Deterministic mechanisms shall narrow agent context and execution scope before model invocation.

## ADR — Lazy context loading

Decision:

> Agent context is divided into L0/L1/L2. L2 is retrieved only on demand.

## ADR — Operational budgets versus hard ceilings

Decision:

> Hard safety ceilings remain large enough for exceptional tasks, while normal calls receive task-class-specific operational envelopes.

## ADR — Conditional independent critique

Decision:

> AI critique is invoked based on deterministic policy, not universally.

## ADR — Lazy procedural Skills

Decision:

> Engineering procedures may be packaged as narrow Skills and loaded only when selected by deterministic obligation/task context.

## ADR — Skill/runtime boundary

Decision:

> `.agents/skills` is an authoritative repository source for procedural guidance, but Fabro runtime availability must be explicitly rendered/retrieved and digest-bound unless verified native runtime support is pinned.

## ADR — Spec Kit-controlled optimization

Decision:

> Token/cost optimization is developed through Spec Kit work products and cannot bypass the project's specification/planning/task/acceptance lifecycle.

## ADR — Evidence/context separation

Decision:

> Complete evidence remains retained outside LLM conversation history; agents receive bounded summaries and references.

---

# 34. Expected end state

The optimized Fabric should behave approximately as follows:

```text
                       Spec Kit
                          |
                          v
                     Change Request
                          |
                          v
                Process / Obligation Engine
                          |
                          v
                 Change Impact / Freshness
                          |
                          v
                  Task Classification
                          |
                          v
                    Context Manifest
                          |
                          v
                     Token Governor
                 /         |         \
                /          |          \
             Context     Skills       Model
            L0/L1/L2   selected     selected
                \          |          /
                 +---------+---------+
                           |
                           v
                         Agent
                           |
                           v
                Deterministic Validation
                           |
                      +----+----+
                      |         |
                    PASS       FAIL
                      |         |
                     done   one bounded correction
                                |
                                v
                      escalation only if justified
                                |
                                v
                      optional critic/supervisor
```

The model should receive the **minimum sufficient engineering context and minimum necessary procedural Skill content**.

The Fabric should retain the **maximum required assurance evidence**.

These are intentionally different quantities.

Spec Kit should retain the **complete implementation intent, plan, backlog and convergence evidence** without being injected wholesale into runtime agent prompts.



# 35. Final design principle

Use this principle when choosing between implementations:

> **As the deterministic Fabric becomes more capable, each individual AI agent should need less context, fewer turns, fewer tools, and less authority.**

The goal is not merely to reduce API cost.

The goal is to make S-CORE SW Fabric:

- cheaper;
- more predictable;
- faster;
- more reproducible;
- easier to audit;
- safer to operate unattended;
- less dependent on any specific LLM provider.

---

# 36. Definition of done

This optimization increment is complete only when all of the following are demonstrated:

- Increment 011 is specified/planned/tasked/analyzed through Spec Kit;
- required Spec Kit checklist(s) exist and are reconciled;
- Skills are represented in the Spec Kit requirements/plan/tasks rather than added ad hoc;
- a bounded Skill registry exists;
- deterministic Skill selection exists;
- selected Skill digests are bound to execution context;
- Skill progressive disclosure is implemented;
- Codex/Fabro Skill boundary is explicit and tested;
- raw SARIF/minified structured evidence cannot enter model context through unrestricted generic tools;
- bounded deterministic evidence-query adapters exist;
- collectors produce normalized agent-facing summaries alongside raw evidence;
- per-tool output ceilings exist;
- per-stage aggregate tool-result budgets exist;
- silent-execution/no-narration prompt policy exists;
- intermediate stages return structured completion output instead of verbose execution prose;
- deterministic task classification exists;
- Context Manifest exists;
- L0/L1/L2 context behavior exists;
- observation text is lazy by default;
- token-aware context accounting exists;
- operational budgets exist separately from hard ceilings;
- Token Governor exists;
- conditional model escalation exists;
- conditional critic invocation exists;
- tool results are summarized before agent reinjection;
- full evidence remains preserved;
- delta/correction/verification-only modes exist where applicable;
- progress/no-progress detection exists;
- token/cost telemetry exists;
- baseline and optimized benchmark results are retained;
- routine tasks show material uncached-token reduction;
- deterministic acceptance outcomes remain equivalent;
- assurance/human authority boundaries remain unchanged;
- roadmap/tasks/ADRs/acceptance are reconciled with implementation state.

---

# 37. Codex starting instruction

Use the following as the initial execution directive:

> Implement this brief in `jnsagai/s-core_sw_fabric` through the repository's Spec Kit workflow. First inspect the current repository, `.specify/memory/constitution.md`, roadmap, requirement index, ADRs and any existing Increment 011 material. Before broader token optimization, reproduce and eliminate the demonstrated failure mode in which generic grep/read of minified SARIF/JSON injects extremely large tool results into model conversation history. Preserve all existing work and historical evidence. If the constitution does not already express deterministic-first context minimization, evidence/context separation, lazy procedural Skills, operational budgets and conditional escalation, amend it through `$speckit-constitution` without weakening existing principles. Then create or extend `specs/011-change-impact-and-freshness` with `$speckit-specify`, using change impact/freshness as the source for token-efficient bounded re-analysis. Run `$speckit-clarify` only for material ambiguity not resolved by this brief, then `$speckit-plan`, `$speckit-checklist`, `$speckit-tasks` and `$speckit-analyze` before broad implementation.
>
> Implement the work incrementally in the order: (1) emergency raw-evidence/tool-output containment with bounded SARIF/JSON query adapters, collector-normalized summaries, per-tool and per-stage result budgets, and silent-execution prompts; (2) baseline token/cost/cache telemetry; (3) transitive impact/freshness and deterministic task classification; (4) Context Manifest and L0/L1/L2 lazy context; (5) narrow S-CORE Skills with deterministic Skill selection and progressive disclosure; (6) an explicit Codex-Skill/Fabro-runtime boundary with digest-bound rendering or retrieval; (7) Token Governor with operational budgets and hard ceilings; (8) conditional model routing/critic/supervisor escalation; (9) progress/no-progress termination; (10) full/delta/correction/verification-only/evidence-refresh workflows; and (11) before/after benchmarks.
>
> Keep applicability, obligations, traceability, freshness, evidence trust, gate state, verification results, safety acceptance and human authority deterministic or human-owned; never move those decisions into Skills or LLM prompts. Skills teach one engineering activity and should normally remain about 1–3k tokens, with detailed references/scripts/templates loaded only on demand. Do not assume `.agents/skills` are automatically available inside Fabro; runtime Skill use must be explicitly supported, versioned, digest-bound, context-accounted and bounded.
>
> Use negative-first tests, keep full evidence outside LLM conversation history, and do not enable live model calls or complete human-owned tasks without existing explicit authorization. After every major phase, run the relevant deterministic checks and `$speckit-converge`; rerun `$speckit-analyze` after material scope/interface changes. Establish baseline measurements before changing token budgets. Do not claim completion until the Spec Kit requirements, plan, tasks, checklists, acceptance, ADRs and roadmap are reconciled and representative tasks demonstrate materially lower uncached input-token consumption with equivalent deterministic engineering outcomes.

---

# 38. Immediate Codex deliverables

The first Codex pass should produce reviewable Spec Kit artifacts before broad code changes.

Expected first-pass outputs:

```text
.specify/memory/constitution.md
    only if a justified amendment is required

specs/011-change-impact-and-freshness/
├── spec.md
├── plan.md
├── tasks.md
├── quickstart.md
├── acceptance.md
├── contracts/
├── schemas/
└── checklists/
```

The plan should explicitly map proposed implementation to:

```text
src/score_sw_fabric/artifacts/
src/score_sw_fabric/assurance/
src/score_sw_fabric/agents/
src/score_sw_fabric/compiler/
src/score_sw_fabric/planning/
src/score_sw_fabric/optimization/
.agents/skills/
profiles/
policies/
schemas/
tests/
```

The first implementation task should be **raw structured-evidence/tool-output containment**, because a single unsafe SARIF/JSON query can dominate token usage. Immediately after containment, establish **measurement** before changing model budgets.

The second should establish **baseline token/cost/cache telemetry**.

The third should establish the **impact → Context Manifest** path.

The fourth should establish the **Skill registry/selection** path.

Only after those are measurable should Codex tune model budgets and escalation policy.
