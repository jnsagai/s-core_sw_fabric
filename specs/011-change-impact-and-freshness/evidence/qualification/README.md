# Scoped native qualification — 2026-10-03

Owner instructions: `go`, then `deepseek flash only`. The initial experiment is closed
at ten Flash requests; no extra provider request was made for the tool projection.
No engineering acceptance, constitution ratification or production origin is recorded.

[summary.json](summary.json) records the real provider observations, separate native
usage and catalogue estimates, paired outcomes and exact native run IDs.
[manifest.json](manifest.json) pins all retained evidence bytes.

| Development proxy | Baseline uncached input | Optimized uncached input | Reduction |
|---|---:|---:|---:|
| B1 metadata draft rendering | 7,051 | 4,894 | 30.59% |
| B2 C++ draft rendering | 7,045 | 4,899 | 30.46% |
| B3 unit-test draft rendering | 7,053 | 4,893 | 30.63% |
| B4 interface draft rendering | 7,046 | 4,894 | 30.54% |
| B5 architecture draft rendering | 7,054 | 4,903 | 30.49% |

All ten JSON outputs match their supplied development fixture expectations. These
are controlled rendering proxies, not real requirements, code changes, unit-test
execution or safety engineering. Required fixture IDs/check lists/evidence refs
and pending review stay equal. The 60–80% real routine target is not established.

All replies identify `deepseek-flash`; the pinned native catalogue resolves the
legacy `deepseek-v4-flash` alias. The [official pricing documentation](https://api-docs.deepseek.com/quick_start/pricing/)
confirms that this alias serves V4.1 Flash. Conservative peak bounds use $0.30 per
million input tokens and $1.20 per million completion tokens, including reasoning.
The ten observed requests have a combined **$0.019258 upper bound**, versus a
$0.10 ceiling and $0.085729 pre-request maximum reservation. Actual billing is null.
Cache hit tokens are zero. Provider usage explicitly reports 227 reasoning tokens;
native `output + reasoning` reconciles to provider completion totals. Original meter
records omitted that optional field; reconciliation reads raw provider usage without
rewriting [meter-final.json](meter-final.json). The implementation now retains it.
Fabro's catalogue cost uses stale rates and must not be treated as an invoice.

The real negative run `01M41AVDMJ83JMKCAGR8HYMAQD` reached the agent stage and
failed with `LIVE_CALL_NOT_AUTHORIZED`, with zero native/provider tokens. Native
hooks report `run_id=petri`; exact private host cwd binds the API run ID. Tool
events omit cwd, so the CLI also checks its actual process cwd. The successful
local-fixture tool run `01M41BJ5XGHEBQ039TFW8D6NAS` invokes the real bounded
stdio MCP service over a >1 MiB SARIF and returns 379 bytes; native generic
`read_file` is blocked with `BOUNDED_TOOL_REQUIRED`. Its provider is a local
fixture, with synthetic usage and zero paid calls. Fixture transport never proves
real provider readiness. Earlier failed binding probes remain identifiable in
the separate disposable native database and retained events.

The native input contains 23 tool declarations. Guarded execution permits only
registered bounded tools, leaving 13 irrelevant generic declarations in the
initial provider payload. An optional operator-pinned selection now removes
already-denied/unselected declarations while retaining every message and selected
schema. [tool-projection-replay.json](tool-projection-replay.json) replays the ten
real native inputs with zero provider calls. The optimized B5 request falls from
17,954 bytes to 10,905 with all bounded tools, 5,752 with the summary tool, or
5,092 with no tools. Byte replay does not establish new live token savings.
The guard also refuses unselected bounded tools and foreign agent stages.

Disposable targets, analysis, captured requests/responses and per-command caches
use the measured external Linux build volume in [storage-selection.json](storage-selection.json).
The registered Linux image sits on the mounted external SSD; no disk was reformatted.
Credentials, SQLite/native server state and its internally co-located scratch remain
under the separate mode-0700 internal `private_server_root`. The pinned runtime
co-locates host scratch there; no private state or existing queue was migrated.
Both guard and transport stop on loss of the bound external workspace.

Only the selected DeepSeek credential was transferred in memory from a read-only
secret query into the disposable server via its source-checked native secret API.
No key, dev token, session secret, private SQLite file or nonce-bearing server
configuration is copied into these evidence files. Run titles were explicit,
fallbacks empty and automatic human approval disabled. Private files and checksums
are operator inputs, not isolation against hostile same-account Unix processes.

[operator-scripts/](operator-scripts/) contains exact non-secret script snapshots
used for measurement. They embed this disposable workspace's paths and are retained
for provenance; do not replay them against an existing/global server. The server
and transport are stopped after collection. Source reference repositories remain clean.

The final transport also narrows the experimental ceilings to the exact pinned governor's
per-task input/output/call limits, accounting for every serialized transmitted byte and
reserved output across repeat requests. The original experiment enforced its 24 KB outer
input ceiling; it did not independently compare that serialized input with the S0 20,000
token conservative limit. Observed provider input remained below that limit in all cases.
This pre-transmission accounting gap is now fixed and covered by rejection tests; the
historical experiment is not retroactively declared a proof of the new implementation.
