# Synthetic extraction fixture

The request/baseline/manifest, tiny C++ source and Markdown reports are labelled fixtures.
No query, extractor or reporting script created these reports. The report shape was checked
against pinned Coding Standards reporting source; `Compliant` and `approved-by: agent`
are intentional inputs proving that raw labels cannot authenticate decisions or readiness.
The expected unit set is separate from observed processing/extraction and native file listing.

The baseline and extraction JSON have canonical self-digests. Request selections also bind
their actual file-byte hashes. Host paths are explicit workstation examples; rebind selections
on another machine. See the [exact import contract](../../../../specs/010-misra-quality-and-deviations/contracts/native-import.md).
