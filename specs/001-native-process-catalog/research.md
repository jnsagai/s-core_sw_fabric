# Catalogue research

Decision: import native versioned exports plus metamodel rules, rather than scrape HTML
or infer directive instances with regex. Rationale and alternatives: ADR0002/0006 and
[native source review](../../docs/discovery/native-source-review.md).

Decided design constraints: sparse defaults are scoped by export version/schema; source
namespace differs from native ID; selected need version differs from export version;
qualified relation selectors are preserved; backlinks do not create scheduling edges;
rendered /main URLs and mounted docnames do not prove immutable source locations.

The implemented adapter supports the pinned docs-as-code v8.2.0 metamodel/schema
digests and the observed Sphinx-Needs 8.3.1 sparse envelope. The upstream nested
bundle expected export has version key empty string, one need, and defaults removed.
File reads are bounded to 64 MiB each. A genuine fixture preserves original export,
metamodel, schema and source RST bytes; its mount is explicit in the manifest.

A fresh minimal consumer built the pinned process export and passed docs_check.
Its export version is 0.1, with 1,251 needs; all imported source locations were
verified. The full module_template/score documentation bundle builds remain
unverified: their attempted disposable builds were interrupted for disk headroom,
with saved logs. No runtime/provider decision is necessary for 001.
