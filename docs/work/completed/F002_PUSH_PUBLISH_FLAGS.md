# F002 Follow-up - Push Publish Flags

Status: Completed  
Owner: Jeff + Codex  
Started: 2026-02-21
Completed: 2026-02-21

## User story

As a maintainer, I want `ivy push` to optionally run git publish steps so I can promote and publish safely in one command when I explicitly opt in.

## Scope

In scope:
- Add `ivy push --commit` to stage and commit promoted changes.
- Add `ivy push --push` to push committed changes to remote.
- Keep default `ivy push` behavior promotion-only (no commit/push).
- Add safety checks for non-interactive and dirty-tree states.
- Add structured output fields indicating publish operations performed.

Out of scope:
- Changing default behavior to auto-commit or auto-push.
- New standalone publish command (`ivy publish`).
- Cross-box status or watch mode behavior.

## Contracts touched

- `PushCommand`
- `GitPythonGateway`
- `CommandRouter` (`push` CLI options and help)
- `CommandResult` payload contract for push reporting

## Acceptance criteria

- [x] `ivy push` without flags only updates garden working tree.
- [x] `ivy push --commit` stages and commits only intended garden changes.
- [x] `ivy push --push` requires `--commit` (or explicit equivalent) and pushes to configured remote.
- [x] Publish path is blocked when git safety invariants fail (dirty state, missing remote, push failure).
- [x] No auto-commit/push occurs without explicit opt-in.
- [x] Push JSON output includes publish outcomes (`committed`, `pushed`, commit id or reason for skip/failure).

## Implementation phases and steps

Phase A - CLI and contract updates
- [x] Define final flag contract: `--commit`, `--push`, and validation rules.
- [x] Update `push` command help and JSON payload schema docs.
- [x] Add clear user-facing error messages for invalid flag combinations.

Phase B - Git publish implementation
- [x] Implement git stage+commit flow in gateway and push command path.
- [x] Implement push-to-remote flow with explicit remote/branch handling.
- [x] Ensure publish only runs after successful promotion plan/apply.

Phase C - Safety and non-interactive behavior
- [x] Enforce dirty-tree, missing-remote, and no-op commit safeguards.
- [x] Enforce deterministic behavior in non-interactive runs.
- [x] Preserve current safety defaults (opt-in only publish).

Phase D - Tests and docs
- [x] Add integration tests for promotion-only, commit-only, and commit+push flows.
- [x] Add failure-path tests (dirty tree, missing remote, push failure).
- [x] Update docs/workboard/phase references after passing tests.

## Gate

Gate F002-Followup: Push publish flags ready

Gate acceptance criteria:
- [x] All acceptance criteria checked.
- [x] Test matrix for publish/no-publish and failure modes passes.
- [x] CLI/docs reflect final behavior and safety defaults.
- [x] Workboard/backlog updated.

## Notes

- Current implemented baseline: `ivy push` promotes content only.
- This follow-up intentionally extends `ivy push` rather than introducing a new publish command.

## Completion evidence

- CLI flags and validation: `src/ivy/cli/router.py`
- Publish implementation: `src/ivy/app/commands/push.py`
- Git gateway commit/remote support: `src/ivy/infra/git/gateway.py`
- Publish test matrix: `tests/test_push_publish_flags.py`
- Full suite pass: `46 passed` via `uv run pytest -q`

## Change log

- 2026-02-21: Created follow-up plan for push publish flags.
- 2026-02-21: Implemented and validated publish flags; marked completed.
