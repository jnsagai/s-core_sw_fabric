# Host addendum to the authorized all-obligations scope

This is task context, not engineering acceptance or an approved tailoring decision.
Use the already pinned .llm_tmp/context/obligations/source-index.json.

The verification_process.rst metadata lists fault injection, interface, requirements
and resource tests, and requirements/design/boundary/equivalence/fuzzy/error-guessing/
explorative derivation techniques. Review source-supported applicability and actual
coverage of these techniques. In particular, security_review, traceability_review,
integration_aou_review and verification_report_draft must distinguish configured
module tests from any absent fuzz/fault-injection harness or full feature/platform
reference-hardware tests. Unknown applicability and unexecuted applicable checks
remain explicit pending work. Do not label identifier-only tests as full platform
validation or claim a fuzzy technique was executed without an actual measurement.

Concrete missing boundary/equivalence regression cases can be implemented within the
six source paths by the existing coverage/tests repair stages. Native source IDs must
be verified; there is no authority to invent links, select safety classification,
accept risk/deviations or answer the independent human gate.
