# ADR 0012: Baseline hashes, impact and invalidation

Date: 2026-09-27. Status: **Proposed; implement in 005/011/016; owner review pending**.

## Decision

Use a vector of repository commits plus content digests for artifacts, exports, schemas, tools, policies, mappings and workflow. Hash canonical subject manifests excluding self/approval fields. Propagate change along native dependencies plus explicit conservative rules for new interfaces/shared resources/AoUs. Preserve historical evidence; mark applicability stale in the new assessment.

## Source evidence

Brief §§10,16; [fabro-nightly: docs/public/execution/checkpoints.mdx](https://github.com/fabro-sh/fabro/blob/1b4fb15281ebb724426f9e480dce48d0100ff79b/docs/public/execution/checkpoints.mdx); [docs-as-code: src/extensions/score_metamodel/metamodel.yaml](https://github.com/eclipse-score/docs-as-code/blob/d5f3de608cdfc034952c57d40979c78d8cd35957/src/extensions/score_metamodel/metamodel.yaml)

## Alternatives considered

Filenames, runtime completion and old cached review flags are insufficient cache keys. Rewriting accepted history destroys provenance. Reusing stable metadata-branch assumptions against newer Petri storage is unsafe.

## Consequences

Before native Fabro resume, verify all subject and workflow inputs. Unknown dependencies widen review/block. Authorized no-impact decisions must bind old/new baselines and precise scope. No secondary run database.

## Unresolved assumptions

Canonicalization conformance and dependency completeness require later adversarial tests. Instance IDs stay stable across revisions; evidence identities do not.
