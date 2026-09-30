# ADR 0001: Workspace and authority boundaries

Date: 2026-09-27. Status: **Selected foundation boundary; owner review pending**.

## Decision

Keep this independent Apache-2.0 package; target-native documents remain in target repositories. References are immutable inputs. Spec Kit develops the fabric, S-CORE defines engineering semantics, Fabro owns execution, APM/MCP supplies context/tools. Agents draft; trusted tools measure; humans accept.

## Source evidence

Brief §§3–6 and existing LICENSE; [score: BUILD](https://github.com/eclipse-score/score/blob/e2373d822fc2f6e9a3f8a0538904f3faa39309ea/BUILD); [spec-kit: templates/commands/plan.md](https://github.com/github/spec-kit/blob/e77daa9021d20db26b878f7dfa5640fe5a42d04e/templates/commands/plan.md)

## Alternatives considered

Embedding the project in X-Verse would add unrelated dependencies. Replacing native artifacts with Spec Kit specs or a JSON requirements database would introduce a second authority.

## Consequences

Keep only a small Python CLI now. Build native docs in disposable copies. No scheduler/database/web service. Separate fixture and real evidence. Future upstream packaging remains a maintainer decision.

## Unresolved assumptions

Owner review of foundation remains pending; no upstream adoption claimed.
