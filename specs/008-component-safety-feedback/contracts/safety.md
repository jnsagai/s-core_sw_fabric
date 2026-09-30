# Component safety contract (008)

**Status:** Proposed contract implemented for fixture demonstrations. Owner review of the safety
profile and FMEA/DFA roles is pending. No command writes native files, calls a model, or records
a human decision.

## Commands

```text
score-fabric safety check  --request <check.yaml>  --out <report.json> [--json]
score-fabric safety packet --request <packet.yaml> --out <packet.json> [--json]
score-fabric safety gate   --request <gate.yaml>   --out <gates.json>  [--json]
```

Exits: `0` complete report / requestable packet / design acceptance `accepted`; `1` published non-success
(`blocked` report, packet of a blocked report, no gate accepted); `2` malformed, unsafe or
unavailable input with a bounded diagnostic and prior output preserved.

## Requests

| Kind | Fields |
| --- | --- |
| `safety_check_request` | `profile`, `component`, `analysis` (`fmea|dfa`), `current` (`root`, `files[]` of `{path, sha256, role}`), `baseline` (same shape or `null`), `agent_checks[]` (007 `agent_output_check` refs), `platform_allocation` (native ID or `null`), `iteration`, `roles` (`null` or `{lock, fmea, dfa}` 007 lock and role profile refs), `protected_roots[]` |
| `safety_packet_request` | `profile`, `report`, `evidence[]` (`id`, `kind`, `ref`, `origin`, `requirement`), `protected_roots[]` |
| `safety_gate_request` | `profile`, `packet`, `decisions[]` (`assessment`, `trust_context` refs), `protected_roots[]` |

File roles: `requirements`, `architecture`, `analysis`, `allocation`. Paths are relative POSIX
paths under `root`; each file is SHA-256 bound.

## Reason codes

Coverage: `CATALOGUE_ID_UNCOVERED`, `APPLICABLE_WITHOUT_ITEM`, `EXCLUSION_WITHOUT_RATIONALE`,
`APPLICABILITY_UNKNOWN`, `UNKNOWN_CATALOGUE_ID`, `DUPLICATE_ROW`, `ALLOCATION_UNRESOLVED`.
Items: `MANDATORY_OPTION`, `OPTION_FORMAT`, `PLACEHOLDER`, `LINK_UNRESOLVED`, `LINK_TYPE`,
`CONTENT_MISSING`, `SUFFICIENT_WITHOUT_MITIGATION`, `VALID_WITHOUT_MITIGATION`,
`MITIGATION_ISSUE_FORMAT`, `DUPLICATE_NEED`. Mitigation: `MITIGATION_UNRESOLVED`.
Promotion: `UNTRUSTED_PROMOTION`, `PROMOTION_UNREVIEWED`. Re-analysis: `REANALYSIS_REQUIRED`,
`NEW_ELEMENT_UNANALYSED`. Loop: `ESCALATE_TO_HUMAN`, flag `AOU_TRANSFER_REVIEW`. Roles:
`ROLE_NOT_SEPARATE`, `ROLE_SCOPE_OVERLAP`, `ROLE_SCOPE_EXCEEDS_ANALYSIS`. Gates:
`DESIGN_PREREQUISITES_BLOCKED`, `DECISION_MISSING`, `DECISION_SUBJECT_MISMATCH`,
`DECISION_NOT_REPRODUCED`, `PRODUCTION_AUTHORITY_UNAVAILABLE`, `DESIGN_NOT_ACCEPTED`,
`MITIGATION_EVIDENCE_MISSING`.

## Guarantees

- Only directives outside literal blocks count; template examples in `code-block` are ignored.
- `sufficient: yes`/`status: valid` never become reviewed without a verified decision; agent
  promotions are refused even with a decision request pending.
- Decisions count only when `verify_assessment` reproduces a 005 assessment, its gate ID matches,
  its outcome is `pass`, its domain is not `production` (005 T009 open), and every packet file
  `(path, sha256)` appears in the assessment subject file closure.
- Checklist answers are always `pending_human`; structural support never answers adequacy.
