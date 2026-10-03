# Tasks: Fabric-wide storage preference

- [x] T001 Specify shared preference, fallback and preservation behavior.
- [x] T002 Prepare compatible build storage on connected SSD without overwriting existing files.
- [x] T003 Centralize selection, workspace binding and private internal server paths.
- [x] T004 Integrate shared allocation across fabric native build and quality tool paths.
- [x] T005 Add generic storage CLI and feature compatibility wrappers.
- [x] T006 Verify contracts, real external compilation, internal fallback, lint and types.
- [x] T007 Run required foundation check and package build; document verified results.
- [x] T008 Reproduce Docker snapshot failure on the real SSD and implement shared archive
  transfer preserving source bytes/modes while excluding Fabro-owned Git metadata.
- [x] T009 Verify archive boundaries and actual host collectors on the preserved workspace;
  record detailed infrastructure errors and eliminate whole-chain loops for single-pass runs.
- [x] T010 Freeze corrected controls and restart the complete queue with prior changes/reports
  preserved, then verify worker, isolation and native stage progress.
- [x] T011 Diagnose repeated FUSE write failures; verify the preserved image using offline
  filesystem checks and kernel mounting, including backing-file substitution rejection.
- [x] T012 Rerun real compiler, coverage and process collectors on the kernel SSD mount;
  run Ruff, mypy, 46 relevant contracts, foundation consistency and package build.
- [ ] Human-owned engineering review and acceptance, if applicable.
