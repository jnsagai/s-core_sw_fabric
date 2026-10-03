# Increment 010: CodeQL prerequisite inspection

The autonomous 010 work reached a [blocked handoff](010-to-011.md) at 04:32 UTC.
The user subsequently [resumed work](010-resumed-approval.md). Separate authorized synthetic
software demonstrations now run real CodeQL extraction/query phases; the public commands
described here retain their inspection-only contract. [New measurements](../../specs/010-misra-quality-and-deviations/codeql-native-demonstration-acceptance.md)
retain seeded/fresh-corrected results, installation failure and remaining reporting gaps.
[Contract](../../specs/010-misra-quality-and-deviations/contracts/codeql-prerequisites.md),
[implementation evidence](../../specs/010-misra-quality-and-deviations/codeql-prerequisites-acceptance.md).

Both quality capability/run commands now accept `--adapter codeql`. They inspect explicit local
source, pack, library, configuration and supporting eligibility selections. They execute only
bounded Git inspections, with native roots/indexes protected and selected bytes refrozen.
Neither command runs the CodeQL CLI or a reporting interpreter. Every result stays unavailable,
not eligible, with zero accepted claims and unknown extraction for the blocked run.

The real installed source/pack inspection finds 233 matching MISRA source files and 13 matching
embedded library identities. Different source/build commit IDs resolve to the same Git tree.
Compiled provenance, library source reconciliation, runtime closure, eligible use and native
reporting/configuration acceptance remain gaps. Native audit/default-disabled exclusions stay visible.

The profile and reporting interface remain proposed. Supporting `eligible` text, fixture decisions
or a declared Python 3.9 interpreter cannot authorize query execution. Full-increment CodeQL
execution/integration tasks T011/T012 remain open; these inspections do not satisfy them.

The earlier eligibility question received no project-use record; the later continuation and
installation permission are recorded separately. T032, 009 T018 and 005 T009 remain human/external gates. Next work
is the remaining task/spec/plan audit, deterministic implementation gaps within 010 and final
handoff. No 011 implementation is authorized.
