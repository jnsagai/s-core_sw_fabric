# Legacy CodeQL disposition packet fixture

`legacy-disposition-packet.json` retains the original synthetic public CLI checkpoint before
library metadata capture and embedded historical-control replay were added. Its packet digest is
`0525467a1d3b620b0c7957be39c191d61d5294ef63f007187484c2de4f523040`.

The finding, query source, CLI and library metadata are synthetic; the CLI never executes.
CodeQL inspection and all required human questions remain unavailable/pending. Zero accepted
claims and not_eligible/readiness not_evaluated are unchanged. Temporary paths are labels only;
offline replay must not read or probe them. No proprietary guideline/query implementation text
or production approval is included. Preserve original bytes for compatibility verification.
