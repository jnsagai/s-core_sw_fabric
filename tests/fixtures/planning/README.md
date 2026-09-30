# Planning acceptance scenarios

These Apache-2.0 fixtures are synthetic and have no engineering authority. They describe the
minimum acceptance journeys exercised by the generated test inputs in
`tests/planning_support.py`. No fixture exposes an approval or trusted-authority switch.

| Scenario | Expected result |
| --- | --- |
| New component | Exact expected instances remain when inventory entries are absent; complete absence requests create. |
| Reused component | Logical identity remains stable; reuse stays effectively unresolved with authority findings. |
| Security feature | Unknown/security interaction candidates remain visible and source conflicts block the draft. |
| Multi-scope review | Every native/scope pair has coverage and review purposes produce distinct identities. |
| Invalid input | Malformed, unselected, or unsafe inputs return exit 2 and preserve a prior plan. |
