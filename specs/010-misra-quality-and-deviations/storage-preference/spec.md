# Feature Specification: Fabric-wide external SSD preference

**Feature Branch**: Existing working branch; no new branch requested.

**Created**: 2026-10-02

**Status**: Draft; implementation verification does not imply engineering acceptance.

**Input**: User description: "If an external SSD is connected, prefer it; otherwise use internal storage. This is a s-core_sw_fabric rule, not only a rule for SOME/IP."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prefer suitable external storage (Priority: P1)

As a fabric operator, I want all features to place newly allocated disposable builds,
analysis work and tool caches on a suitable mounted external SSD, reducing pressure
on my internal disk.

**Why this priority**: Internal disk exhaustion interrupted the overnight native builds.

**Independent Test**: Create a generic fabric workspace and native tool scratch with
an eligible external SSD present; both reside on that SSD.

**Acceptance Scenarios**:

1. **Given** a suitable mounted external SSD, **When** any fabric feature allocates
   default build or analysis scratch, **Then** the workspace uses that SSD.
2. **Given** an explicit artifact output destination, **When** scratch is allocated
   elsewhere, **Then** the output destination remains unchanged.

### User Story 2 - Continue without external storage (Priority: P1)

As an operator, I want new work to use internal storage when external storage is
absent or unsuitable, with the selection and any rejection reason visible.

**Why this priority**: The same fabric must work with or without a connected SSD.

**Independent Test**: Allocate work with no external SSD and with an incompatible or
unwritable SSD; both use internal storage and report the reason when applicable.

**Acceptance Scenarios**:

1. **Given** no external SSD, **When** new work is allocated, **Then** it uses internal storage.
2. **Given** an external SSD that cannot support the workload, **When** new work is
   allocated, **Then** it uses internal storage with a rejection reason.

### User Story 3 - Preserve data and active work identity (Priority: P1)

As an operator, I want my existing disk files, private credentials and running queues
preserved while future jobs follow the shared preference.

**Why this priority**: Moving active work or exposing secrets would invalidate run state.

**Independent Test**: Bind a workspace, simulate SSD removal, and confirm validation
fails while a newly allocated workspace falls back internally.

**Acceptance Scenarios**:

1. **Given** an active workspace on an SSD, **When** that volume disappears or changes,
   **Then** its validation stops clearly rather than relocating the run.
2. **Given** existing external files, **When** storage is configured, **Then** no existing
   file or partition is formatted or overwritten.
3. **Given** credentials and private server state, **When** builds use an external SSD,
   **Then** that private state remains on internal storage.

### Edge Cases

- Mounted rotating drives are ineligible; multiple eligible SSDs have stable selection.
- Unwritable, non-executable, incompatible or insufficient-space volumes cause fallback.
- An incompatible filesystem requires separately configured compatible build storage.
- A stale image registration or occupied mount point is rejected without overwriting it.
- Explicit output destinations and same-filesystem atomic writes retain their original paths.
- Existing running queues and historical scripts retain their original locations.
- Registered Linux images may use UDisks/kernel mounting. Admission verifies the
  exact loop backing file and native mount; validation never creates a mount.
- A filesystem helper that rejects writes or exits is unsuitable, even if its
  initial permission probe passed. Historical workspace contents remain preserved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All fabric features MUST share the default preference for mounted external
  SSD storage when allocating disposable build, validation and analysis workspaces.
- **FR-002**: Selection MUST verify write access, required filesystem capabilities and
  at least 20 GiB free space on an external build volume; rejection MUST be visible.
- **FR-003**: New work MUST fall back internally if no suitable external SSD exists.
- **FR-004**: Each managed workspace MUST record its selection and validate the bound
  external device and mount identity before reuse.
- **FR-005**: Active work MUST NOT silently move following disconnection; new work may fall back.
- **FR-006**: Configuring compatible build storage MUST preserve existing files and partitions.
- **FR-007**: Private credentials and server state MUST remain internal; explicit output
  destinations and atomic output staging MUST retain their specified locations.
- **FR-008**: The operator MUST be able to inspect selection, allocate a generic workspace,
  and apply the preference to a command's build scratch and tool caches.
- **FR-009**: Storage changes MUST NOT start paid model calls, migrate running queues,
  modify global tool configuration or imply engineering acceptance.

### Key Entities

- **Storage selection**: Selected location, external identity when applicable, free space
  and reasons rejected candidates were unsuitable.
- **Managed workspace**: Disposable work bound to one selection for its lifetime.
- **Compatible build volume**: Registered build storage supporting required file behavior
  while preserving the backing disk's existing contents.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing default native build, analysis and validation workspace
  allocation paths obey the same external preference in code and verification.
- **SC-002**: Absence and every tested unsuitable-storage case yield an internal workspace.
- **SC-003**: Every tested disconnection or substitution prevents active workspace reuse.
- **SC-004**: A real native compile and execution succeed on the connected external SSD.
- **SC-005**: No pre-existing user file, historical run script or running queue is changed
  by storage setup; credentials remain internal.

## Assumptions

- This is bounded cross-cutting maintenance within active increment 010, not a new
  roadmap increment or authorization to continue into increment 011.
- The desktop or operator mounts the physical SSD; fabric discovery does not mount raw disks.
- Preference applies to newly allocated defaults; explicit destinations remain authoritative.
- Compatible build storage on a filesystem without native file capabilities is explicitly
  configured once and reused; absent prerequisites produce internal fallback.
