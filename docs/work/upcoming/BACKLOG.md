# Feature Backlog

Last updated: 2026-02-21

## Immediate next work

## F003 - Cross-box status

Steps:
- [ ] Write/read `status/<box_id>.json`.
- [ ] Add `ivy status --boxes`.

Gate G3 acceptance:
- [ ] Snapshot schema versioned.
- [ ] Missing/stale snapshot handling validated.

## F004 - Watch / Auto-Pull

Steps:
- [ ] File watch and debounce.
- [ ] Safety-aware auto-pull behavior.

Gate G4 acceptance:
- [ ] Dirty-state protections verified.
- [ ] Auto-pull respects conflict policy.

## F005 - TUI

Steps:
- [ ] Dashboard view.
- [ ] Artifact detail view.
- [ ] Setup wizard.

Gate G5 acceptance:
- [ ] TUI uses existing engine paths.
- [ ] UI state matches CLI outputs.
