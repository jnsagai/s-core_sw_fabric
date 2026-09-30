# ADR 0011: Providers, budgets and unattended operation

Date: 2026-09-27. Status: **Proposed; implement in 007/016; owner review pending**.

## Decision

Configure exact per-role provider/model/reasoning/output/context/time limits, bounded correction visits and concurrency, with data-destination allowlists. Prefer DeepSeek for routine engineering and deliberate Codex supervision/review. All live calls disabled in the foundation. Fabro progresses and emits events; terminal handoff is non-LLM/event-driven.

## Source evidence

[fabro-nightly: docs/public/integrations/deepseek.mdx](https://github.com/fabro-sh/fabro/blob/1b4fb15281ebb724426f9e480dce48d0100ff79b/docs/public/integrations/deepseek.mdx); [fabro-nightly: lib/components/fabro-llm/src/catalog.rs](https://github.com/fabro-sh/fabro/blob/1b4fb15281ebb724426f9e480dce48d0100ff79b/lib/components/fabro-llm/src/catalog.rs)

## Alternatives considered

Hardcoded marketing aliases, subscription/API credential mixing, automatic expensive fallback and continuous Codex polling violate reproducibility or budget boundaries.

## Consequences

Validate installed catalogue and provider capability before opt-in bounded smoke calls. Missing usage is unknown, never zero; enforce conservative pre-call ceilings and document in-flight overshoot. Human gates remain stopping conditions.

## Unresolved assumptions

Model IDs and rates are documentation candidates only until runtime/provider probe. No live profile, credentials or budget approved here.
