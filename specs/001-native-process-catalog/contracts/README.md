# Minimum contract proposals

Status: source/catalogue v1 has an executable adapter, contract tests, and a
fresh pinned minimal-consumer process export. Full score/module_template
documentation bundles remain unverified. Forward contracts remain design
proposals and are not existing upstream APIs.

- [Catalogue/source contracts](catalogue.md): bounded implementation target for 001.
- [Forward boundary contracts](forward-boundaries.md): instance identity (002), evidence
  and typed gates (005), impact/readiness consumers (011–017); no implementation in 001.

Each serialized contract will have an explicit schema version and reject unknown
normative fields/enums. Raw native metadata remains in a dedicated lossless field;
new schema versions require migration/compatibility review. No fake acceptance samples.
