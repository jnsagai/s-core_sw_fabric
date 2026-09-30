# Increment 007 evidence: Fabro model catalogue capture

Raw, unmodified response bodies captured on 2026-09-30 from a disposable server running the
pinned Fabro candidate `1b4fb15281ebb724426f9e480dce48d0100ff79b` (executable SHA-256
`09d338fbbe107d6c2e41fe9f3b33531c72b54782a2e17dac7c720b89898a68cf`) on `127.0.0.1`, with
dev-token authentication only and no provider credentials in its environment.

| File | Request | SHA-256 |
| --- | --- | --- |
| `fabro-catalogue/models-offset-0.json` | `GET /api/v1/models?page[limit]=100&page[offset]=0` | `d5fd82e4b8f000c0a0b3f477e6d67fa252e3cb23c40277f3fd120680e2b9ce86` |
| `fabro-catalogue/models-offset-100.json` | `GET /api/v1/models?page[limit]=100&page[offset]=100` | `5409cc1f898f32f989bac306bae423f608f31347fcbf451e721b6f9464756bae` |
| `fabro-catalogue/providers.json` | `GET /api/v1/providers` | `66025cdab3ec1332a94706cda107cc3385cd939137583b111c1591ab9c1d7223` |

These are runtime observations of a candidate, not a selected runtime or provider approval. No
model test or prompt was sent. Every row reports `configured: false`. See the
[007 acceptance record](../../../specs/007-apm-agent-context-and-profiles/acceptance.md).
