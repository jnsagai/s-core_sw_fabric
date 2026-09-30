# ADR 0013: Scoped readiness, portable evidence and upstream boundary

Date: 2026-09-27. Status: **Proposed; implement in 014–018; owner review pending**.

## Decision

Assess required scoped instances and explicit external obligations. Distinguish demo/component/feature/module/platform and experimental intent, technical readiness and accountable release authorization. Export native artifacts or immutable retrievable references, source locks, raw results, decisions, limitations and independently verifiable manifests.

## Source evidence

[score: docs/platform_management_plan/release_management.rst](https://github.com/eclipse-score/score/blob/e2373d822fc2f6e9a3f8a0538904f3faa39309ea/docs/platform_management_plan/release_management.rst); [module_template: docs/module/safety_mgt/module_safety_plan.rst](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/docs/module/safety_mgt/module_safety_plan.rst)

## Alternatives considered

Runtime success or component evidence cannot imply module/platform readiness. Publishing/deployment are separate decisions. A temporary CI link alone cannot serve durable evidence.

## Consequences

The portable verifier must work without contacting Fabro; schemas/readable reports cannot depend on runtime IDs for meaning. Required audits/qualification/confirmation remain blockers when absent. Later upstream proposal may expose a small adapter/APM package without X-Verse dependencies.

## Unresolved assumptions

No readiness, certification, release or deployment claimed. Retention/offline bundles, identity trust roots and maintainers adoption remain open before their increments.
