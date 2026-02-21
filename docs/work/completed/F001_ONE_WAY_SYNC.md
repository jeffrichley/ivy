# F001 - One-Way Deterministic Sync

Status: Completed  
Owner: Jeff + Codex  
Started: 2026-02-20
Last updated: 2026-02-21
Completed: 2026-02-21

## User story

As a developer, I can register a project as a bed and run `ivy plan` / `ivy sync` to copy garden artifacts into that project safely and predictably.

## Scope

- `ivy plant` writes `.ivy/bed.yaml` in the project root.
- `ivy plan` computes file actions with no writes.
- `ivy sync` applies planned copy actions.
- `ivy status` reports in-sync vs drift for registered bed content.

Out of scope:
- Bidirectional promotion (`push`/`pull`)
- Conflict merge flows
- Watch mode / auto-pull
- TUI

## Contracts touched

- `CommandRouter`
- `InitBedCommand`
- `PlanCommand`
- `SyncCommand`
- `StatusCommand`
- `ContextResolver`
- `ConfigResolver`
- `ArtifactCatalog`
- `SelectorEngine`
- `PlanBuilder`
- `ApplyEngine`
- `StateStore`

## Acceptance criteria

- [x] `ivy plant` creates `.ivy/bed.yaml`.
- [x] `ivy plan` shows create/update/skip actions and does not write files.
- [x] `ivy sync` applies only planned actions (copy mode).
- [x] Re-running `ivy sync` without changes yields no-op.
- [x] `ivy status` reports in-sync vs drift.

Current gate score: `5/5` acceptance criteria complete.

## Implementation phases and steps

Phase A - Setup and contracts
- [x] Finalize command contracts for `plant`, `plan`, `sync`, `status`.
- [x] Finalize domain models used by planner and status flow.

Phase B - Plan pipeline
- [x] Implement context + config resolution for Cut 001 scope.
- [x] Implement artifact load and selection.
- [x] Implement deterministic plan generation.
- [x] Add tests proving `plan` does not write files.

Phase C - Apply and state
- [x] Implement copy-mode apply engine.
- [x] Implement local state write for applied actions.
- [x] Add no-op repeat sync test.

Phase D - Status and hardening
- [x] Implement status read model for in-sync vs drift.
- [x] Add CLI integration tests for `status` (plan/sync/plant coverage exists).
- [x] Validate safety defaults and error messages.

## Gate

Gate F001: Feature ready for completion move

Gate acceptance criteria:
- [x] All F001 acceptance criteria are checked.
- [x] Unit and integration tests pass for F001 flows (including status).
- [x] Feature behavior is documented in command help and docs.
- [x] `docs/WORKBOARD.md` updated before moving to completed.

## Implemented evidence

- `plant` behavior and aliases: `tests/test_init_commands.py`
- Deterministic plan/sync + no-op rerun: `tests/test_plan_sync_actions.py`
- Bed discovery and planning scope: `tests/test_plan_sync_scope.py`
- Selector behavior for plan/sync: `tests/test_selectors_and_push_json.py`

## Completion evidence

- `StatusCommand` implemented: `src/ivy/app/commands/status.py`
- CLI status wiring + flags (`--all`, `--garden-id`, `--only`, `--bed`, `--json`): `src/ivy/cli/router.py`
- Status rendering: `src/ivy/cli/render.py`
- Status integration tests: `tests/test_status_command.py`
- Full suite pass: `33 passed` via `uv run pytest -q`

## Notes

- Safety defaults apply: no silent destructive behavior.
- Deterministic ordering is required for all plan outputs.
- Hidden alias remains available: `ivy init-bed`.

## Change log

- 2026-02-20: Created feature spec and set as active item.
- 2026-02-21: Updated command naming from `init bed` to `plant` with alias.
- 2026-02-21: Marked plan/sync/state milestones complete; status remains open.
- 2026-02-21: Added explicit closeout checklist and implementation evidence links.
- 2026-02-21: Implemented status command + tests; marked F001 complete.
