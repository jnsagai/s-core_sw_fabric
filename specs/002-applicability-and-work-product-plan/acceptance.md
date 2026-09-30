# 002 acceptance record

Date: 2026-09-27

Increment 002 implements an offline, deterministic draft work-product planner over a selected
sealed 001 catalogue. This record is fabric-development evidence. It is not target engineering
acceptance, profile approval, or resolution of the native security-FDR conflict.

## Delivered behavior

- Strict version-1 catalogue, intake, profile, mapping, inventory, decision-reference, and plan
  boundaries with duplicate-key, digest, identity, relation, size, and path checks.
- Complete native-work-product × declared-scope coverage accounting, stable structured instance
  identities, explicit purposes, shared-parent deduplication, and finite dependency closure.
- Conservative unknown handling that retains candidate instances and separates coverage state,
  applicability, requested disposition, and effective disposition.
- Exact inventory matching with complete/partial absence semantics; Q/QR/NQ reuse route checks;
  stale revision, modified-reuse, tailoring-impact, separate-decision, external-owner, and
  unavailable-authority findings.
- Canonical sealed plans and protected atomic output. CLI exits are 0 complete draft, 1 blocked
  draft written, and 2 invalid input/output with prior output preserved.
- A review-draft profile and explicit 74-rule policy pinned to catalogue digest
  `a69436e36d00e4950d46eb933488d5d71b806554da96902ca8ff6373c04727f3`.

## Acceptance coverage

| Acceptance cases | Evidence |
| --- | --- |
| AC002-01–04 | Exact new-component set, multiple FDR purposes, two-component shared-module deduplication, deletion resistance, partial inventory, external ownership, dependency cycles, and missing context tests |
| AC002-05–08 | Unknown predicate candidate retention, unsupported profile facts, mapping gaps, all-74 security-feature coverage, preserved audit statement, and explicit security-FDR conflict |
| AC002-09–12 | Q/QR/NQ routes, modified reuse, exact accepted-revision matching, separate classification/change-request refs, stale reuse, tailoring permission/impact/authority, and cross-scope identity tests |
| AC002-13–14 | Relocation/order determinism, semantic digest sensitivity, deterministic closure limits, stable logical identities, selected catalogue baseline, and multiple-revision ambiguity |
| AC002-15–16 | Duplicate keys, 64 MiB bound, corrupt/resealed catalogue, invalid endpoints, cycles, unsafe/symlink/hardlink paths, prior-output preservation, forged local trust flags, and invariant draft/not-evaluated claims |

The contract and integration tests contain independent assertions; they do not snapshot planner
output as their oracle. The full source-backed case accounts for all 74 selected native work
products and confirms the real conflict and audit rationale remain visible.

## Validation outcome

The final validation run must remain reproducible with the frozen environment:

- `ruff check .`: pass.
- `ruff format --check .`: pass.
- strict `mypy`: pass.
- full `pytest -q`: 76 passed, 1 optional 001 live-export test skipped.
- planning-focused tests: pass, including the available full 74-work-product catalogue.
- `scripts/check_foundation.py`: pass after acceptance/handoff links are present.
- `uv build --offline`: wheel and source distribution built successfully.
- Public complete-draft CLI example: exit 0, 12 instances, zero findings,
  plan semantic digest `d283dba7bb49e5e4e012f132c1757fff8259d3c09ed06d899db9e3bfb8e0a58a`; canonical file SHA-256 `ffa4f4e42e84d70e4e19a72c372d96d773c973014079dfd273fec8352651e80f`.

Artifact hashes are recorded after the final rebuild:

| Artifact | SHA-256 |
| --- | --- |
| Review-draft profile | `0f8a833dd5d4fe7051c86d860067e68da311df2b02bd30267b776890a0ae83eb` |
| Applicability policy | `7d3101983f7b6ae5ab41c589aebc404434d395b071ad61badf33a7bbc98e4106` |
| Source distribution | `acacc3989673cba238131934e6ba520ca93653907dad452daa79d9b371284461` |
| Wheel | `ba6288b871c24c4aa4276cc59644f3101334e8cc35ede523b88ff00cbaca7c38` |

## Open owner decisions

- Review and approve or revise the conservative 74-rule project mapping. Coverage accounting does
  not establish correct target applicability.
- Resolve the upstream `wp__fdr_reports_security` versus module-template
  `wp__fdr_reports` conflict.
- Supply protected decision verification in increment 005 before any reuse/tailoring proposal can
  become effective.
- Complete the existing 000/001/002 human review checklists. Automated implementation did not mark
  human-owned review items complete.
