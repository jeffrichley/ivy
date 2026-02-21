# Ivy - System Design and Component Contracts

This document defines the major architectural pieces of Ivy and the contracts between them so implementation can proceed in parallel without ambiguity.

Status: Active design baseline (updated for current CLI and contracts).

## 1. Design goals

- Deterministic behavior: same input state -> same plan/apply result.
- Conservative safety defaults: no silent destructive actions.
- Explicit layering: UI/CLI thin, engine authoritative.
- Expandable architecture: new beds, sources, resolvers, policies without core rewrites.
- Testable contracts: each component has a clear interface and boundaries.

## 2. Architecture at a glance

Layers:

1. Interface layer: CLI (and later TUI) parses intent.
2. Application layer: command handlers orchestrate workflows.
3. Domain layer: sync planning, drift/conflict logic, policy enforcement.
4. Infrastructure layer: filesystem, git, secret backends, local state, status registry.

Core rule: interface never implements sync logic directly; it only calls application services.

## 3. Major components and contracts

### 3.1 `CommandRouter` (Interface Facade)

Responsibility:
- Map CLI subcommands (`seed`, `plant`, `add`, `plan`, `sync`, `push`, `status`) to command handlers.
- Preserve hidden compatibility aliases (`init`, `init-bed`).

Contract:
- Input: parsed `CommandRequest`.
- Output: `CommandResult` with exit code, human-readable report, and machine-readable payload.
- No filesystem/git logic allowed.

Pattern:
- Facade.

### 3.2 `Command` handlers (Application layer)

Core handlers:
- `InitGardenCommand`
- `InitBedCommand`
- `AddCommand`
- `PlanCommand`
- `SyncCommand`
- `StatusCommand`
- `PushCommand`

Planned handler:
- `PullCommand`

Contract:
- Accept `ExecutionContext` and command options.
- Call domain services in deterministic order.
- Emit `ExecutionReport`.

Pattern:
- Template Method (shared command lifecycle: load context -> validate -> execute -> report).

### 3.3 `ContextResolver`

Responsibility:
- Detect runtime context: OS, arch, hostname, username, cwd project root, box_id, profile, selected garden.

Contract:
- `resolve(request) -> RuntimeContext`
- No side effects except optional initial `box_id` materialization.

Pattern:
- Builder (constructs `RuntimeContext` from multiple probes).

### 3.4 `ConfigResolver`

Responsibility:
- Merge layered configuration with fixed precedence:
  `global < garden < profile < platform < box < project < CLI`.

Contract:
- `resolve(context, cli_overrides) -> EffectiveConfig`
- Deterministic deep-merge semantics.
- Returns provenance metadata for `--explain`.

Pattern:
- Chain of Responsibility (layer processors).

### 3.5 `ArtifactCatalog`

Responsibility:
- Load and normalize artifact definitions from manifests/config.

Contract:
- `list_artifacts(effective_config) -> list[ArtifactSpec]`
- Validate schema and required fields.

Pattern:
- Factory Method (creates typed artifact specs by kind).

### 3.6 `SelectorEngine`

Responsibility:
- Select applicable artifacts/beds based on context selectors and filters.

Contract:
- `select(catalog, context, filters) -> SelectionResult`
- Must be pure and deterministic.

Pattern:
- Strategy (selector implementations per selector type).

### 3.7 `RenderEngine`

Responsibility:
- Render templates with approved variables and secret placeholders.

Contract:
- `render(artifact, context, values) -> RenderedArtifact`
- No writes to disk.
- Must fail closed on unresolved required variables.

Pattern:
- Strategy (template engine variants), Adapter (Jinja backend).

### 3.8 `SecretResolver`

Responsibility:
- Resolve secret/value references from allowed sources (1Password, Bitwarden, keychain, env allowlist, local gitignored file).

Contract:
- `resolve(ref, context) -> SecretValue`
- Read-only behavior; never persists plaintext into ivy config/state.

Pattern:
- Abstract Factory + Strategy (backend providers).

### 3.9 `DriftDetector`

