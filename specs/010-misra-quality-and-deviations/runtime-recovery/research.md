# Research

Local Codex 0.159.3 exec supports --ignore-user-config, --ephemeral, --json,
--output-schema, workspace-write sandbox and stdin prompts. Local login status
confirms ChatGPT. Official references: https://developers.openai.com/codex/noninteractive
and https://developers.openai.com/codex/config-reference (forced_login_method).
No platform API key is required or selected. Exact model remains gpt-6.1-sol/medium.

Actual Fabro endpoints are /api/v1/runs/{id}, /state and /cancel. Native running
worker titles are `fabro {first-12-ID-characters} running`; process executable and
start time must match. Stale running state alone is not proof of a live worker.
Existing current run 01M3XZAQ65TTE35XSGXC4JAMAH has no external repair supervisor.
The user systemd manager is available (degraded globally); unit availability and
ready receipt must be measured independently.

Earlier Docker extraction failed on read-only runtime Git objects. FUSE retries
failed with read-only/transport errors. The same retained image now has a verified
kernel mount. These faults must reach host recovery, beyond the six source paths.
