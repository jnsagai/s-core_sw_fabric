# Increment 006 runtime fixture sources

Runtime contract tests use the sealed
`tests/fixtures/compiler/linear/out/package.json` as the 003 workflow source and the
fixture-domain records under `tests/fixtures/assurance/` as 005 assurance sources. Keep those
files at their original paths and verify their exact bytes; do not copy a fixture receipt into
a production request or treat Fabro events as signed assurance evidence.

The 003 package declares `workflow.toml` as its entrypoint. Fabro's inspected version wire
form expects the graph entrypoint `workflow.fabro`. The 006 projection must retain both
identities and the complete native file map. No live run output is checked into this folder.
