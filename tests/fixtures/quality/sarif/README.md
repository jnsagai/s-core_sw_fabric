# Synthetic SARIF fixture

The adjacent SARIF and [extraction fixture](../extraction/README.md) are agent-authored
test data, not CodeQL execution, S-CORE artifacts, licensed query output or human decisions.
`fixture/check`, `fixture-pack`, `fixture-suite` and repeated-digit binary/pack/suite hashes
are explicitly synthetic identifiers. No MISRA rule text or native process ID is invented.

The importer uses a bounded subset of
[SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html).
Dynamic tests add multiple runs, duplicates, indexed artifacts/rules/logical locations,
code flows, stacks, fixes, fingerprints and native suppressions to this minimal format.
The native output remains raw fixture data with no production eligibility.
