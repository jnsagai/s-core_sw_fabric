# Verification and operation

Run `uv run --frozen pytest -q tests/contract/test_runtime_supervision.py`.
Run `uv run --frozen python docs/handoff/someip-84/factory/supervise_overnight.py ROOT`
to attach supervision to one existing bound run. Future queue launches require it
automatically. Inspect the printed private policy, heartbeat and user service.
Use `systemctl --user status UNIT` for process liveness. A ready receipt alone is
insufficient: the PID/start time, fresh heartbeat, run ID and policy hash must match.
Account repair drills use an isolated disposable workspace; they never fail a live
engineering run or imply real native restart/engineering acceptance.
