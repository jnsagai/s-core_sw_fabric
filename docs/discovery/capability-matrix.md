# Capability matrix

States: `supported` means demonstrated here at the stated level; `partially_supported`
means inspected implementation with remaining integration/coverage gaps; `unsupported`
means absent in the named baseline; `not_verified` means insufficient evidence.
None of these states is engineering acceptance.

| Capability / baseline | State | Evidence / limitation | Owner |
| --- | --- | --- | --- |
| Spec Kit 1.0.12 Codex skills, including converge | supported | Installed using official bundled init; version/integration manifests | 000 |
| Python package / offline diagnostic / quality checks | supported | 000 acceptance and local commands; hosted CI not run | 000 |
| Native needs export and metamodel | partially_supported | docs.bzl + expected real export shape inspected; no fresh native build | 001 |
| Native catalogue importer | unsupported | Planned only; no source importer written | 001 |
| Process2.1.2/docs8.2/template baseline | not_verified | Consumer declarations match; native build resolution untested | 001 |
| Work-product IDs and review instances | partially_supported | FMEA/DFA/FDR/release definitions inspected; catalogue closure not computed | 001–002 |
| Native status/link preservation | partially_supported | Metamodel constrains per type; no artifact editor yet | 001,004 |
| Fabro stable v0.254.0 DOT/TOML/validate/lifecycle | partially_supported | Native source inspected, executable absent | 003,006 |
| Stable immutable workflow registry | unsupported | No registry API/tool at stable pin | 003,006 |
| Nightly registry and Petri execution | partially_supported | Source SHA/API inspected, release compatibility unresolved | 003,006 |
| Human interviews | partially_supported | Upstream auto/default/replay supported; fabric trust enforcement absent | 005,006,016 |
| Authenticated scoped engineering approval | unsupported | Design proposal; no protected collector/approval channel | 005 |
| MCP setup/context/graph packages | partially_supported | Real manifests/tools inspected; no handshake/setup executed | 007 |
| MCP process compiler/metamodel-flow at selected SHA | unsupported | Absent from pinned packages; PR link points elsewhere | 001,007 |
| DeepSeek provider/model integration | not_verified | Newer docs candidate IDs, no installed catalogue or paid smoke call | 007 |
| Language/reliability support | not_verified | C++17/MISRA policy inspected; no safety classification/profile acceptance | 002,010 |
| Clang-Tidy/sanitizer policy and time CodeQL wrapper | partially_supported | Source/config inspected, exact override pending, analyzer not run | 010 |
| CodeQL CLI eligibility / report environment | not_verified | Query MIT is not CLI license; report Python3.9 not tested | 010 |
| Portable evidence, impact and scoped readiness | unsupported | Contracts/architecture proposed only | 005,011,014–017 |

The foundation has no target engineering readiness. Missing Fabro/Bazel/APM or license
capabilities cannot be treated as successful checks by future profiles.
