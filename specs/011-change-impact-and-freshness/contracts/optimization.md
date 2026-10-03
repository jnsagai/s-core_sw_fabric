# Versioned optimization contract

New additive command group: `score-fabric optimization`. Query: `evidence --root ROOT --path PATH
--operation summary|findings|count_by_rule|count_by_path|json_summary --rule RULE --file FILE
--line N --offset N --limit N`. Output is a sealed bounded record with raw path/SHA-256/bytes,
exact total, pagination, omitted-field/gap counts and no raw messages. Limit <=30; default 10.
`serve --root ROOT --state PATH` exposes bounded stdio MCP tools; generic shell/read/grep are absent.
`benchmark --output DIR` records five fixture comparisons without provider calls.
`audit --root ROOT` checks 011 spec/task/coverage/implementation artifacts. Exit 0 success,
1 refused/blocked decision, 2 malformed input. No raw input is echoed in diagnostics.

`prepare --request FILE` consumes `optimization_prepare_request`; old/new index references
are checksum-bound and the explicit native-ID/path mapping derives impact, manifest and class.
`context --request FILE` and `govern --request FILE` consume new
`optimized_agent_context_request`/`optimized_agent_admit_request` contracts and validate their
checksum-bound legacy requests before narrowing context/admission. Equivalent entrypoints are
`agent context-optimized` and `agent admit-optimized`. `classify`, `mode` and `skills` consume
the corresponding `optimization_*_request` schemas. They produce records without runtime effects.

The service publishes exact tool input schemas. Finding queries support rule/file/line filters
and offset pagination; `finding_get` returns one row at an offset. Source excerpts require an
explicit path/SHA-256 manifest, at most 250 lines and 3,000 UTF-8 bytes. Observation retrieval
requires an ID and raw-log digest and returns a hint, never accepted evidence. Generic tools
cannot substitute for these operations. A refusal persists a stage stop; restart cannot reset it.

The firewall allows only registered bounded query/retrieval tools for optimized evidence ingress.
Generic read/grep/shell/broad MCP reads are refused rather than pretending native post-hook result
rewriting exists. SOME/IP legacy source reads are narrowed to explicit source/summary paths and
bounded reads; new structured reports use summary records. Existing frozen runs do not change.

Every result has a byte ceiling covering the entire serialized result including references and
metadata. Token estimates are labelled conservative UTF-8-byte upper bounds, not provider usage.
Repeated exact queries and exhausted persistent aggregate budgets refuse further retrieval.
Raw artifact digest bindings also persist across requests and restarts. MCP escaping/envelope
overhead is included in result/stage accounting. Measured shared-storage bindings are checked
before each operation; disconnect or selection drift stops rather than relocating state.
Oversized native identity fields are omitted with explicit counts; identities are never clipped.
Safe path resolution validates every component, including symlinks and output-parent links.

Context/classification/Skill/governor adapters accept sealed records with declared bindings.
Authority comes from 004/005/007 contracts and caller-owned reviewed policy, never from an
optimization record or Skill. Existing admission must be admissible before governor can narrow
it. Missing usage/capability/destination/authority cannot be overridden. Routing uses catalogue
profile IDs supplied by the existing admitted record. Mode plans retain all supplied mandatory
checks and human gates. No plan updates a native gate or launches a model/runtime.

Provider fields remain null for offline fixtures. Offline benchmark estimated-context savings
cannot satisfy live uncached-token/cost acceptance. Runtime configuration is a source-checked
candidate until native activation and hook/service qualification are measured separately.
The pinned native validator accepts the candidate configuration and narrowed agent graph.
Default guard calls without a private qualification instruction refuse every live stage.
Neither a sealed optimization record nor `call_authorized=true` grants execution.
The explicit US12 owner continuation permits a disposable Flash-only experiment, separate
from production engineering authority and default 007 admission.

The private instruction uses `kind=qualification_instruction`, `scope=qualification_only`,
exact owner-message references, workspace/stage/task, current context/governor/role/Skill
bindings, pinned file hashes, run-binding path, Flash aliases, limits, price bounds and
exact task prompts. Its SHA-256 is an operator input to `guard --instruction FILE
--instruction-sha256 SHA`. Private input files must be owned by the operator, without
symbolic ancestors, mode 0600 within private directories and outside the agent workspace.
Private Unix files do not isolate hostile processes sharing the operator account.

For pinned Fabro 1b4fb152, native hook `run_id` is `petri`; tool contexts also omit cwd.
The exact run-specific private host cwd, checked against the process cwd in the CLI,
binds the native API ID. The private run record pins source commit, API run ID, workflow
version and exact native cwd; another cwd, scope, stage or identity refuses. This is
revision-specific measured qualification, not a claim about other Fabro releases.

The loopback transport admits only DeepSeek Flash to its fixed upstream endpoint.
Entire serialized native input and projected provider input each remain <=24,000 bytes,
output <=2,000 tokens, <=10 calls and conservative total reservations <=$0.10. Per-task limits additionally narrow these ceilings to the exact pinned governor;
serialized transmitted input and reserved output accumulate across its requests. A
persistent lock-protected reservation precedes transmission; failed/unknown/in-flight
outcomes stop further requests, including restart. Missing required input/output/cache
usage stops. Optional reasoning usage is retained when explicitly reported; missing
billed cost remains null. Peak source-derived pricing bounds are not actual invoices.
Explicit native run titles prevent unrelated model calls. Only the separate disposable
server holds its one DeepSeek credential; no existing queue or global profile changes.

Optional `tool_projection.allowed_tools` selects registered bounded tool names. The
transport removes only already-denied/unselected function declarations. It preserves all
messages and selected declarations, rejects missing selected tools or unavailable explicit
tool choices and records original/transmitted hashes and sizes. The native guard uses
the same selection. Absence of projection preserves the request byte-for-byte.
Current live measurements predate projection; its measured replay is offline only.
