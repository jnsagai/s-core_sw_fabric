# Exact command evidence

`tool-invocations.jsonl` records exact functions.exec tool inputs, including shell command
strings, inline scripts and read-only source research, extracted from this session and
the two planning research agents. Only tool calls/results are exported, not user messages
or private reasoning. Result metadata/short output excerpts are retained; repeated source
file dumps are abbreviated. Some shell groups ended with exit0 despite an earlier failing
command; consult the visible error excerpts and corrected final checks, never infer all
subcommands passed from the final group's exit alone.

`verification.txt` separately retains exact argv, complete output and individual exit
status for the final checks. `references.json` records actual source hash/status results.
The command extraction snapshot predates its own completion; its final invocation is
`python3 /tmp/s-core-foundation/record_commands.py` (exit0). Later final verification
commands are independently retained in verification.txt. Authoring helpers in /tmp are
session-local; their exact creation content is retained in the tool invocation inputs.

Principal executed setup commands:

```bash
UV_TOOL_DIR=/tmp/s-core-foundation/tools UV_TOOL_BIN_DIR=/tmp/s-core-foundation/bin uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.0.12
git switch -c 000-bootstrap-and-discovery
/tmp/s-core-foundation/bin/specify init --here --force --non-interactive --integration codex --integration-options='--skills' --script sh
PATH=/tmp/s-core-foundation/bin:$PATH .specify/scripts/bash/resolve-template.sh constitution-template --json
PATH=/tmp/s-core-foundation/bin:$PATH SPECIFY_FEATURE_DIRECTORY="$PWD/specs/000-bootstrap-and-discovery" .specify/scripts/bash/setup-plan.sh --json
PATH=/tmp/s-core-foundation/bin:$PATH SPECIFY_FEATURE_DIRECTORY="$PWD/specs/001-native-process-catalog" .specify/scripts/bash/setup-plan.sh --json
uv sync
uv run --frozen python /tmp/s-core-foundation/finalize_evidence.py
```

All final setup steps succeeded; initial failures and fixes are documented in acceptance.md.
Public reference clones used `git clone --depth 1 [--branch PIN] URL /tmp/s-core-foundation/references/NAME`;
exact repository-specific argv and results are in the transcript. PR API reads paginated
all issue comments, review comments, submitted reviews, files and commits, without writes.

No native export, Fabro generation/validation/run, MCP setup, CodeQL analysis or model
call command was executed. Such future commands in design documents are labeled proposals.
No commit, upstream publication, merge, release or deployment occurred.
