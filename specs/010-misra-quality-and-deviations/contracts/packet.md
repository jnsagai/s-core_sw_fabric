# Portable quality review packet (version 1)

`quality packet --request REQUEST --out PACKET [--json]` executes no analyzer.
It retains selected evidence and review questions; emitting a packet is not acceptance.

The exact `quality_packet_request` fields are `profile`, `coverage`, `analyses`,
`dispositions`, `source_snapshots`, `notices`, `protected_roots`, plus version/kind.
Transport references are exact `{path, sha256}` objects.

- `coverage`: nullable `{request, report}` selecting a reproduced coverage matrix.
- `analyses`: at most 20 distinct `{request, report}` native import selections, including
  prior runs. Coverage-selected analyses are included automatically. Each import reproduces
  from original bytes without execution; stale and inadequate analyses remain in the packet.
- `dispositions`: at most 1000 distinct `{request, review, decision}` selections. `decision`
  is null or `{request, result}` selecting the existing quality decision bridge. Current
  run requests are read only. Correction actions are never reexecuted by packet creation.
  Every linked review ancestor, original report, draft, compensating reference and selected
  decision reference is retained. A decision result must reproduce through the existing
  bridge; selected 005 assessment/context originals remain portable.
- `source_snapshots`: at most 500 `{baseline_digest, root}` selections. The digest is a
  baseline's `full_digest`, including policy/tool identity. An explicitly selected directory
  supplies the exact source file bytes for a historical or current baseline. Every baseline
  encountered in analyses, local original runs, disposition/history/fresh runs and decision
  bindings needs a snapshot. Missing snapshots produce an incomplete packet; mismatched
  supplied bytes refuse publication. Unselected snapshots refuse. A historical source path
  cannot be inferred from a local analysis baseline. Snapshot roots are protected.
- `notices`: at most 64 `{id, license, notice, ref, applies_to}` selections retaining original notice or
  license bytes. Missing notices remain a named closure gap. Supplied text is provenance,
  never license eligibility, qualification or policy adoption. `applies_to` explicitly lists
  `native:<profile-source-id>` and `tool:<adapter-id>` associations. Every selected native
  source and analyzer needs notice closure; unassociated declarations remain gaps.

The sealed `quality_review_packet` contains the unchanged request, its original absolute
path label, loaded profile, coverage, analyses, dispositions with complete history,
source snapshots, notices, an original-byte file archive, gaps, origins, and review questions.
Every question has `answer: pending_human`; this command accepts no answered questionnaire.
`packet_state: complete|incomplete` describes portable closure only. `outcome: emitted|incomplete`;
`accepted_claims: 0`, origin `local_unprotected_evaluation`, assurance eligibility `not_eligible`,
engineering readiness `not_evaluated`. Original local/import/fixture origins remain distinct.

Archive paths are provenance labels. An offline verifier must never open, execute or write them.
It checks strict fields, byte hashes, selected transport references, source closure, native raw
output closure and linked history against embedded originals. Retained observations and seals
do not authenticate historical execution or human authority. Truncated raw bytes retain their
prefix and full-stream digest and keep the packet incomplete; absent bytes are never invented.
Tool/library executables are identities only and are not redistributed in the packet.

Controls are at most 1 MiB, individual archive/source files 16 MiB, archive retained bytes
64 MiB, archive files 5000, selected derived records and final packet 96 MiB, depth 64 and
200000 nodes. Review history is at most 1000 revisions and 96 MiB per selected chain, with
the final packet aggregate bound also enforced. Controls, references and selected source
bytes are refrozen before atomic publication. Output cannot overwrite any selected input,
historical source, protected root or notice. Exit 0 emits structurally complete closure with
human/authority/compliance gaps still visible; 1 publishes incomplete closure; 2 refuses an
invalid or unsafe selection and preserves an existing output.
