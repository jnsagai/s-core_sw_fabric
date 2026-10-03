# Authorized projection comparison — 2026-10-03

The owner's subsequent `go` approved ten additional Flash requests capped at $0.10.
This experiment uses a fresh private native server, external volume-bound workspace and
request ledger. The original experiment and its exhausted ledger remain unchanged.
[summary.json](summary.json) retains results and [authorization.json](authorization.json)
identifies the bounded instruction pins and source-derived price bounds.

| Development rendering proxy | Baseline uncached input | Optimized uncached input | Reduction |
| --- | ---: | ---: | ---: |
| B1 metadata | 3,237 | 1,081 | 66.60% |
| B2 C++ draft | 3,238 | 1,090 | 66.34% |
| B3 unit-test draft | 3,230 | 1,088 | 66.32% |
| B4 interface draft | 3,245 | 1,088 | 66.47% |
| B5 architecture draft | 3,250 | 1,091 | 66.43% |

These are the exact original supplied prompts and expected JSON outputs. Both variants
select no tools, matching the fixture instruction “Use no tools.” The transport removes
23 unselected declarations while preserving every native message and all other fields.
The baseline's unrelated fixture material remains unchanged. Each native agent stage,
exact output, request hashes and native/provider token totals are checked before the next
request. All ten outputs match; fixture IDs, checks, evidence refs and pending review remain
equal. Cache hits are zero, so uncached and total-input reductions agree. Output/reasoning
remain separately observed; no runtime or semantic-quality improvement is claimed.

All replies identify `deepseek-flash`. Provider usage reports 455 reasoning tokens and
native output plus reasoning reconciles to completion tokens. Conservative peak prices
freshly checked in the [official documentation](https://api-docs.deepseek.com/quick_start/pricing/)
give an observed cost upper bound of **$0.008103**, with **$0.047131** total maximum
reservations against the $0.10 cap. Actual billed cost stays null; native catalogue costs
remain stale estimates. The meter stops at ten requests; native and transport servers stop.

The 60–80% target is met for controlled JSON rendering fixtures. They are not real S-CORE
requirements/code changes, test execution or safety engineering. Real engineering performance
and human acceptance remain unmeasured/pending T032/T033. Default live policy stays disabled.

[storage-selection.json](storage-selection.json) binds targets, captures and per-command
caches to the measured external Linux build volume. Private credentials/server SQLite and
the pinned runtime's co-located native scratch remain internal. No global configuration,
running queue, reference repository or historical evidence is modified.

[operator-scripts/](operator-scripts/) contains exact executed Python source snapshots as
`.py.txt` evidence, including the finite comparison driver. They embed disposable paths;
do not replay them against global or existing servers. Non-secret operator inputs and native
workflow/API/event/stage records retain the native activation bindings. Credentials and the
private transport nonce are excluded. These bindings do not isolate hostile same-account
processes. [manifest.json](manifest.json) pins all retained evidence bytes.