Responsibility:
- Compare source, bed, and `last_applied` to classify state.

Contract:
- `detect(source_snapshot, bed_snapshot, last_applied) -> DriftState`
- Outputs: `IN_SYNC | SOURCE_ONLY | DRIFTED | BOTH_CHANGED`.

Pattern:
- State (explicit drift state model).

### 3.10 `PlanBuilder`

Responsibility:
- Build an ordered execution plan from drift and policy.

Contract:
- `build(selection, rendered, drift, policies, mode) -> ExecutionPlan`
- Mode examples: `plan`, `sync`, `pull`, `push`.

Pattern:
- Builder.

### 3.11 `ConflictResolver`

Responsibility:
- Apply conflict policy (`prompt`, `abort`, `source_wins`, `bed_wins`, `merge`) and produce actions.

Contract:
- `resolve(conflict, policy, io) -> ResolutionAction`
- In non-interactive mode, `prompt` degrades to `abort`.

Pattern:
- Strategy.

### 3.12 `ApplyEngine`

Responsibility:
- Execute plan actions with atomic writes, backup policy, and path safety checks.

Contract:
- `apply(plan, write_mode) -> ApplyResult`
- Supports `dry_run` and `diff_only`.
- Guarantees idempotent no-op when already in desired state.

Pattern:
- Command (each plan step is an executable action object).

### 3.13 `StateStore`

Responsibility:
- Persist machine-local operational state (including `last_applied`).

Contract:
- `get(artifact_key, bed_key) -> StateEntry?`
- `put(artifact_key, bed_key, StateEntry) -> None`
- `transaction(actions) -> None`

Storage:
- Default path: `~/.ivy/state/state.json` (or `IVY_HOME/state/state.json`).

Pattern:
- Repository.

### 3.14 `GitGateway`

Responsibility:
- Encapsulate all git operations with explicit safety guards.

Contract:
- `pull_ff_only(repo_path) -> GitResult`
- `status_clean(repo_path) -> bool`
- `commit(repo_path, message) -> GitResult` (opt-in only)
- `push(repo_path) -> GitResult` (never force)

Pattern:
- Adapter.

### 3.15 `StatusRegistry` (Cut 003+)

Responsibility:
- Read/write per-box status snapshots for cross-box visibility.

Contract:
- `write(box_id, snapshot) -> None`
- `read_all() -> list[BoxStatus]`

Pattern:
- Repository.

## 4. Core domain models (contract-level)

```text
ArtifactSpec
- id: str
- source: PathSpec
- beds: list[BedTarget]
- direction: one_way | two_way
- conflict_policy: prompt | abort | source_wins | bed_wins | merge
- selectors: SelectorSet
- render: RenderSpec?

ExecutionContext
- command: str
- garden_id: str
- box_id: str
- profile: str?
- project_root: path?
- dry_run: bool
- explain: bool
- filters: FilterSet

ExecutionPlan
- items: list[PlanAction]
- summary: PlanSummary

PlanAction
- type: CREATE | UPDATE | DRIFTED | BOTH_CHANGED | COPY | RENDER | BACKUP | DELETE | PROMOTE_BED_TO_SOURCE | SKIP | CONFLICT
- artifact_id: str
- source_path: path?
- target_path: path?
- reason: str

StateEntry
- artifact_id: str
- bed_path: str
- last_applied_hash: str
- last_applied_at: timestamp
- last_direction: source_to_bed | bed_to_source
```

## 5. End-to-end command pipelines

### 5.1 `ivy plan`

1. Resolve context/config.
2. Load catalog and select artifacts.
3. Render templates and resolve values.
4. Detect drift.
5. Build plan.
6. Report only (no writes, no state mutation).

Status classification vocabulary (required):
- `IN_SYNC` - source and target match.
- `SOURCE_ONLY` - only source changed since last applied baseline.
- `DRIFTED` - only target changed locally since last applied baseline (one-way mode; blocks sync by default).
- `BOTH_CHANGED` - source and target both changed since last applied baseline (conflict-like state).

