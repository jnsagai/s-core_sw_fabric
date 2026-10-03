# SOME/IP factory execution correction

This directory connects the earlier external candidate to the existing fabric
compiler and Fabro runtime. It does not reattribute the patch to Fabro or an agent.

## Current queue and diagram

Run `01M3YRJEGXNY6CB81T7TKW774B` reached human review after 93 completed workflow
stages, then timed out without an answer at 19:56 Lisbon on 2026-10-02. It is stopped;
no successor is running. Latest candidate source and reports are preserved.
Verification has failed/unavailable checks and unresolved findings. Engineering
acceptance remains pending. See the [terminal observation](runs/score-someip84-factory-2fekt_ew/terminal-status.json)
and [measured verification report](runs/score-someip84-factory-2fekt_ew/verification-report-result.json).

[Current workflow SVG](current-workflow.svg) shows all 99 nodes and their
transitions. [Expanded SVG](current-workflow-expanded.svg) preserves the Graphviz
layout. See [current status and run path](overnight-queue.md) and
[verified restart evidence](runs/score-someip84-factory-2fekt_ew/restart-status.json).

## Actual workflow

1. A local operational draft plan binds the user's execution instruction, frozen
   native source manifests, regression input, external patch and tool identities.
   Its local instance IDs are not native S-CORE engineering needs or accepted tailoring.
2. The fabric compiler projects the mapping into its IR and a closed native package.
   Every command binds packaged script content through `command_file`; none of the
   demonstrator's checks use the historical prototype `script="true"` rendering.
3. The pinned Fabro validator accepts the actual package. The existing fabric runtime
   registers its immutable version, creates one disposable run and starts it once.
4. Fabro executes fresh GCC/GTest baseline and external-candidate measurements.
   The latter applies the earlier patch to a fresh baseline copy; it is validation
   of external work, not a new agent implementation.
5. Execution stops at an unanswered configuration gate. Native status/events/outputs
   are exported and independently replayed; no engineering decision is submitted.

The rebuilt runtime comes from commit
`1b4fb15281ebb724426f9e480dce48d0100ff79b`, rebuilt offline in a bound SSD
disposable copy with the recorded 32,768-event overlay. The executable is installed
at `/home/jefferson/.local/share/s-core-tools/fabro-1b4fb152-agent32768/fabro`.
Reference repositories stay read-only. Each run records
the rebuilt executable and source API hashes separately from older runtime trials.

## Commands

From a normal terminal with the existing local inputs/tools:

```bash
cd /home/jefferson/s-core_sw_fabric
SCORE_FABRO_BIN=/home/jefferson/.local/share/s-core-tools/fabro-1b4fb152-agent32768/fabro uv run --frozen score-fabric storage exec -- python docs/handoff/someip-84/factory/run_host.py
```

Each invocation creates a fresh disposable root and a new `runs/` evidence directory.
The server and native CLI use isolated, owner-only credentials. The user's credentials
are not copied into the deterministic demonstrator. Fabro's native `wait` observes the
run for 120 seconds; its timeout at the configuration gate is retained. Server shutdown
after export preserves the blocked observation and storage; same-run resume is unproven
on this candidate and is not invoked.

## Retained execution history

| Run / attempt | What happened |
| --- | --- |
| `score-someip84-factory-hm743vf_` | Sandbox forbids listener startup (`Operation not permitted`); package validation passed, no run created. |
| `01M3VZ48HZGTB0JAFTZ6MP9H37` | Host starts Fabro and the real baseline command. Native CLI wait fails authentication, causing premature export/shutdown. Original export remains incomplete; late baseline files are labelled separately. |
| `01M3VZNAAQ1QXK5530X7E8HZ26` | Both command stages succeed after checking the expected 13/7 baseline and 13/0 external-candidate counts. Fabro blocks for human input; complete native export reproduces offline. |

Historical failures are retained. New output never overwrites earlier run evidence.

The [fresh export](runs/score-someip84-factory-zd4mjmhk/runtime-export.json)
preserves 63 events, three checkpoints, nine blobs, one unanswered question and zero
native human answers. [Offline verification](runs/score-someip84-factory-zd4mjmhk/offline-verification.json)
reports `reproduced: true`, `completeness: complete`, and no closure reason codes.
The fabric snapshot explicitly retains `QUESTION_SUBJECT_UNKNOWN`: this operational
configuration question has no authenticated 005 engineering subject. It is not an
engineering approval handoff. The gate label predates the user's later DeepSeek choice;
credential availability and native agent binding remain outstanding.

