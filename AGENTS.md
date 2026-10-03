# Working in s-core_sw_fabric

Read `.specify/memory/constitution.md`, the active `specs/<increment>/` and
`docs/handoff/000-to-001.md`. The attached first-session scope ends after 000 and
001 planning. Do not treat the brief's automatic continuation as authorization.

- Preserve user work, including the original brief. Never write/build in reference
  repositories. Use disposable copies for native builds; inspect hooks first.
- Fabric-wide storage rule: prefer a mounted, writable external SSD for new
  disposable workspaces, native builds, analysis scratch and tool caches; fall back
  to internal storage when none is suitable. Use `score_sw_fabric.storage` and
  `score-fabric storage` across all features. Honor explicit artifact destinations.
  Require measured Linux filesystem capabilities; use a registered Linux build
  image on incompatible filesystems without reformatting existing disks or files.
  Bind each workspace to its selected volume; stop on disconnection rather than
  silently relocating active work. Keep credentials and private server state on
  internal storage. Do not migrate running queues or alter global tool storage.
- Spec Kit controls fabric development. S-CORE owns target semantics and native
  artifacts. Fabro owns execution and run state. APM/MCP provides context/tools.
- Source locks are reviewed baselines. Unknown capability or applicability remains
  explicit; never invent a native identifier or copy an unverified CLI example.
- Agents draft; deterministic tools measure; authorized humans accept engineering
  decisions. Tests, analyzer cleanliness and Fabro success never imply acceptance.
- Never add a scheduler, requirements database, hidden policy, automatic approvals,
  paid model call, publishing, merging, release or deployment without task authority.
- Contracts marked proposed are not validated implementations. Preserve source IDs,
  native statuses and license notices. Fixtures cannot satisfy real readiness.
- Use Python >=3.12, `uv sync --frozen`, Ruff, mypy and pytest. Run
  `uv run --frozen python scripts/check_foundation.py` and `uv build` for foundation changes.
- For Spec Kit scripts use the pinned CLI on PATH and explicit
  `SPECIFY_FEATURE_DIRECTORY="$PWD/specs/<increment-slug>"`; this release does not
  infer the directory solely from a Git branch. Keep detailed tasks limited to the
  current and next increment. Do not check off human-owned review items.

Invariant: If Fabro disappeared tomorrow, all authoritative S-CORE engineering
artifacts would remain valid and understandable.

## User handoff preference

End every final response about this repository with two explicit, concise lines:
- Next step: the most useful concrete action, or "none" if work is complete.
- Recommended model: an exact available model name (and reasoning effort when useful),
  with a brief task-specific reason. Reassess the choice for each step; never imply
  that naming a model switches the current session automatically.