### 5.2 `ivy sync` (Cut 001 default behavior)

1. Run same planning pipeline as `plan`.
2. Classify actions (`CREATE`, `UPDATE`, `SKIP`, plus guarded states like `DRIFTED`/`BOTH_CHANGED`).
3. Apply safe actions.
4. Update local state entries for applied actions.
5. Print summary/report.

### 5.3 `ivy push` (Cut 002)

1. Resolve context/config for two-way artifacts.
2. Detect bed-side changes for managed artifacts.
3. Promote bed -> source (working tree update).
4. Optional publish step (git add/commit/push) only with explicit flags/config.

Current status:
- Implemented: promotion to garden working tree.
- Implemented: explicit publish flags on `ivy push` for commit/push.

Required UX/API details:
- `ivy push --json` emits machine-readable action/status output.
- `ivy push --only <artifact_id>` limits push to one artifact.
- `ivy push --bed <bed_id>` limits push to one bed.
- `ivy push --commit` stages and commits promoted changes.
- `ivy push --push` requires `--commit` and pushes committed changes to remote.

### 5.4 `ivy add` (Cut 002)

1. Resolve current bed context.
2. Register provided file path(s) as managed artifacts in garden `ivy.yaml`.
3. Seed garden source content from current bed file(s) under `assets/shared/...`.
4. Optional `ivy add <file> --sync` runs immediate distribution after registration.

Selector requirements for sync/plan:
- `ivy plan --only <artifact_id>` and `ivy sync --only <artifact_id>` limit action scope.
- `ivy plan --bed <bed_id>` and `ivy sync --bed <bed_id>` limit action scope.

## 6. Error and safety contract

Error classes:
- `ConfigError` (invalid schema/layering)
- `SelectionError` (invalid selectors)
- `RenderError` (missing variable/secret)
- `ConflictError` (unresolved conflict)
- `ApplyError` (filesystem write/permission)
- `GitError` (dirty tree, ff-only failed, push failure)

Safety invariants:
- Never overwrite dirty target silently when policy forbids it.
- Never force push.
- Never execute scripts from garden content.
- Never store plaintext secrets in garden/state.
- All destructive actions must appear in plan output first.

## 7. GoF pattern mapping summary

- Facade: `CommandRouter`
- Template Method: command handler lifecycle
- Strategy: selectors, conflict policies, secret backends, template engines
- Abstract Factory: backend provider construction
- Adapter: git/filesystem/secret tooling integration
- Builder: `RuntimeContext`, `ExecutionPlan`
- Command: `PlanAction` execution objects
- State: drift/conflict state model
- Repository: state store and status registry
- Observer (Cut 004 watch mode): file/watch events feeding sync triggers

## 8. Extensibility contracts

New bed type:
- Implement `BedAdapter` contract:
  - `scan(target) -> BedSnapshot`
  - `validate_target(path) -> ValidationResult`
  - `apply(action) -> ApplyResult`
- Register adapter in `BedAdapterRegistry`.

New source type:
- Implement `SourceAdapter` contract:
  - `fetch() -> SourceSnapshot`
  - `read(path) -> bytes`
- Register via source factory.

New secret backend:
- Implement `SecretBackend`:
  - `can_resolve(ref) -> bool`
  - `resolve(ref) -> SecretValue`

All plugins must be deterministic and side-effect bounded by declared contract.

## 9. Proposed module boundaries (implementation blueprint)

```text
src/ivy/
  cli/
    router.py
  app/
    commands/
  domain/
    models/
    selection/
    planning/
    drift/
    conflict/
  infra/
    fs/
    git/
    secrets/
    state/
    status_registry/
  interfaces/
    contracts.py
```

## 10. Acceptance criteria for this design

- Every major command can be implemented by wiring existing contracts.
- Core logic can be unit-tested without real git/filesystem/network.
- New bed/source/secret backends can be added without changing planner core.
- Cut 001 features fit directly; Cut 002/003 add capabilities by plugging into existing contracts rather than redesign.
