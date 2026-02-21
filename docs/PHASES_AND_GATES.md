# Ivy - Phases, Steps, Gates, and Acceptance Criteria

This document defines execution phases for delivering Ivy and the quality gates required to move between phases.

Last updated: 2026-02-21

## Planning policy

- Detailed planning now: Phase 0 through Phase 2.
- Provisional planning now: Phase 3 through Phase 5.
- Re-planning checkpoint: before starting each new phase, after prior gate is accepted.

Re-planning checklist (run at each gate):
- [ ] Confirm scope still matches product goals.
- [ ] Update steps and acceptance criteria for next phase.
- [ ] Confirm dependencies and risks.
- [ ] Update `docs/WORKBOARD.md` and upcoming feature specs.

## Phase checklist

- [x] Phase 0: Foundation and contracts
- [x] Phase 1: Cut 001 one-way deterministic sync
- [x] Phase 2: Cut 002 bidirectional sync
- [ ] Phase 3: Cut 003 cross-box status
- [ ] Phase 4: Cut 004 watch and auto-pull
- [ ] Phase 5: Cut 005 TUI

## Phase 0 - Foundation and contracts

Planning depth: Detailed

Goal: lock architecture contracts and project scaffolding.

Steps:
- [x] Create module skeleton aligned to `docs/SYSTEM_DESIGN.md`.
- [x] Define interface contracts for core components.
- [x] Define domain models for context, artifacts, plans, and state.
- [x] Add base test harness and fixture layout.

Gate G0: Contract baseline approved

Acceptance criteria:
- [x] Contracts exist for router, commands, planner, applier, state, and git gateway.
- [x] Contract tests compile and run.
- [x] Core docs are linked from `docs/README.md`.

## Phase 1 - Cut 001 one-way deterministic sync

Planning depth: Detailed

Goal: ship first usable CLI with safe one-way sync.

Steps:
- [x] Implement `ivy plant` (`init-bed` alias) and `.ivy/bed.yaml` generation.
- [x] Implement context and config resolution with precedence.
- [x] Implement artifact catalog + selector flow.
- [x] Implement planning pipeline for create/update/skip.
- [x] Implement apply pipeline in copy mode.
- [x] Implement local state persistence (`last_applied`).
- [x] Implement `ivy status` basic drift states.
- [x] Add CLI integration tests for `plan`, `sync`, `status`, `plant`.

Gate G1: Cut 001 ready

Acceptance criteria:
- [x] `ivy plant` creates `.ivy/bed.yaml`.
- [x] `ivy plan` reports actions with no writes.
- [x] `ivy sync` applies only planned actions.
- [x] Re-running `ivy sync` without changes is a no-op.
- [x] `ivy status` reports in-sync vs drift.
- [x] All Cut 001 tests (including status coverage) pass.

## Phase 2 - Cut 002 bidirectional sync

Planning depth: Detailed

Goal: add safe two-way promotion workflows.

Steps:
- [x] Implement `ivy pull` with guarded `git pull --ff-only`.
- [x] Implement `ivy add` to register managed artifacts in garden `ivy.yaml`.
- [x] Implement `ivy push` bed-to-source promotion.
- [x] Implement conflict policy strategies.
- [x] Add non-interactive fallback for `prompt` policy.
- [x] Add drift classification with explicit states: `IN_SYNC`, `SOURCE_ONLY`, `DRIFTED`, `BOTH_CHANGED`.
- [x] Use `DRIFTED` (not `CONFLICT`) for one-way local-only edits.
- [x] Add selectors: `--only <artifact_id>` and `--bed <bed_id>` for `plan`, `sync`, and `push`.
- [x] Add machine-readable output: `ivy push --json`.

Gate G2: Cut 002 ready

Acceptance criteria:
- [x] `ivy add <file>` registers artifact mappings and seeds garden source.
- [x] `ivy add <file> --sync` applies distribution immediately.
- [x] One-way local edits surface as `DRIFTED` and are blocked by default safety policy.
- [x] `plan/sync/push` support `--only` and `--bed` scoping.
- [x] `ivy push --json` output is stable and tested.
- [x] `push` and `pull` both respect git cleanliness guards.
- [x] Default conflict policy is `prompt`.
- [x] No auto-commit without explicit opt-in.
- [x] Conflict and drift test matrix passes.

## Phase 3 - Cut 003 cross-box status

Planning depth: Provisional (refine at Gate G2)

Goal: provide status visibility across machines without servers.

Steps:
- [ ] Implement status snapshot schema and writer.
- [ ] Write/read `status/<box_id>.json`.
- [ ] Implement `ivy status --boxes`.
- [ ] Handle missing/stale snapshots safely.

Gate G3: Cut 003 ready

Acceptance criteria:
- [ ] Snapshot schema is versioned.
- [ ] `status --boxes` reports per-box state.
- [ ] Cross-box flow passes integration tests.

## Phase 4 - Cut 004 watch and auto-pull

Planning depth: Provisional (refine at Gate G3)

Goal: optional background syncing with strict safety.

Steps:
- [ ] Implement watcher loop with debounce.
- [ ] Implement optional auto-pull polling.
- [ ] Add dirty-state protection behavior.
- [ ] Add OS integration hooks (where supported).

Gate G4: Cut 004 ready

Acceptance criteria:
- [ ] Watch mode applies only safe, policy-compliant actions.
- [ ] Dirty states block destructive updates.
- [ ] Auto-pull never bypasses safety rules.

## Phase 5 - Cut 005 TUI

Planning depth: Provisional (refine at Gate G4)

Goal: add a thin UI over stable engine behavior.

Steps:
- [ ] Implement dashboard view.
- [ ] Implement artifact detail view.
- [ ] Implement mapping/setup wizard.
- [ ] Wire UI actions to existing engine commands only.

Gate G5: Cut 005 ready

Acceptance criteria:
- [ ] TUI executes the same engine paths as CLI.
- [ ] Dashboard reflects plan/sync/status accurately.
- [ ] Wizard writes valid config artifacts.
