<!--
*******************************************************************************
Copyright (c) 2026 Contributors to the Eclipse Foundation

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This program and the accompanying materials are made available under the
terms of the Apache License Version 2.0 which is available at
https://www.apache.org/licenses/LICENSE-2.0

SPDX-License-Identifier: Apache-2.0
*******************************************************************************
-->

# SOME/IP issue #84 — bounded duplicate-server registration-key slice

**Document type:** review draft (scope only)
**Date:** 2026-10-01
**Repository:** `eclipse-score/inc_someip_gateway`
**Slice:** duplicate-server registration-key handling within *Revise version handling in socom*
**Status:** local, unprotected, scoped analysis. Full native runtime tests and human
review remain pending. Nothing in this document is a published or accepted engineering
artifact.

> **Write constraint observed.** This is the only file written for this task. No source,
> build, test, config, or notice file was modified. Content is derived solely from
> `read_file`, `grep`, and `glob` over the working tree and `.llm_tmp/context/`.

---

## 1. Binding issue #84 to the verified baseline

### 1.1 Issue of record

| Field | Value |
|-------|-------|
| Issue | `eclipse-score/inc_someip_gateway#84` |
| Title | *Revise version handling in socom* |
| State | open |
| Author | `NEOatNHNG` |
| Created | 2026-04-14T13:23:24Z |
| Updated | 2026-04-14T13:23:24Z |
| Comments | 0 |
| Source | `.llm_tmp/context/issue-snapshot.json` |

Issue body (verbatim intent): the reporter distinguishes three identity use cases —
service-instance identifier = `service id + major + minor + instance id`; service identifier
= `service id + major`; FindService request = `service id + major + optional<minor> +
optional<instance>` — and proposes that `service_interface` be designed to serve those cases,
"exclude the minor version and make it a property of the service instance to be able to better
compare and index compatible service instances." The FindService `major = FF` AUTOSAR case is
called out as theoretically possible but not useful.

### 1.2 Verified baseline

| Item | Value |
|------|-------|
| Baseline commit | `f8a196c3b16d5172d898394ab99b0ed81346d63d` |
| Recorded in | `.llm_tmp/context/source-manifest.json` (line 3) |
| Working branch | `fabro/run/01M3WSTF1DAJA248NQ5QQGQG52` |
| HEAD commit | `a282596` — `fabro(01M3WSTF1DAJA248NQ5QQGQG52): start (success)` |

Baseline blobs of the in-scope files were cross-checked between
`.llm_tmp/context/candidate-files.json` and the matching `sha` entries in
`.llm_tmp/context/source-manifest.json`; they agree, which binds the slice to the baseline
above rather than to the working HEAD.

### 1.3 In-scope candidate files

| File (repo-relative) | Baseline git blob | Baseline present | Candidate sha256 (working tree) |
|----------------------|-------------------|------------------|---------------------------------|
| `score/socom/impl/service_identifier.hpp` | `c8bae7908da9f087c518934f7b9f8d86db9a20ec` | yes | `96b33a1fee4d54577ae9bc46c313409a0d59336f76df85ef1925ffebdd1a2119` |
| `score/socom/impl/service_identifier.cpp` | `6c7e7a4e22355242009fe20dada2a9a0d0c7a9c7` | yes | `d766902e4bda5306095a6e5326ea91d28df3a6e1ef4e77dc9ba47556ed559a9a` |
| `score/socom/BUILD` | `3477ea0851fdcd82ec6ea9d71424013cbdf41962` | yes | `dee826163ac5e6336d51a293136b424696c2884aa1b2592395e1e06423c0ba44` |
| `score/socom/test/unit/BUILD` | `3c03a7b14286051f97fa5022206564bd63645171` | yes | `9b3c5b341211e2c387858fd1fe5c669a6a422b6e8b5e80fce35ba22c61186799` |
| `score/socom/test/unit/runtime_tests.cpp` | `8ecf5ab726db8bf994c960045d6fd7fdf84d7395` | yes | `5e35e24d0abcfa361b5a5283a005b307b86026a970464a3423be7c6eed66631e` |
| `score/socom/test/unit/service_identifier_tests.cpp` | *(none)* | **no** | `45d073998108df76c8f4534508d65f02cead28aa568cd5c45b5a3d8a4fd36a25` |

