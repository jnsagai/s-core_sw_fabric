# Runtime and CodeQL source review — 2026-09-27

This is source inspection, not an installed-runtime validation or live-provider smoke test. References were read-only; no runtime installation, model calls, source builds, or upstream writes were performed.

## Revisions and recommendation

| Source | Exact revision | Result |
|---|---|---|
| `/tmp/s-core-foundation/references/fabro-stable`, v0.254.0 | `497aaba6f20c1fac052346c39f52e08fabadb179` | MIT; examined stable release lacks required workflow-version registration and built-in DeepSeek catalogue. Not compatible with the full brief without scope changes. |
| `/home/jefferson/fabro`, Cargo version 0.362.0-nightly.0 | `1b4fb15281ebb724426f9e480dce48d0100ff79b` | MIT; exact source candidate supports version registration, but is not a validated compatible release. Working tree was clean. |
| `/tmp/s-core-foundation/references/codeql-coding-standards`, v2.61.0 | `06dc6bc32b05152fbe94dbf341a3e854574c9df5` | MIT with exceptions; explicit supported CodeQL environment is CLI 2.21.4 / standard library codeql-cli/v2.21.4 / codeql-bundle-v2.21.4. |

Recommended foundation decision: preserve both Fabro pins as investigated sources, mark the runtime-release selection unresolved before compiler/runtime increments, and do not pretend stable satisfies the registry contract. Increment 001 importer does not need a runtime. The brief explicitly requires a compatible release and forbids an unreviewed nightly installer; adopting a nightly silently would violate that requirement. A reviewed candidate build with bounded fixture tests can be considered later, or a compatible stable release selected then. Do not install or upgrade the runtime during 000.

## Stable Fabro evidence

Paths below are relative to the stable checkout unless prefixed otherwise.

- `Cargo.toml:8-9` declares version and MIT; `LICENSE.md` names Qlty Software Inc. and notice preservation.
- `docs/public/workflows/stages-and-nodes.mdx` describes DOT-based `.fabro` graph semantics: one start `Mdiamond`, one exit `Msquare`, agent `box`, prompt `tab`, shell/Python command `parallelogram`, human `hexagon`, conditional `diamond`, parallel/merge and child workflow machinery. Graph parser/validation belongs to Fabro; compiler must emit a pinned subset and use native validation, never infer acceptance from graph validity.
- `docs/public/execution/run-configuration.mdx:14-31` defines TOML `_version = 1`, `[workflow] graph = "workflow.fabro"`, `[run] goal`; graph paths relative to configuration file. `_version` omitted defaults to 1; legacy top-level `version` rejected. Named workflows resolve `.fabro/workflows/<name>/workflow.toml` (AGENTS).
- `lib/crates/fabro-cli/src/commands/validate.rs` implements `fabro validate <workflow>` via native manifest build and validation. Global JSON output returns `workflow_name`, `nodes`, `edges`, `valid`, `diagnostics`; errors cause nonzero failure. This was read, not executed. Validation loads local settings/catalog, so future deterministic verification must isolate configuration and record it.
- `lib/crates/fabro-mcp-server/src/server.rs:53-203` exposes `fabro_run_create`, `fabro_run_search`, `fabro_run_get`, `fabro_run_interact`, `fabro_run_gather`, `fabro_run_pair`, `fabro_run_events`. No workflow-version registration tool exists. `lib/crates/fabro-tool/src/create.rs` accepts workflow selector strings or objects with `workflow`, unlike nightly version IDs.
- `docs/public/api-reference/fabro-api.yaml` contains native run create/start/resume/validation APIs (OpenAPI is upstream wire source of truth). Reuse these rather than create a scheduler.
- `lib/crates/fabro-interview/src/auto_approve.rs`: automatic interviewer answers yes/confirmation positively, selects first option for choice/multi-select, and emits `auto-approved` freeform with a system actor.
- `lib/crates/fabro-interview/src/replay.rs`: replay drops question matching and replays recorded answer submissions in sequence, including their actors; exhausted replay returns interrupted. A recorded user actor alone therefore does not prove fresh human authorization.
- `lib/crates/fabro-workflow/src/handler/human.rs:269-308`: timeout with `human.default_choice` returns selected-choice outcome; absent default returns retry-classified timeout. Interrupted/absent answers do not automatically approve. `docs/public/workflows/human-in-the-loop.mdx` explicitly documents auto-approve, timeout defaults and fail-closed missing input.
- Consequence: engineering approval requires independently verified authenticated identity, authority, current scope/baseline/evidence bindings and fresh signed/authenticated decision provenance. Reject auto mode, replay and success defaults both at compilation and submission. Runtime gate traversal is never the approval record.
- `docs/public/execution/checkpoints.mdx`: stable uses `fabro/run/{id}`, orphan `fabro/meta/{id}`, and durable run store. Metadata/code Git writes are best effort; durable checkpoint remains authoritative for resume. Checkpoint commits disable signing. Thus neither Git trailers nor run success prove signed evidence/acceptance. Resume/fork/rewind APIs are native.
- Recursive source search `rg -n 'DeepSeek|deepseek' <stable>` returned no matches. `docs/public/core-concepts/models.mdx:41` supports custom provider/model catalogue overlays with string IDs and OpenAI-compatible transport; that is an extension capability, not verified DeepSeek compatibility.

