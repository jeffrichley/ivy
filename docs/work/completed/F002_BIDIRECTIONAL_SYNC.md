# F002 - Bidirectional Sync and Promotion

Status: Completed  
Owner: Jeff + Codex  
Started: 2026-02-21  
Target phase: Phase 2 / Gate G2
Completed: 2026-02-21

## User story

As a developer, I can intentionally promote local managed changes back to the garden and safely propagate them across beds without silent overwrite.

## Scope

- `ivy add <file>` registers managed artifacts and seeds garden content.
- `ivy add <file> --sync` performs immediate registration + distribution.
- `ivy push` promotes bed-side managed changes to garden source.
- `ivy pull` updates garden from canon with guarded ff-only behavior.
- Drift classification and status vocabulary are explicit and stable.

Out of scope:
- TUI workflows
- Watch/auto-pull daemon behavior

## Required status vocabulary

- `IN_SYNC`
- `SOURCE_ONLY`
- `DRIFTED` (one-way local-only change; block by default)
- `BOTH_CHANGED`

## Required command flags

- `plan/sync/push --only <artifact_id>`
- `plan/sync/push --bed <bed_id>`
- `push --json`

## Acceptance criteria

- [x] `ivy add <file>` updates `ivy.yaml` and seeds source content.
- [x] `ivy add <file> --sync` works end-to-end.
- [x] One-way local edits are reported as `DRIFTED`, not `CONFLICT`.
- [x] `push` promotes only safe, eligible changes.
- [x] `push`/`pull` enforce git cleanliness and ff-only policies.
- [x] `--only` and `--bed` selectors work for `plan`, `sync`, and `push`.
- [x] `push --json` emits stable machine-readable output.
- [x] Drift and conflict matrix tests pass.

## Gate

Gate F002: Feature ready for completion move

Gate acceptance criteria:
- [x] All F002 acceptance criteria checked.
- [x] CLI/docs updated for new vocabulary and flags.
- [x] Workboard and phase docs updated.

## Completion evidence

- `pull` command and ff-only git flow: `src/ivy/app/commands/pull.py`, `src/ivy/cli/router.py`
- Conflict policy engine + non-interactive prompt fallback: `src/ivy/app/commands/_conflicts.py`
- Policy-aware sync/push behavior: `src/ivy/app/commands/sync.py`, `src/ivy/app/commands/push.py`
- Pull git safety tests: `tests/test_pull_command.py`
- Drift/conflict policy matrix tests: `tests/test_conflict_policy.py`
- Full suite pass (at completion time): `39 passed` via `uv run pytest -q`

## Decision note

- `ivy push` is the designated command for git publishing workflows.
- In this completed cut, `ivy push` performs safe bed->garden promotion only.
- Direct git publish (`git add/commit/push`) via `ivy push` was delivered in follow-up spec `docs/work/completed/F002_PUSH_PUBLISH_FLAGS.md`.

## Change log

- 2026-02-20: Initial feature spec created.
- 2026-02-21: Moved to current work and aligned with implemented `add`/`push`/selectors/json behavior.
- 2026-02-21: Implemented `pull`, conflict policy strategies, non-interactive prompt fallback, and matrix tests.
- 2026-02-21: Documented `ivy push` as the future git publish entrypoint with current promotion-only behavior.