The explicit `null` baseline blob for `service_identifier_tests.cpp` is evidence that this
slice expects a **new** unit-test file; it is absent from the baseline manifest. `glob` for
`**/service_identifier*` confirms only the two `impl/` files exist on disk today.

### 1.4 Prior reports and host feedback

`glob` over `.llm_tmp/overnight/reports/*` and `.llm_tmp/overnight/validation/*` returned no
files. There are **no earlier overnight reports and no host validation feedback** in this
workspace to reconcile against. This document therefore records the first scope draft and
marks the following as un-confirmed: any previously "accepted" wording, any prior measurement
numbers, and any earlier reviewer guidance.

---

## 2. As-is behaviour of the duplicate-server registration key

Facts read from the working tree at the baseline:

- **Key type.** `Service_instance_identifier` is
  `{ Service_interface_identifier interface; Service_instance instance; }`
  (`score/socom/impl/service_identifier.hpp:26-29`) with a declared `operator<`
  (`:32`). Its definition orders by `std::tie(lhs.instance, lhs.interface) <
  std::tie(rhs.instance, rhs.interface)` (`service_identifier.cpp:20-22`).
- **What it keys.** The type is used *only* as the duplicate-server registration key:
  `using Service_identifiers = Mutexed_variable<std::set<Service_instance_identifier>>`
  (`runtime_impl.hpp:56`), held as `Runtime_impl::m_service_identifiers` (`:228-229`).
- **Insertion / duplicate rejection.** `Runtime_impl::make_server_connector` builds
  `Service_instance_identifier{configuration.get_interface(), instance}`
  (`runtime_impl.cpp:443`) and returns `Construction_error::duplicate_service` if
  `insert(...).second` is false (`:449-454`). The key is erased by a `Final_action` on
  connector destruction (`:456-463`).
- **What the key contains.** `Service_interface_identifier` = `{ id, Version{ major, minor } }`
  (`service_interface_identifier.hpp:74-124`); equality/ordering compare `(id, version)` with
  version = `(major, minor)` (`:130-162`). Because `std::set` uniqueness is
  `!(a<b) && !(b<a)`, **minor version is part of the duplicate-server key today.**
- **Conflicting index semantics.** `Service_database` deliberately indexes service records by
  `id + major` and **ignores minor** via `Minor_version_ignoring_hash` /
  `Minor_version_ignoring_key_equal` (`runtime_impl.hpp:116-134`), and `get_record` uses that
  map (`runtime_impl.cpp:313-324`).
- **Enable path.** Enabling a server calls `Runtime_impl::register_connector`
  (`server_connector_impl.cpp:72`), which resolves the record via the minor-ignoring lookup
  (`runtime_impl.cpp:526-531`) and calls `Service_record::register_server_connector`, whose
  contract is `SCORE_LANGUAGE_FUTURECPP_ASSERT(!m_server)` (`runtime_impl.cpp:366-371`).
- **Compatibility rule.** `is_interface_compatible` requires equal `id` and equal `major`, with
  `client.minor <= server.minor` (`runtime_impl.cpp:133-146`).
- **Documented contract.** `Runtime::make_server_connector` says duplicate if "a service defined
  by the `configuration.interface` and instance parameters is already registered"
  (`runtime.hpp:170-191`); the error comment is merely "Service identifier already exists"
  (`error.hpp:55`).
