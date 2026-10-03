# SOME/IP #84 overnight work queue

Status: **prepared, not submitted**. Cutoff: **2026-10-02T07:00:00+01:00**.

20 draft tasks, four measured check stages, four conditional correction stages, then an unanswered human review gate.

Rework has no added queue cap. The pinned runtime has a hard ceiling of 500 visits per loop node.

Each measured check compares the agent-authored tests against the untouched baseline and drafted source. Original outputs are retained; two check stages enable UBSan. Full native Bazel/runtime checks remain pending.

## Work order

1. `scope`
2. `callsites`
3. `invariants`
4. `reproducer`
5. `key_fix`
6. `unit_matrix`
7. `check_unit_matrix`
8. `runtime_disabled`
9. `runtime_enabled`
10. `lifetime_tests`
11. `check_lifetime_tests`
12. `ordering_tests`
13. `conversion_tests`
14. `check_conversion_tests`
15. `compatibility`
16. `lifetime_review`
17. `concurrency_review`
18. `api_review`
19. `test_metadata`
20. `bazel_plan`
21. `analyzer_plan`
22. `evidence_inventory`
23. `review_packet`
24. `check_review_packet`

## Correction routes

- `check_unit_matrix` findings → `repair_unit_matrix` → `check_unit_matrix`. Infrastructure failures stop for human review.
- `check_lifetime_tests` findings → `repair_lifetime_tests` → `check_lifetime_tests`. Infrastructure failures stop for human review.
- `check_conversion_tests` findings → `repair_conversion_tests` → `check_conversion_tests`. Infrastructure failures stop for human review.
- `check_review_packet` findings → `repair_review_packet` → `check_review_packet`. Infrastructure failures stop for human review.

## Startup

The host launcher smoke-tests Flash, checks native preflight, creates a submitted Fabro run, saves its native run ID, then starts it. It selects only that run’s container and does not stop other queues.

```bash
uv run --frozen python docs/handoff/someip-84/factory/start_overnight_queue.py /tmp/score-someip84-factory-_etjbuqw
```

The current session denies local socket/Docker access; Fabro MCP requires approval while approval policy is never. No model recovery probe, native admission or live deadline/concurrency validation has executed.

## Local verification

- Native compiler and operational overlay validation pass.
- 18 component checks pass, including actual GCC/GTest: baseline 7 failures; known external candidate 13 passes. Docker transport was stubbed; this is not an agent draft or live run.
- Three container-ownership component cases pass; foreign and duplicate-owned containers cause no mutation. Live Docker behavior is unverified.
- Ruff passes. Engineering acceptance and human reviews remain pending.