## DeepSeek selection and remaining work

The user's answer selects DeepSeek Flash and authorizes spending without a user cap.
[The separate selection record](deepseek-selection.yaml) preserves the captured native
catalogue offering and selects the current `deepseek-flash` API alias, high reasoning,
and no fallback provider.
Its finite technical ceiling comes from the existing compiler limits; it is not an
enforced live spending ledger. The existing draft profiles stay unchanged.

At the time of the measurement run, live implementation still needed a provider
credential, a native model binding, enforced tool/path boundaries and measured
runtime usage/admission. The live execution record below supersedes that status.
The existing 007 admission command is a pre-call diagnostic and always reports
`call_authorized: false`; changing a profile label cannot enable implementation.
DeepSeek calls and implementation attempts have now executed, but none is an
engineering decision.

Current [provider updates](https://api-docs.deepseek.com/updates/) identify the Flash
model as V4.1 and route legacy `deepseek-v4-flash` calls to it. The captured Fabro V4
offering is historical metadata. Provider [effort documentation](https://api-docs.deepseek.com/guides/thinking_mode/)
maps requested medium effort to high. A native authenticated tool smoke probe
passed. No old catalogue estimate is promoted to a current provider guarantee.

## Submitted DeepSeek implementation run

On 2026-10-01, an owner-only `DEEPSEEK_API_KEY` was found at
`/home/jefferson/.config/sesn/deepseek.env` and stored through stdin in a new,
isolated Fabro server vault. The key is absent from this repository and its
evidence. The isolated server runs at `127.0.0.1:43916`; the owner restored host
access later in this session and its process and authenticated endpoint were verified.

The [queue record](runs/score-someip84-factory-j3n0k9nl/queue-record.json)
captures run `01M3W4HERGBZ5SVR52BZ2NHQ9K` in native `submitted` state,
with no start record or model call. The workflow has a baseline command, a
DeepSeek Flash draft agent and an external review stop. Its target is a
manifest-verified disposable SOME/IP baseline. The compiler accepted its graph;
an explicit [operational overlay](runs/score-someip84-factory-j3n0k9nl/operational-overlay.json)
sets high reasoning and disables clone and managed branch pushes. Native
preflight passed. The server stores the submitted run under
`/tmp/score-someip84-factory-52ixww18/storage` and retains its owner-only auth
file in that disposable root.

That submitted local-provider run was never started and is superseded by the
Docker attempts below. A submitted run is not engineering acceptance. The reusable
preparation script is [prepare_implementation_queue.py](prepare_implementation_queue.py).

## Live DeepSeek attempts (2026-10-01)

The implementation graph is `start → agent → human review stop → exit`. A host
`pre_tool_use` hook restricts the agent to file reads and writes under the six
candidate paths. A host `sandbox_ready` hook disconnects the disposable Docker
container from all networks and provisions a manifest-verified baseline and
issue context into `/workspace`. Live canaries confirmed shell and subagent
calls are denied. The initial Docker attempt `01M3WD3X77REVPFZHY5ZN2A07T`
exposed that Fabro did not copy `--target-from` into the Docker workspace; the
agent made no changes. The provisioning hook corrected this.

Runs `01M3WDR8X6526VX69KGXEFZBQH` and
`01M3WEH3JSB1AWCEEF32Z7DJGR` had the source available, but their agent
stages failed when Pebble's 1,024-event queue filled during DeepSeek reasoning.
Their extracted workspaces showed no source changes. A disposable copy of the
pinned Petri runtime was changed only to set the agent event capacity to 32,768,
then Fabro was rebuilt in `/tmp`; no reference repository was modified.

Run `01M3WF6CGPT9DQBVV4Q6DN63XH` was started with that runtime and the same
Docker and tool hooks. The agent ultimately failed with native class
`llm:server` after repeated DeepSeek 900-second processing timeouts. The
unanswered review gate then expired, leaving the run in `failed` state.
No draft or human answer was produced. Direct authenticated checks returned
HTTP 200 for the model list, timed out for a minimal Flash generation request,
and returned HTTP 200 for a tiny Pro diagnostic request. The implementation
selection remains Flash with no fallback; the user explicitly rejected Pro
because of cost. All native run state remains under
`/tmp/score-someip84-factory-52ixww18/storage`.

Native Bazel/full runtime tests, exact native analyzer configuration, target CodeQL
eligibility/mapping, and required engineering reviews remain pending. The measurements
here use local GCC 12.3 rather than the native 12.2 pin and cover the focused registration
key regression. No MISRA compliance, full issue completion or engineering acceptance is claimed.

## Codex account alternative (2026-10-01)

The user selected their existing Codex ChatGPT account with `gpt-6.1-sol` and
medium reasoning as the alternative to Flash. The separate
[selection](codex-selection.yaml) preserves that authority and the successful
Codex CLI account smoke: API key variables removed, ChatGPT login forced, exit 0,
reply `OK`. This confirms account/model access; Fabro tool compatibility remains
unverified. [OpenAI authentication documentation](https://developers.openai.com/codex/auth)
distinguishes subscription login from platform API key billing.

The [catalogue overlay](codex-catalogue.toml) adds the exact model to the isolated
Fabro subscription provider. The preparation script supports `--selection codex`
and pins the native workflow to `openai-codex`, `gpt-6.1-sol`, medium, and an empty
fallback chain. It retains the same Docker isolation, six writable paths and
unanswered human review gate. The prepared package is in
`/tmp/score-someip84-factory-nz2flmbk`; its
[retained preparation evidence](runs/score-someip84-factory-nz2flmbk/queue-record.json)
records **prepared, not submitted**. Native validation passes.

**The account implementation is not running.** At that historical attempt, the session denied local
socket creation and Docker access. The Fabro MCP connector also refuses calls
because it requires approval while the current approval policy is `never`.
No account credential was imported and no new native run was created.

The [launcher](start_codex_queue.py) was prepared for a host session with normal
Fabro/Docker access. Its live path remains untested. It first checks the image,
prepared file hashes and baseline; then starts a separate isolated Fabro server,
imports only the existing account access token, requires a native model/tool
smoke and preflight, and invokes native `fabro run --detach`. It does not refresh
or change the original Codex login, answer review questions or select an API key.
Run from the repository root in a host terminal with that access:

```bash
uv run --frozen python docs/handoff/someip-84/factory/start_codex_queue.py /tmp/score-someip84-factory-nz2flmbk
```

It prints the new native run ID only after Fabro accepts the start. Evidence and
server metadata stay in that disposable root. A failed socket check stops before
credentials are read. If a submission times out, inspect preserved native state
before retrying; the launcher keeps the server and submission output available.

## Morning status: stalled; container stopped

Observed 2026-10-02T07:52:16.042312+01:00. Fabro retains a stale `running` state; its last event
was at **02:07 Lisbon** and the launch worker is no longer present. Native cancellation
returned HTTP 409 (`Run is not cancellable`). Only the exact owned container was stopped;
its workspace remains at `/tmp/score-someip84-factory-81ibm9qq/cutoff-workspace`. No native database status was rewritten.

Focused GCC tests, ASan/LSan/UBSan and Memcheck passed. Latest focused production coverage
was **77.8% line / 64.3% branch**. Full native builds/tests did not pass: LLVM extraction
hit `No space left on device`. TSan had a runtime mapping failure; Clang/native analyzer
configuration and other checks have unresolved failures. Raw CodeQL output includes
dependency findings and requires triage. Final review/report stages were not reached.
Engineering acceptance remains pending.

[Morning evidence](runs/score-someip84-factory-81ibm9qq/morning-status.json).

## Expanded overnight queue: startup history

At the owner's instruction, the original run `01M3WSTF1DAJA248NQ5QQGQG52`
was cancelled and its drafts, 18 identifier tests and reports were preserved.
The first expanded startup was cancelled before collection to correct the native
traceability output path. The current replacement is **`01M3WX09X84XFM5X08QY2944DF`**,
observed **running at 00:34 Lisbon on 2026-10-02**, with a **07:00 Lisbon cutoff**.
Its disposable root is `/tmp/score-someip84-factory-81ibm9qq`.

The [queue](overnight-queue.md) has 99 native nodes: 38 draft/repair tasks, four
conditional correction agents, 54 deterministic nodes, start, human gate and exit.
It covers the sourced process/platform obligations and additional checks: coverage,
MISRA applicability/analysis/manual review drafts, native builds and regressions,
analyzers, sanitizers, integration/AoU, performance, cross builds, security,
repository hygiene, traceability, tool assurance, inspection and review/report drafts.
See the [full obligation table and work items](runs/score-someip84-factory-81ibm9qq/QUEUE.md).

The workflow uses DeepSeek Flash with high reasoning and no fallback. No additional
spending/rework cap is imposed; the pinned runtime retains its native 500-visit
ceiling. Two repair agents revisit actual diagnostics and coverage. Changed source
is remeasured; reuse requires matching source and collector/executable/configuration
hashes and retains the original execution provenance. Remaining findings stop being
reworked when a round makes no source progress; they remain explicit blockers.

The old focused check incorrectly counted Fabro Git checkpoint metadata as engineering
source changes. That comparison is corrected; agents still cannot write Git metadata.
The preserved agent draft also has a genuine compiler error, supplied to the replacement
agents for correction. Infrastructure failures in the expanded queue are recorded while
remaining checks continue. Collection success never implies verification success.

The [preparation script](prepare_overnight_queue.py) uses the existing fabric compiler
and records its separate native runtime overlay. The [launcher](start_overnight_queue.py)
uses native create, binds the submitted ID before Docker startup, then invokes start.
Client preflight uses a seeded local environment; native create independently resolves
the server-managed Docker environment. [Live observation](runs/score-someip84-factory-81ibm9qq/live-observation.json)
confirms the exact owned container, pinned image and zero attached networks. Another
queue is outside that exact ownership filter and was not stopped or changed.

Native graph/overlay validation passes (99 nodes, 194 edges), ten collector contract
cases pass and Ruff passes. Actual production-filtered coverage and Memcheck component
executions worked on a separate preexisting external candidate, not the agent draft.
Installed portable tools and their hashes/versions are recorded. Full native collector
execution and deadline expiry have not yet been observed. Licensed QNX/Coverity access,
complete MISRA mapping/manual decisions, adopted dependency vulnerability scanning,
selected safety class/tailoring, tool qualification and required human acceptance stay
pending where unavailable. No external scans, publishing, merges or release occur.

Host hooks restrict stage writes and protect measurement feedback. They refuse a
new stage if its timeout and grace allowance cannot fit before cutoff. The queue
may finish drafting or block earlier; its final human gate remains unanswered.
[Verification and installation evidence](runs/score-someip84-factory-81ibm9qq/verification.json) is retained.

## Verification

The user subsequently reported that Flash is available again. A fresh Flash
package was prepared at `/tmp/score-someip84-factory-etyna3pp` with high reasoning
and no fallback; native graph and overlay validation pass. Its
[queue record](runs/score-someip84-factory-etyna3pp/queue-record.json) remains
**prepared, not submitted**. It was superseded by the overnight queue above;
the later native Flash tool smoke independently confirmed access. The previous native
Flash implementation run remains `failed` in the saved database; reporting
recovery does not restart it.

- Negative-first binding tests: six failures before implementation; after implementation,
  packaged content executes and exit 7 is preserved. A separately resealed IR binding
  substitution is refused after its recorded negative-first failure.
- Host handoff: three failures before correction, then three passes, including real native
  CLI auth-store parsing and preservation of incomplete phase output.
- Compiler/runtime regression: 258 passed. Native compiler integration: four passed.
- Combined new binding/handoff checks: 21 passed. Ruff, format, mypy, frozen sync,
  foundation and offline build records are under [evidence](evidence/).

Runtime observations are not trusted collector receipts or authenticated human decisions.
All authoritative source, patch, notices and native measurements remain understandable
without Fabro.

## Shared storage preference

Future preparation uses the [fabric-wide storage rule](../../../storage.md), preferring
a suitable mounted external SSD with internal fallback. Storage selection and its
implementation are frozen with each prepared root; existing run snapshots retain
their original paths. Private server state and credentials remain internal.