- **Existing tests.** `runtime_tests.cpp:317-363` covers duplicate detection with the *same*
  interface/version (default factory config): `ConstructDuplicateReturnsDuplicateServiceError`,
  `ConstructDuplicateMultipleTimesReturnsDuplicateServiceError`,
  `CreatingServerConnectorDeletingItAndRecreatingReturnsValidServerConnector`. No test varies
  only the minor version. `service_interface_identifier_tests.cpp` covers the identifier
  constructors and `Service_instance` constructors but not the `Service_instance_identifier`
  ordering/identity.

### 2.1 Static mismatch surfaced by the slice (unverified at runtime)

The duplicate key includes `minor`, while the record index ignores it. Consequently two server
connectors for the same `id + major + instance` with **different minor versions**:

1. produce distinct `Service_instance_identifier` keys, so both pass the `duplicate_service`
   check in `make_server_connector`; but
2. resolve to the **same** `Service_record` (minor-ignoring lookup) on enable, so the second
   `register_server_connector` violates `ASSERT(!m_server)` — undefined behaviour in release
   builds (silent `m_server.emplace` overwrite).

This is a static reading of the code, not a measured runtime result. It is the concrete defect
the bounded slice should decide on and, if accepted, pin with a test. Whether it is reachable
depends on the minor-version question in §4.

---

## 3. Accepted draft scope (bounded)

Scope is deliberately limited to the **duplicate-server registration key** and its tests. It
does **not** attempt the full version-model revision described in #84.

In scope for this slice:

