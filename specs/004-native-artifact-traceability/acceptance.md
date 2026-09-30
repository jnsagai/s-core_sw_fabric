# Increment 004 acceptance record

**Date**: 2026-09-28  
**Scope**: Deterministic native indexing, isolated candidates, expected-set trace coverage,
semantic diff, direct drift, and conservative impact for fixture-reviewed profiles.

## Results

| Check | Result |
| --- | --- |
| Artifact contract/integration suite without native environment | PASS - 85 passed, 1 intentionally environment-gated |
| Locked real-native index/create/update journey | PASS - 1 passed, 3 fixture cases deselected, 68.46 s |
| Full pytest with pinned Fabro and real-native environment | PASS - 209 passed, 1 pre-existing native-export-manifest skip, 91.99 s |
| Ruff check and format | PASS - 203 files formatted |
| strict mypy | PASS - 43 source files |
| foundation checker | PASS - 64 requirements, 19 dependency rows |
| offline wheel and source distribution | PASS |
| public index/create/update/validate/trace/diff/drift commands | PASS with documented 0/1 exits |
| exact-max/one-over limit matrix | PASS |
| one-mutation-per-category diff/impact/drift journeys | PASS - 17 focused cases |
| locked module-template `needs_json` | PASS - 365 packages, 31,010 configured targets, 81 actions, 355.251 s |
| locked module-template `docs_check` | PASS - 47 module sources plus mounted inputs, 0 schema warnings |

The only full-suite skip was
`tests/integration/test_native_export.py`, which requires a separate
`SCORE_NATIVE_EXPORT_MANIFEST` for Increment 001. The Increment 004 real-native test was enabled
with `SCORE_BAZEL_BIN` and `SCORE_NATIVE_MODULE_ROOT` and did not skip.

## Native identities and evidence

- Module template commit:
  `c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d`.
- Process description commit:
  `98d1d5f42dad412a09a888ea25e59c62fa6371ce`.
- Fabro commit:
  `1b4fb15281ebb724426f9e480dce48d0100ff79b`.
- Bazel 8.7.0 executable SHA-256:
  `d7606e679b78067c811096fb3d6cf135225b528835ca396e3a4dddf957859544`.
- Module `MODULE.bazel.lock` SHA-256:
  `2c3fb185150806e30ccd9d4e8ef6f8e1797f647f6c642308a5fcf07a708596ce`.
- Artifact profile semantic/transport SHA-256:
  `01384aaad3bcb3b5f43eb0c5fd72e8ed334271eae52b4da1596c9b8160964dba` /
  `7cac85a69d47ef5ca34bb3e420c47c76d1be2bc7327279a57328318e026f1cf8`.
- Native-build profile semantic/transport SHA-256:
  `0afcefd3d9c60089c94e2bb41ba4f0a71c475fb65ef46f04e47d0574e5b6247c` /
  `34c8065d27ddfe744e269b42a0d011928ec7d2e4437fb3cde2ecb444141079f3`.
- Trace profile semantic/transport SHA-256:
  `f7fe4eec7439e99d5dbc9c6ddfd01166fcb9409a39a8edef7534a222b58c137f` /
  `9f41d55e1803c0d342e5c400c8287ffcd4c9366565ec5fe17301fcdaeec96936`.
- Baseline fresh `needs.json` SHA-256:
  `db78f1d7f94387364766eb1cdfc52c30b18e7f9f4b073fbaba0259d6a94ac9ed`.
- Six-edit candidate fresh `needs.json` SHA-256:
  `dad4d6a9d5855cc6facaa069a1f1310ed7457da25258f19870e9bc21b18bc993`.

The baseline real index reconciled 62/62 records from 47 RST files: 33 document wrappers,
29 child needs, 82 typed relations, and zero findings. Representative feature, component, and
analysis sets contained 8, 14, and 9 live entities. Literal example directives remained opaque.
The candidate performed one create and one scoped update for each of feature, component, and
analysis. It produced 36 wrappers, six overlay files, a fresh matching export, and an identical
candidate/index native receipt. Hashes of every source RST file were unchanged after both journeys.

Native stdout/stderr was captured without a shell, cumulatively capped at 8 MiB, and hashed in the
receipt. The logs recorded zero metamodel schema warnings after the candidate templates supplied
the required version, safety, security, and work-product relation fields. Disposable HOME/cache
paths were excluded from receipts. The successful reusable Bazel cache occupied 14 GiB; a cold run
therefore requires at least 15 GiB free. Generated fixture packages peaked at 18,378 bytes.
The offline distributions were:

- wheel: 99,803 bytes,
  `516150ee6d69bd2139988ea06e2100203bb561c88e771bc6da65c7950f97f962`;
- sdist immediately before recording this evidence: 724,298 bytes,
  `2cc77b5a5e27857235ced34cd1e43b4589c97f733ff3954bf7a8176ed4ff629c`.

## Requirement evidence

- FAB-016: source-qualified identities, exact RST spans, native type/status/relation validation,
  hash-bound templates, preimage-bound scoped edits, fresh native receipts, deterministic candidate
  overlays, semantic diff, and direct drift.
- FAB-017: plan/package-derived expected obligations, explicit output classifications, fixed
  denominators, typed verification paths, blocked missing-obligation reports, and conservative,
  cycle-safe impact.
- FAB-018: independent wrapper and contained-need records and validation; a valid wrapper cannot
  mask an invalid child.

AC004-01-16 and SC004-01-08 are covered by the contract, integration, public-command, relocation,
limit, mutation-category, and locked-native runs above. The public missing-verification trace
returned exit 1 with both expected verification obligations retained in the denominator and
`TRACE_UNRESOLVED` findings. The semantic diff returned exit 1; clean drift returned exit 0.

## Limits and boundaries

Version 1 enforces inclusive maxima of 64 MiB per control input, emitted package, and declared
target; 10,000 files; 2 MiB per managed text file; 100,000 native entities; 100,000 expected
obligations; 500,000 relations; 10,000 edits; 20,000 findings; 8 MiB cumulative native output; and
1,800 seconds per native command. The tests pass every exact maximum and reject every maximum plus
one through the same production enforcement primitive used at each consumption point. Oversize
control input is rejected before parsing, cumulative native output is tested with an exact 8 MiB
payload and one byte over, and representative one-over candidate failures preserve prior output.
The suite does not allocate all maxima concurrently; concurrency and aggregate host-resource
capacity remain deployment concerns rather than format acceptance claims.

Checked-in artifact/build/trace profiles remain pending production owner review. Their reviewed
override authorizes fixtures only, including the real Bazel compatibility journey. No result
authenticates evidence or approval, changes engineering readiness, mutates a production target,
or registers/executes a workflow. All six later capability fields remain `not_evaluated`.
