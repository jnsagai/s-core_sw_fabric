# Independent quality compliance assessment (version 1)

`quality assess --request REQUEST --out ASSESSMENT [--json]` invokes no analyzer or signer.
It independently replays a portable quality packet before evaluating the declared scope.

The exact `quality_assessment_request` fields are `profile`, `packet`, `current_baseline`,
`decisions`, `assurance_domain`, `as_of`, `protected_roots`, plus version/kind. Profile and
packet are transport references. Current baseline is a transport reference to an existing
sealed quality_import_baseline, or null for an explicitly offline assessment. When selected,
its actual source files are frozen now and compared with the packet's current coverage or
analysis baseline. No current host state is inferred from archived path labels. Null leaves
BASELINE_FRESHNESS_UNKNOWN. Time is caller-selected RFC 3339 with timezone and remains untrusted.
Domains are fixture_contract and production.

Decisions are at most 20 distinct {assessment, trust_context} transport-ref pairs selecting
005 originals. Each is independently replayed, then its entire gate is reevaluated at as_of.
A supporting decision has exact packet binding only when the verified 005 file closure and
original source bytes include the canonical entire packet bytes. Matching names, headers,
unrelated gate passes and caller assertions do not suffice. Supporting decisions never
adopt guideline policy or discharge manual obligations automatically. Packet disposition
bridge decisions are also reevaluated at this assessment's as_of and requested domain,
retaining original results separately from current observations. At most 20 signed decision
records across selected support and disposition histories, 96 MiB combined selected records.

The sealed quality_compliance_assessment retains the request, selected profile, full portable
packet and its independent replay, nullable current frozen baseline and original source byte
closure, all supporting 005 selections/current gates, disposition observations, explicit
obligation results and gaps. Each declared guideline has a result, including missing mappings,
excluded, manual, audit, unsupported and unknown states. Unknown denominator remains null.
Complementary structural observations can be pass/fail/blocked/not_evaluated without
constituting accepted guideline or overall compliance claims. No denominator, mapping,
category or manual review is inferred from native report wording or a query support count.

Overall outcome is pass/fail/blocked/not_evaluated; missing required engineering prerequisites
have precedence over positive tool observations. The current supported profile is unmapped,
CodeQL primary execution/eligibility remains unavailable and protected 005 production authority
is unavailable. Thus no current production or fixture quality compliance pass is possible.
A fixture disposition acceptance is still visible as accepted_fixture and cannot clear the
matrix or make a production finding resolved. Historical corrections remain local unprotected
observations; an assessment cannot rerun or authenticate them. Production evidence is never
upgraded from local/imported/fixture origins. Every assessment has accepted_claims 0,
assurance eligibility not_eligible and engineering readiness not_evaluated.

Controls are 1 MiB, packets/selected derived records/final output 96 MiB with existing depth/node
limits. Source files retain the existing 500-file/64-MiB bound. Source/current transport and all
005 inputs are refrozen after replay; output cannot overwrite any selected or historical input,
current source, packet notice or protected root. Offline archive path labels are protected
against output replacement but never opened to resolve claims. A malformed or unreproduced
packet refuses (exit 2) with previous output preserved; a published blocked/fail/not_evaluated
assessment exits 1. Exit 0 is reserved for a future independently supported pass and is
unreachable with the current unmapped profile. No paid call, automatic approval or native
status change occurs.