1. **Key semantics for duplicate server connectors.** Decide and implement whether the
   `Service_instance_identifier` used by `Runtime_impl::m_service_identifiers` should keep
   `minor` in the key or ignore it (aligning with `Service_database`'s minor-ignoring index and
   the #84 "service identifier = id + major" use case). Touch
   `impl/service_identifier.hpp` / `.cpp` only as far as that decision requires.
2. **Ordering/identity contract.** Make `operator<` (and, if introduced, any companion
   equality/equivalence) express the chosen key unambiguously, keeping the existing
   `std::set` usage correct.
3. **New unit tests** in `score/socom/test/unit/service_identifier_tests.cpp` (new file, no
   baseline blob) covering: ordering by instance then interface; same id/major/instance with
   differing minor treated per the chosen policy; distinct instance; distinct id; distinct
   major.
4. **Runtime-level duplicate tests** extended in `score/socom/test/unit/runtime_tests.cpp` to
   cover same `id + major + instance` with differing minor versions, asserting
   `Construction_error::duplicate_service` (or the chosen alternative) — only if the decision
   in §4 makes that observable at construction.
5. **Build wiring** `score/socom/BUILD` and `score/socom/test/unit/BUILD` only if the new file
   needs it (the unit test target already globs `*.cpp`).
6. **Notice preservation** — Apache-2.0 headers on every touched file, including the new test
   file and this report; no `NOTICE`/`LICENSE` changes.

Explicitly **out of scope** for this bounded slice (deferred to the wider #84 discussion):

- Reshaping the public `Service_interface_identifier` type or moving `minor` onto
  `Service_instance` (the reporter's longer-term proposal).
- FindService wildcard (`major = FF`) handling and the SD/wire mapping.
- The `Service_database` minor-ignoring index and client/server minor-compatibility algorithm
  beyond what the key decision forces.
- `score/config` minor wildcard (`0xFFFFFFFF`) semantics.

**Acceptance caveat.** No earlier acceptance record exists locally (§1.4). The scope above is
the draft accepted *for this local iteration only*; it is not an engineering acceptance and
must be confirmed by human review before implementation proceeds.

---

## 4. Open design questions

These must be resolved before the scope in §3 can be implemented.

1. **Minor in the duplicate key, or not?** If the key ignores `minor` (consistent with
   `Service_database` and #84), two servers with the same `id + major + instance` but different
   minor collide at `make_server_connector` → `duplicate_service`. If the key keeps `minor`,
   the `Service_database` index must stop ignoring minor (or `register_server_connector` must
   tolerate replacement) to remove the assert/UB path in §2.1. Which is authoritative?
2. **Two servers, one `id + major + instance`, different minor.** Should this be rejected as a
   duplicate, should the later minor replace/supersede the earlier one, or should both be
   allowed with some negotiation? Today the code cannot express the last option.
3. **Is the assert path reachable and intended?** Is `SCORE_LANGUAGE_FUTURECPP_ASSERT(!m_server)`
   a genuine invariant, meaning duplicate detection *must* cover every collision the record
   index can produce — i.e. the two keys must use the same equivalence?
4. **Scope of the `#84` restructure.** Do we now introduce `Service_identifier = id + major`
   plus minor-as-instance-property (large API change), or keep
   `Service_interface_identifier{major,minor}` and only fix the key? This report assumes the
   latter for the bounded slice; confirm.
5. **Version field widths and wildcard.** socom uses `uint16 major` / `uint16 minor`
   (`service_interface_identifier.hpp:80-88`), while the SOME/IP config uses `uint8 major` /
   `uint32 minor = 0xFFFFFFFF` wildcard (`score/config/mw_someip_config.fbs:18-23`). How is the
   wildcard mapped into socom's key/compatibility logic, and does it interact with duplicate
   detection?
6. **Ordering vs. identity.** `operator<`'s `(instance, interface)` order is only used for
   `std::set` membership. Is a total order actually meaningful, or should the internal key be
   an equality/hash key (with `operator<` retained for other users, if any) to make intent
   explicit?
7. **Public vs. internal placement.** `impl/service_identifier.hpp` is compiled into the
   `//score/socom:socom` library via the `impl/**` glob, not the public `*.hpp` headers glob.
   Confirm the key stays internal and that changing its ordering is not an ABI/API concern.
8. **Error semantics.** Should a minor-only collision report `duplicate_service` (the current
   enum) or a more specific error? `error.hpp:55`'s comment ("Service identifier already
   exists") is already narrower than the actual key.
9. **Test expectations for `service_identifier_tests.cpp`.** Confirm the intended coverage and
   that a new test file is preferred over extending
   `service_interface_identifier_tests.cpp`, given the candidate manifest treats it as new.

---

## 5. Measurement and validation status

- **Measurements:** none performed. `shell` was intentionally unavailable to this task
  ("Overnight tool/path boundary"), and the task restricted tools to `read_file`, `grep`,
  `glob`, `write_file`. No build, no `bazel test`, no runtime execution.
- **Scope of claims:** all observations are static readings of baseline source plus the
  context snapshots. The §2.1 assert/UB path is a hypothesis, not a reproduced result.
- **Local / unprotected / scoped:** this draft has not been reviewed, accepted, published, or
  reproduced on a full native runtime. Unit/integration execution and human review remain
  pending.
- **Reproduction path (for the next iteration, not run here):**
  `bazel test //score/socom/test/unit:socom_test`, plus a targeted case that constructs two
  server connectors differing only in minor version for one `id + major + instance`.

---

## 6. Notice preservation

- No source, build, config, `NOTICE`, `LICENSE`, or `REUSE.toml` file was created, edited, or
  deleted by this task. All existing Apache-2.0/notice headers are untouched.
- Any future implementation in this slice must carry the Apache-2.0 header on new files
  (including `service_identifier_tests.cpp`) per `.github/instructions/code-style.md` and the
  repository's REUSE configuration.

## 7. Pending human review checklist

- [ ] Confirm the baseline binding in §1.2–1.3 (issue #84 ↔ commit `f8a196c3…`).
- [ ] Confirm or amend the accepted draft scope in §3, including the out-of-scope boundary.
- [ ] Answer the design questions in §4, in particular Q1/Q2 on minor-version key semantics.
- [ ] Confirm whether §2.1 is a real defect and, if so, treat it as the slice's regression
      test target.
- [ ] Schedule the deferred full native runtime test run and human review.