## Nightly differences and candidate contract

Paths below relative to `/home/jefferson/fabro`.

- `lib/apps/fabro-mcp-server/src/server.rs:89-126` implements `fabro_workflow_version_create`, then `fabro_run_create` from registered IDs. `lib/components/fabro-tool/src/workflow_version.rs` accepts `{entrypoint, files}` (package-relative text file map), validates paths, entrypoint presence, collisions and size; packaging resolves local closure before registration. Treat this as a candidate native boundary, not a fabric API already implemented.
- `lib/components/fabro-tool/src/create.rs`: `runs` length 1–50; objects require `workflow_version_id`; standalone calls require explicit `target` (including `kind: none` for empty workspace), canonical `args`, optional environment/parent/title/goal/start. `start` defaults true, so review tooling must explicitly suppress start when registering/preparing only. Registration itself does not create or start runs.
- `Cargo.toml:107-116` delegates workflow engine/frontends to Petri; `Cargo.lock` resolves Petri to `153d586871824b8023a5691e49a1e99421bae282`. This is a significant engine boundary change, not just a renamed crate.
- `lib/apps/fabro-cli/src/commands/validate.rs` keeps native manifest validation/JSON diagnostics but uses the newer engine path.
- `docs/public/workflows/stages-and-nodes.mdx:17` describes explicit `type` precedence over shape, and script-inferred command behavior when both omitted. Emit explicit behavior and validate against the selected runtime.
- `docs/public/execution/checkpoints.mdx` replaces metadata branches with durable events/projections and content-addressed artifacts; `fabro dump` exports run files. Current code uses Petri SQLite/event store. Fabric must not bind portable evidence to obsolete metadata-branch internals.
- `lib/components/fabro-petri/src/interview.rs:400` still calls `AutoApproveInterviewer` for automatic approval; docs retain timeout defaults. Engineering restrictions remain necessary.
- `docs/public/integrations/deepseek.mdx` lists candidate model IDs `deepseek-v4-flash` and `deepseek-v4-pro`, provider `deepseek`, capability-specific effort controls, and bearer Chat Completions endpoint. However `lib/components/fabro-llm/src/catalog.rs:1-50` now builds catalogue from `lithos_llm` builtins plus operator overlay. Local docs do not replace installed catalogue/remote capability verification. Do not claim these IDs, credentials, prices or reasoning settings were live-tested. No model pricing should be used as a fixed budget fact without current provider verification.
- Native checkpoint/schema/grammar changes require conformance fixtures at adoption; exact current docs are not evidence that v0.254.0 has these capabilities.

## CodeQL constraints and terms

- `supported_codeql_configs.json` specifies exactly one tested environment: CLI 2.21.4, standard library `codeql-cli/v2.21.4`, bundle `codeql-bundle-v2.21.4`. Record this as an exact compatibility pair, not an invented minimum version range.
- `docs/user_manual.md:155-162` requires report scripts' Python interpreter version 3.9 and a CLI listed in that release artifact. Keep tooling isolated from fabric Python tooling; do not assume fabric Python version covers qualified report environment.
- `README.md:49-60`, `LICENSE.md`: repository code is MIT unless otherwise noted; CERT query-help material under `thirdparty/cert/LICENSE` is CC BY 4.0 with MIT code examples; all thirdparty subdirectory notices and `c/common/test/includes/standard-library/LICENSE` apply separately. CLI distribution entitlement/license is distinct and was not established by reading query-source MIT license.
- README qualification language is conditional on distributed tooling and user manual requirements. A clean CodeQL report does not prove full rule coverage, safety acceptance, tool qualification for this deployment, or release readiness. Manual lists unsupported and partially supported rules/compiler/language constraints; preserve coverage and applicability.

## Commands and limits

All source reads used escalated read-only shell commands because parent reported sandbox mountinfo failure. Main reproducible checks: `git -C <source> rev-parse HEAD` (three SHAs above); `git -C /home/jefferson/fabro status --short` (empty); `rg --files -g AGENTS.md <codeql>` (none); `cat <source>/AGENTS.md` for both Fabro checkouts; `cat`/`sed -n` of source paths above; recursive `rg -n` for exact tool/model names and version identifiers. Several exploratory searches of nonexistent guessed paths returned exit 2 and were replaced with actual discovered paths; no capability inference relies on those failures. No executable runtime validation, CodeQL analysis, or provider tests were run. Full terminal commands remain in session tool history.
