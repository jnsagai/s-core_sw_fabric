# Increment 009 data model

Version-1 records reject unknown or missing fields, bound strings, arrays and bytes, carry a
canonical `digest`, and state `engineering_readiness: not_evaluated`.

## Verification profile (`verification_profile`, YAML)

`id`, `status`, `sources[]` (`id`, `repository`, `commit`, `path`, `sha256`), `test_types[]`,
`derivation_techniques[]`, `rules[]` (`id`, `check`, `source`), `source_tags[]`,
`requirement_directives[]`, `design` (`work_product`, `sections[]`, `diagram_directives[]`),
`inspection_checklist[]` (`id`, `criterion`, `source`), `loop.max_attempts`,
`pending_obligations[]` (`id`, `description`, `owner`).

## Toolchain profile (`cpp_toolchain_profile`, YAML)

`id`, `status`, `compiler` (`path`, `sha256`, `version`), `test_library` (`name`, `version`,
`include`, `header_sha256`, `libraries[]` of `{path, sha256}`), `coverage_tool` (`path`, `sha256`,
`version`), `standard`, `policy` (`source`, `selected_levels[]`, `unavailable_levels[]`,
`flags[]`, `unsupported_flags[]`), `link_flags[]`.

## Detailed design report (`detailed_design_report`)

Component, file digests, design (`document_id`, `work_product`, `sections`, `diagram`),
`units[]` (`path`, `sha256`, `tags[]` of `{id, line}`), `requirements[]` (`id`, `type`,
`implemented_by[]`), `findings[]`, `outcome` (`complete|blocked`).

## Unit verification run (`unit_verification_run`)

`baseline` (`sources`, `tests`, `requirements`, `toolchain`, `flags`, `source_digest`,
`full_digest`), `build` (`steps[]` with argv, exit code, bounded stdout/stderr and digests;
`outcome`), `execution` (exit code, timeout, bounded output, `xml_sha256`), `tests[]` (`suite`,
`name`, `result` = `passed|failed|skipped`, `result_text`, `test_type`, `derivation_technique`,
`fully_verifies[]`, `partially_verifies[]`, `description`), `metadata_findings[]`,
`requirements[]` (`state` = `verified|partially_verified|failing|unverified`), `coverage`
(`status` = `imported|not_requested|unavailable`, per-unit line/branch counts), `origin:
local_unprotected_execution`, `assurance_eligibility: not_eligible`, `outcome`
(`passed|failed|blocked`), `findings[]`.

## Milestone report (`verification_milestone_report`)

`current` run summary, `history[]`, `failures[]` with retained output digests and `routes`,
`nondeterminism[]`, `attempts`, `requirement_matrix[]`, `mitigation_candidates[]` (from 008
reports), `inspection_packet` (units, design reference, checklist with `answer: pending_human`),
`pending_obligations[]`, `outcome` (`verified_on_baseline|failures_open|blocked`).
