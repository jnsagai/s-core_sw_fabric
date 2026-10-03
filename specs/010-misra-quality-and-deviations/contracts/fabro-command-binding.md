# Fabro command binding and SOME/IP execution correction

The user's 2026-10-01 continuation authorizes a bounded factory demonstrator for
SOME/IP issue 84. The previous patch and measurements were direct Codex work;
they remain separate inputs, never retroactively attributed to Fabro.

An execution action may add `command_file` to the existing version 1 mapping.
It is valid only for `command` or `deterministic_check`, names a canonical
relative POSIX path, and must occur in both the action's `support_files` and the
mapping's packaged support files. Empty or NUL-containing scripts are refused.
The IR retains the binding. Rendering embeds the selected, newline-normalized
support content as Fabro's native `script` attribute. It never interprets the
filename as a shell command or assumes support files exist in the target folder.
Native validation, closure hashes and the source map bind both copies of the
script. A changed or missing binding cannot silently fall back to `true`.

Historical mappings without this optional field retain their prototype rendering
for portable replay. Their unbound `script="true"` stages are not measured checks.
Every command in the SOME/IP demonstrator must have an explicit binding; this
continuation does not promote the historical prototype mappings to real checks.

Fabro owns actual command execution, stage exits, events and run state. Run only
in disposable source/build directories, with frozen source/tool/script identities
and bounded time/retries. Preserve native stdout/stderr and failures. A baseline
regression may deliberately fail; the measurement stage must check its expected
exit and test counts. Existing candidate validation is labelled external-candidate
validation, not agent implementation.

Live implementation requires explicit provider, permissions, data destinations,
positive spending budget and agent admission. Existing draft profiles disable
live calls with a zero budget. Missing admission stops before an agent stage.
Do not submit an engineering acceptance answer, mint collector receipts, enable
paid calls, or close human-owned review tasks. Runtime completion cannot establish
native process acceptance, MISRA compliance or issue completion.

Tests precede implementation: exact execution and nonzero exit preservation,
undeclared/unsafe/non-command/empty bindings, IR tampering and portable package
integrity. Actual native Fabro evidence is required separately from these tests.
