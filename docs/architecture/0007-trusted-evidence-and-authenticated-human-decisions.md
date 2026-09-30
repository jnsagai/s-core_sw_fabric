# ADR 0007: Trusted evidence and authenticated human decisions

Date: 2026-09-27. Status: **Proposed; enforce in 005; owner review pending**.

## Decision

Separate agent-writable draft workspaces from protected deterministic runners/collectors and approval identity. Bind decision to a canonical subject manifest hash excluding the approval record; record actor/role/authority/independence/policy/scope/rationale/conditions/time/authentication. Hash equality proves integrity, not origin.

## Source evidence

Brief §§14,16; [fabro-stable: lib/crates/fabro-interview/src/replay.rs](https://github.com/fabro-sh/fabro/blob/497aaba6f20c1fac052346c39f52e08fabadb179/lib/crates/fabro-interview/src/replay.rs); [fabro-nightly: docs/public/human-tools/interviews.mdx](https://github.com/fabro-sh/fabro/blob/1b4fb15281ebb724426f9e480dce48d0100ff79b/docs/public/human-tools/interviews.mdx)

## Alternatives considered

Prompt prohibitions, CODEOWNERS, signed-looking YAML or Fabro actor strings alone do not authenticate acceptance. Replay can retain old actor metadata; native run approve is operational authorization.

## Consequences

Recompute subjects at use. Deny agent access to approval tools/credentials and trusted result writes through OS/CI credentials, isolated processes and repository protection. Reject auto/replay/success-defaults at compile and submission. Target code/test subprocesses must run without collector or approval credentials; an isolated collector attests observed outputs after execution. A human interview alone never satisfies gate.

## Unresolved assumptions

Identity provider, protected runner topology and role assignment remain unresolved before real approval support. Local single-user demonstrations have limited assurance and cannot claim protected acceptance.
