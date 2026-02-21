# F000 - Foundation and Contracts

Status: Completed  
Owner: Jeff + Codex  
Started: 2026-02-20  
Completed: 2026-02-21

## User story

As a maintainer, I want stable architecture contracts and module scaffolding so feature implementation can proceed quickly without rework.

## Scope

- Define and lock interface contracts for core components.
- Define and lock domain model contracts.
- Create base module skeleton aligned to `docs/SYSTEM_DESIGN.md`.
- Create baseline test harness and fixtures layout.

Out of scope:
- End-user CLI feature completeness.
- Bidirectional sync and cross-box status behavior.

## Acceptance criteria

- [x] Core contracts exist and are internally consistent.
- [x] Domain model contracts are documented and referenced by features.
- [x] Module skeleton exists for interface/app/domain/infra boundaries.
- [x] Baseline tests execute for contract-level checks.
- [x] `docs/WORKBOARD.md` marks Phase 0 / Gate G0 complete.

## Implementation phases and steps

Phase A - Contracts
- [x] Finalize command, planner, apply, state, and git gateway contracts.
- [x] Finalize model contracts for context, plan, state, and artifact specs.

Phase B - Structure
- [x] Create package/module layout matching design boundaries.
- [x] Add minimal adapters/mocks to enable test wiring.

Phase C - Validation
- [x] Add contract tests and fixture scaffolding.
- [x] Run baseline test pass and capture known gaps.

## Gate

Gate G0: Foundation accepted

Gate acceptance criteria:
- [x] F000 acceptance criteria checked.
- [x] Phase 1 (`F001`) dependencies reviewed.
- [x] Re-planning checklist executed for next phase.

## Change log

- 2026-02-20: Created Phase 0 feature doc.
- 2026-02-20: Added scaffolding, contracts, pydantic models, and baseline passing tests.
- 2026-02-21: Marked complete and moved to completed work.
