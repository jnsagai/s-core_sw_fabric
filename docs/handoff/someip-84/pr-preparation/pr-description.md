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

# Bugfix

## Description

Constructing two SOCom servers with the same service ID, major version and instance
but different minor versions previously occupied separate registration slots while
resolving to the same `Service_database` record. Enabling both could reach the
duplicate-server assertion. The registration key now compares instance, service ID
and major version, so the second construction returns
`Construction_error::duplicate_service` while the first connector exists.

The six-file change adds regression coverage for disabled/enabled connectors,
minor-version and 16-bit boundaries, distinct service/major/instance slots, slot
reuse after destruction, compatibility and ordering properties. The existing
exact-major and client-minor ≤ server-minor matching rules remain covered.

## Related ticket

Related to https://github.com/eclipse-score/inc_someip_gateway/issues/84.

This contribution implements the registration-key bugfix slice. Public identifier
types, optional discovery filters and minor-version representation remain part of
the broader issue. Maintainers can track this bounded fix separately while retaining
the remaining design work under #84; this draft has no automatic issue-closing keyword.

## Validation

- GCC 12 and Clang 19 focused regression executions: 91 tests passed each.
- Native `//score/socom/test/unit:socom_test` and formatting check passed.
- Linux QEMU integration: all six targets executed; 13 applicable cases passed.
  The QNX split-process gateway case was excluded on Linux using its native
  applicability source and exact reason.
- Both native end-to-end profiling targets passed; 12 datasets and 12 flamegraphs
  retained, with no reported benchmark errors.
- Unchanged passing checks were reused only with identical candidate hashes and
  verified original evidence; failed runs remain preserved.

Evidence run: `01M40Y7RJF9NZJTE2N9Z3BAAXA`; fresh integration run:
`01M40XMJ9K182CG0SWBNVPY7AB`. Portable archive SHA-256:
`2b8f5c40ae194ba06f8e6c95933c05727ec8f4bec563ef7c4fc10ef3e33fa6da`.
The companion local handoff contains the archive, XML, raw logs and offline verification.

## Review scope

The user approved the scoped work and local PR preparation outside Fabro. Committer
review and upstream CI remain part of the contribution process. Local tool
qualification, QNX target execution and full MISRA acceptance are not established
by these measurements. The fabric workflow/helper changes stay in the fabric
repository; the native contribution contains only the six SOCom source/build/test files.
