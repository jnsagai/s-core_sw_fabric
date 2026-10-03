# ASan host and complete selected validation

2026-10-01. The user ran the prepared validation in the normal terminal. These are local
unprotected measurements, not engineering acceptance or protected collector attestations.
The agent sandbox's LeakSanitizer thread-attachment failure remains independently reproducible.

## Native ASan evidence

[Original host capability/defect/correction records](sanitizer-environment.md#latest-normal-terminal-checkpoint-2026-10-01)
retain the same selected GCC/runtime/configuration/native templates and suppression bytes.
Capability and clean corrected runtime exit 0; seeded runtime exits 55 with one native
`heap-buffer-overflow` finding. Fresh source digests differ, expected/processed scope is adequate
and original/disposable source integrity is unchanged. No runtime flag or suppression was weakened.

[Targeted host integration](evidence/asan-host-20261001/integration.log) passes **3 tests,
2.61 seconds**: defect/fresh correction, immutable correction/stale history and original-output
import. All three native measurements, seals, captures, phase exits and selected configuration
identities independently verify; imported and executed evidence retain their original authority.

The first host attempt stopped at Ruff on helper/test files being completed. The
[original Ruff failure](evidence/asan-host-20261001/ruff.log) remains exact. Formatting/import
issues are corrected. Six negative cases failed before retained-record verification was
strengthened; the final record/resume tests pass. The combined
[focused checkpoint](evidence/asan-host-contracts.txt) passes **29 tests, 1.90 seconds**.

## Complete selected repository validation

The user resumed with:

```bash
cd /home/jefferson/s-core_sw_fabric
bash scripts/validate_asan_host.sh --resume /tmp/score-quality-asan-host.BVZPU8t8
```

The script verifies the original ASan measurements and three passing integration cases, then
uses a fresh evidence directory. Original failed output is preserved. Exact commands and frozen
native environment selections are in [the script](../../scripts/validate_asan_host.sh).

[All phase statuses](evidence/host-full-validation-20261001/status.txt) are exit 0:

| Gate | Measured result |
| --- | --- |
| `uv sync --frozen` | 18 packages checked |
| Original ASan records and targeted JUnit verification | Pass; native bytes/status/configuration/fresh scope retained |
| `uv run --frozen ruff check .` | Pass |
| `uv run --frozen ruff format --check .` | Pass |
| `uv run --frozen mypy src scripts/verify_asan_host_records.py` | 116 source files, no issues |
| `uv run --frozen python scripts/check_foundation.py` | 64 unchanged FAB requirements, 19 dependency rows, skills/locks/local links pass |
| Full selected pytest command | **1,773 passed, 13 skipped, 361.00 seconds**, zero failures/errors |
| `uv build --offline` | Source distribution and wheel built |

[Regression stdout](evidence/host-full-validation-20261001/regression.log) and original
[JUnit](evidence/host-full-validation-20261001/regression.xml) independently agree: 1,786 tests,
1,773 passes, 13 skips, zero failures/errors. All source logs are retained byte-for-byte.
The full command's three native Fabro compiler tests are explicitly excluded because their
runtime is not selected. These exclusions and skips do not establish native readiness.

The thirteen skipped checks are: one MCP server selection, one native artifact round-trip,
one fresh native catalogue export, two separately measured public CodeQL demonstrations,
six native Fabro runtime cases, one native safety profile and one native verification profile.
Their required external selectors are unconfigured; none is relabelled as passed. The genuine
[CodeQL public native gate](codeql-public-demonstration-acceptance.md) separately passes both
software demonstrations. Eligible target CodeQL execution remains unimplemented and blocked.

The full JUnit also confirms real Clang-Tidy defect/correction and each Cppcheck/ASan/UBSan
seed/fresh-fix case passed. This completes original T008's four-tool source/integration scope.
T030 and T081 are complete for their exact validation/recording scope. Current count is
**88 tasks, 77 complete, 11 open**; source/tool qualification, target CodeQL, mapping/manual
coverage, engineering authority and human-owned T032/T082 remain open. No test or clean native
result accepts engineering decisions. No increment 011, publishing, merge, release or deployment.
