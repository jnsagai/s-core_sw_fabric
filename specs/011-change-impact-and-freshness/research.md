# Research decisions

- Reuse 004 native index/trace and 005 freshness rather than inventing semantic identifiers.
  004 currently traverses only new edges; use both baselines and seed relation changes so removed
  dependencies cannot disappear. Keep native IDs/status/license text unchanged.
- Existing 007 MCP client is discovery-only and cannot protect Fabro builtins. Source inspection
  and the SOME/IP `pre_tool_use` guard identify the real admission boundary. Optimized stages
  deny generic evidence reads/broad grep and use a repository-owned bounded stdio service;
  no unverified post-tool output replacement is relied upon.
- Collectors currently deliver raw reports into workspace feedback. Retain full host feedback
  archive but copy only bounded summaries and completion flags to new agent feedback.
- UTF-8 bytes are a conservative upper token estimate for byte-based tokenizers. This is an
  explicit operational estimate; actual tokenizer/provider/cache data stays unknown until observed.
  No live provider, model ID or price is introduced.
- Skill bodies and explicitly declared references are baseline-bound. Codex Skills are source
  procedures, not automatically installed Fabro tools. Render selected content explicitly.
- Existing exact v1 field sets need additive v2/optional optimization boundaries, not silent field
  changes. New output schemas are separate; historical files and running queues stay immutable.
- Stage budget state is local derived accounting only. Serialize updates with host file locks;
  persist consumption before returning a tool result, including across service restarts.
- Current user requested implementation and preservation of human review. Checklist review does
  not grant engineering authority. Pending owner ratification, live savings and operational
  qualification cannot be checked off by implementation tests.

## Scoped native findings (2026-10-03)

- Pinned Fabro command hooks use host stdin and report `run_id=petri`; stage cwd is exact
  API-run-specific host scratch, tool events omit cwd but process cwd remains that workspace.
  Private binding therefore checks the pinned source revision and exact host cwd, not the
  common hook ID alone. Source: fabro-config storage.rs, fabro-petri workspace.rs/hooks.rs
  at 1b4fb152; real captured hook contexts confirm behavior.
- Explicit native RunIntent.title prevents small-default model title calls. Native secret
  transfer uses source-checked POST /api/v1/secrets rather than copying server databases.
- Real Flash replies supply cache hit/miss, total completion and optional reasoning usage.
  Native output excludes reasoning; output+reasoning reconciles to provider completion.
  Catalogue cost is stale. Current conservative peak rates and legacy alias compatibility
  are from https://api-docs.deepseek.com/quick_start/pricing/ and provider thinking-mode/API docs.
- Fixed system/tool overhead limits the initial fixture savings to about 30.5%. Native
  config exposes no builtin filter. Repository transport now optionally projects only
  registered bounded declarations under a pinned instruction and native guard selection;
  messages and selected schemas remain unchanged. Projection has offline replay only.
