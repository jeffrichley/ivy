# Ivy — Features Plan

Organized outline of all ideas from the initial ideas chat. Use this to align on scope, phases, and open decisions.

---

## 1. Project Identity & Constraints

### What Ivy Is
- **Ivy** = distributed capability sync layer.
- One-line identity: *"A bidirectional, context-aware capability distribution engine with Git-backed state and optional live sync."*
- She is: **deterministic**, **conflict-aware**, **layered**, **safe**, **minimal at first**, **deep later**.

### Default stance (intentional)
- Ivy is a **disciplined infrastructure tool**, not a magical automation layer. This is an explicit product choice.
- **Ivy’s defaults are conservative and explicit. Automation is opt-in.** Copy (not symlink), no auto-commit, prompt on conflict, engine-first — all of that is intentional. Power users can relax settings; the baseline stays predictable and safe.
- Stating this in the spec sets tone for future contributions and for anyone reading the project: we favor clarity and control over convenience-by-default.

### Original Problem
- Shared Git repo that syncs across projects and computers for:
  - Cursor slash commands
  - Codex CLI prompts
  - Reusable agent command files
- Ivy **syncs assets into** projects (and other beds); the **tool** itself is installed once, globally or per-user (§3).

### Hard Constraints (from day one)
- Nothing overly complex
- **Git as source of truth**
- Simple pull + copy mechanism (no symlink weirdness unless explicitly chosen)
- `git pull --ff-only` behavior
- Works across multiple computers
- Project copies treated as **derived artifacts** (not the source of truth)

### What Ivy Is NOT
- Not a full **dotfile manager**, **package manager**, **deployment orchestrator**, **config framework**, or **CI system**.
- Not a **secret store (vault)** — Ivy does not store or manage the authoritative copy of API keys, passwords, or tokens. That stays in 1Password, Bitwarden, OS keychain, or another secret manager.
- **Boundary (decided):** *"Ivy distributes declarative artifacts and manages drift. She does not execute arbitrary code from gardens."*

**What Ivy *does* support (in scope):**
- **Secret resolution** — When syncing, Ivy can resolve template placeholders by calling your real secret backend (1Password CLI, Bitwarden, keychain) or from env / a gitignored local file. The garden never holds plaintext secrets; Ivy fills in values at sync time (§9).
- **.env / value filling** — A bed like `.env` can be produced from a template (list of variable names) with values resolved from the same sources above.
- **Shell rc files (e.g. `.zshrc`)** — Ivy may sync fragments or a full rc file into `~/.zshrc` (or similar). The artifact is a text file; Ivy does not run shell code.
- **Arbitrary system paths** — Ivy may write to any path the user configures (not a fixed allowlist). Optional **path allowlist / safe mode** (e.g. restrict to known-safe dirs) can be offered as an opt-in safety feature.

**What Ivy does *not* do (decided):**
- **Auto-run scripts** — Ivy never executes code from the garden (no post-sync hooks or scripts from the repo). Only copy, symlink, and template rendering.

---

## 2. Core Concepts

### Garden
- A **Garden** is a source package containing:
  - **assets** (files to distribute)
  - **manifests** (what to install where)
  - **overlays** (machine / project / OS / profile specifics)
  - **templates** (e.g. `.gitconfig.j2`, `cursor_command.md.j2`)
  - optional **status registry** (cross-box state)
- Multiple gardens expected: e.g. `work-garden`, `personal-garden`, `teaching-garden`, `lab-garden`.
- Garden can live in Git, local folder, or (later) other backends.

### Profiles
- Named selector bundles: `work`, `personal`, `teaching`, `phd`.
- Profiles decide **what** gets installed and **where** (which beds, which overlays apply).

### Box
- A **box** = machine identity: a stable **box ID** (see below), plus OS/arch, optional tags (`laptop`, `desktop`, `workstation`, `airgapped`).
- A box can have local overrides that never leave that machine.

**Box identity (decided):**
- **Default:** hostname.
- **Override:** allowed via local config (e.g. `~/.config/ivy/ivy.local.yaml` or a dedicated box config). User can set an explicit box ID.
- **Collision:** if a collision is detected (e.g. another box already registered the same ID in the status registry), append a short random suffix to the box ID so this machine gets a unique ID. That avoids VM / clone collisions.
- **Persistence:** store the final box ID in **`~/.config/ivy/box_id`** (one file, one line or one value). Ivy reads this to know “this box”; on first run (or when missing), compute from hostname + override + collision check and write it. Do not rely only on hostname at runtime so that override and suffix are stable.

### Project
- Detected context: repo root, tags, per-project overlays.
- Used for project-local beds (e.g. `.cursor/commands/`, `AGENTS.md` in that repo).

### Configuration Layering (precedence: last wins)
- **global** < **garden** < **profile** < **platform** < **box** < **project** < **CLI**
- Ensures one clear precedence even in v0; local overrides live in e.g. `ivy.local.yaml` (never committed).

### Canon, garden, and beds (bidirectional)
- **Canon** = the repo (Git or something else) — source of truth for the garden’s content. We do not call the canon a “garden” or “mirror.”
- **Garden** = the content package (assets, manifests, overlays). You have a local garden (e.g. a clone of the canon). Gardens stay “gardens.”
- **Beds** = the places on the local box where Ivy deploys: projects, `.cursor/`, `~/.codex/`, etc. We do not call these “mirrors.”
- For each artifact:
  - **source**: one path in the garden (the authoritative copy for that artifact)
  - **beds**: one or more paths on the local box where that artifact is deployed
  - **direction**: `one_way` (garden → beds) or `two_way` (source ↔ beds, and source lives in canon so push = source → canon)
  - **conflict_policy**: how to handle source vs bed both changed
- Editing the source is recommended; editing a bed is supported and must be safe (promote bed → source → commit → push).

### Beds
- A **bed** is a directory or project that has been registered with Ivy so it is controlled by Ivy (a place where Ivy deploys and, if configured, syncs to/from).
- From inside that directory you run **`ivy init bed`**. Ivy writes **`.ivy/bed.yaml`** in the project root (Cut 001). That file is the bed registration; Ivy does not mix bed config into the repo’s main `ivy.yaml` unless explicitly intended. Bed metadata stays **isolated and removable** (delete `.ivy/` to unregister the bed).
- A bed is a location on the local box that has opted in and been registered; artifact config says which sources deploy to which beds (or to paths under them).
- Use case: you `cd` into a project, run `ivy init bed`, and from then on that project is a bed — Ivy can deploy Cursor commands, AGENTS.md, etc. there. Project-level overrides (garden/profile, paths) can live in a separate config if needed; bed identity lives in `.ivy/bed.yaml`.

---

## 3. Installation & Distribution

### Where the Ivy tool is installed (best practice)

- **Install once, globally or per-user** — not into each project.
- **uv:** `uv tool install ivy` (or from repo: `uv tool install .`) so `ivy` is on your PATH. Run from any directory: `ivy sync`, `ivy status`.
- **Why global:** Ivy syncs *from* a garden *to* many beds (Cursor, Codex, multiple projects, home dir). You run her from the garden, from a project, or from home; she’s a user-level CLI, not a project dependency.
- **Alternative for one-off / no install:** `uvx ivy sync` runs without installing.

So: **tool** = one install (global venv / uv tools). **Assets** = what gets synced *into* projects and other beds.

### Other install methods (v1 or later)
- **Python:** pipx, pip, poetry/rye.
- **System:** Homebrew (Mac), Scoop (Windows), apt/dnf/pacman (Linux), Nix.
- **No-install:** curl|bash bootstrapper; single binary (e.g. PyInstaller) for Windows.
- Recommendation: **uv + pipx + uvx** in v1; brew/scoop once adoption grows.

### Project-level config (optional)

- A directory becomes a **bed** when you run **`ivy init bed`** there (§2 Beds). That creates **`.ivy/bed.yaml`** in the project root (Cut 001); we do not write bed registration into the repo’s main `ivy.yaml`.
- When you run Ivy in that project (or pass `--project /path/to/repo`), Ivy reads `.ivy/bed.yaml` and any project-level config. Project config can:
  - Override **where** certain artifacts go for this project (e.g. a different Cursor commands path).
  - Pin which **garden** or **profile** applies to this repo.
  - Add project-specific beds (e.g. “this repo’s `AGENTS.md` is a bed for source X”).
- Layering: project config is one layer in the precedence chain (global < garden < … < **project** < CLI). So garden defines the default; project can direct or narrow for that repo.

---

## 4. Sources (Where Ivy Pulls From)

### v1
- **Git** (local clone or remote)
- **Local folder** (including Obsidian vault path)
- **zip/tar artifact** (pinned releases)

### v2+
- Obsidian Sync *indirectly* (Ivy points at vault folder; Obsidian Sync keeps it updated)
- S3 / GCS (asset bundles)
- HTTP (download with checksum)
- GitHub releases (pinned artifacts)

**Important:** Support **multiple gardens** (e.g. work + personal) from the start in the model; implementation can phase.

---

## 5. Beds (Where Ivy Installs To)

- **cursor_commands** → `.cursor/commands/`
- **codex_prompts** → `~/.codex/prompts/` (or standardized path)
- **obsidian_templates** → `<vault>/.obsidian/templates/`
- **repo_templates** → `.github/` (PR/issue templates, etc.)
- **shell_fragments** → `~/.config/ivy/fragments/` + optional append/include
- **env / .env** — Project (or global) `.env` produced from a template; variable values resolved at sync time from secret backend, env allowlist, or gitignored local file (§9). No secrets in the garden.

Beds should support:
- **copy** (default), **symlink**, or **hardlink** (platform-aware). Symlink is opt-in per bed or artifact; copy is the default for safety and portability.
- Merge strategies for directories
- File collision rules
- Backup/rollback

---

## 6. What Ivy Can Sync (Content Categories)

### Dev / editor tooling
- Cursor: `.cursor/commands/`
- VS Code: snippets, settings
- JetBrains: live templates
- Neovim/LazyVim configs
- Zed editor tasks

### LLM / agent workflows
- Codex prompt packs
- Claude prompt packs
- Cursor rules + project "modes"
- Lily/agent prompt libraries
- "Golden rules" docs, PR templates, issue templates

### Shell + system
- `.zshrc` / `.bashrc` fragments
- gitconfig + global ignore
- SSH config (templated + secrets handled carefully)
- **.env** — Template plus value resolution at sync time (secret backend, env allowlist, or gitignored local file); see §9.
- justfiles / task runners
- Dotfile fragments (without becoming a full dotfile manager)

### Knowledge + writing
- Obsidian vault bundles (templates, snippets, hotkeys, plugins list)
- LaTeX templates (class/professional report frameworks)
- Reference checklists and rubrics
- Starter kits for new projects

### Arbitrary
- "Put this file here"
- "Render this template into that file"
- "Fetch this remote thing and pin version"
- "Symlink or copy depending on platform"

---

## 7. Ivy Pipeline (Per Item)

1. **select** — based on context (OS, hostname, project tags, profile)
2. **render** — template variables (Jinja2)
3. **validate** — linting, schema, checksums, constraints
4. **plan** — diff against current filesystem state
5. **apply** — copy/symlink, backup, atomic writes
6. **report** — what changed

Always support: `--dry-run`, `--explain` (why each item was selected), `--diff`.

---

## 8. Templating & Variables

- **Template engine:** Jinja2 (practical); optionally "simple replace" mode later for safety.
- **Variable sources:**
  - Context: `os`, `arch`, `hostname`, `username`, `home`, `repo_root`
  - Config: `profiles`, `paths`, `tooling`, `vault_path`
  - Environment variables (explicit allowlist only)
  - **Resolved secrets** — Placeholders filled at sync time from a secret backend (1Password, Bitwarden, keychain) or from a gitignored local file (§9). Never stored in the garden.

---

## 9. Secrets & value resolution

### Rule
- **Ivy never stores plaintext secrets.** She is not the system of record (not a vault). API keys, tokens, and passwords live in 1Password, Bitwarden, OS keychain, or similar.

### In scope: resolve, don’t store
- **Template placeholders at sync time** — When rendering a template (e.g. config file, .env), Ivy resolves placeholders by calling a secret backend (read-only), reading from an explicit env allowlist, or reading from a gitignored local file (e.g. `~/.config/ivy/secrets.local` or per-project `.env.local`). The garden only holds the *shape* (which keys exist), not the values.
- **Integrations:** 1Password CLI, Bitwarden, OS keychain; optionally age/sops encrypted files in the garden (Ivy decrypts at sync time with a key that never goes in the garden).
- **.env as a bed** — A manifest can say “produce this project’s `.env` from template X, resolving each variable from allowed sources.” Ivy writes the result into the project. Same pattern for other “fill in values” files (e.g. app config with API key placeholders).

### Out of scope
- Ivy as the place that *stores* or *creates* secrets.
- Executing arbitrary code from the garden.

If we don’t define this, Ivy will eventually hurt users. The above keeps “secret manager” in the “Ivy is NOT” list (she’s not the vault) while making “resolve secrets when syncing” and “.env management” first-class, scoped features.

---

## 10. Bidirectional Sync & Git

### Commands
- **ivy pull** — `git pull --ff-only` (canon → garden) + apply to beds
- **ivy push** — collect changes from beds → update source in garden. By default Ivy does **not** commit or push to canon; the user runs `git commit` and `git push` themselves (or uses an explicit opt-in such as `ivy push --commit` if we add it). No auto-commit by default.
- **ivy sync** — configurable: typically push then pull then apply
- **ivy watch** — (later) watch filesystem; optional auto-pull; debounced

### Safety
- Never auto-force-push
- Always check working tree cleanliness before pull/push
- Optional dedicated branch (e.g. `ivy-state`) for box status or Ivy-managed commits
- If local bed dirty → skip + warn
- If Git working tree dirty → skip (no silent overwrite)

### Conflict handling (per artifact)
- **Default policy: prompt** — super cautious first: stop, show clean diff, offer choices (keep bed / keep source / open merge tool / stash bed + apply source). No automatic resolution by default. Policy is **configurable** per artifact or globally: **prompt** (default), **abort**, **source wins**, **bed wins**, **merge** (where applicable, e.g. AGENTS.md). We can relax defaults later.
- Record audit log when user resolves.

### Automatic pulls ("before I sit down")
- **ivy auto-install** — installs login hook, optional shell hook, optional scheduled task (Windows), optional LaunchAgent (macOS).
- Runs `ivy pull --quiet` with same safety rules (no overwrite of dirty state).
- **ivy watch --auto-pull** (later): periodic poll/fetch; if remote advanced and clean → pull + apply; if local dirty → alert/pause.

---

## 11. TUI & Dashboard

### Technology
- **Textual-based TUI** (keyboard-first, cross-platform, dashboard feel; later web mode possible).

### Screens
1. **Dashboard** — Garden(s) clean/dirty, last pull/push; this box (box ID, profile, active projects); per-artifact status (✅ in sync / ⚠️ drifted / ❌ missing / conflict); Git (remote ahead, working tree, last sync).
2. **Artifact detail** — For one artifact: source path, beds with status; actions: [P] Promote bed → source, [A] Apply source → bed, [D] View diff, [M] Merge, [B] Back.
3. **Wizard** — Add new mapping: select source file, add beds (e.g. "Auto-detect AGENTS.md in projects?"), direction (one-way / two-way), conflict policy. Writes config for you.

### Cross-box status (optional)
- Each box writes `status/<box_id>.json` (e.g. last_sync, artifact status), where `box_id` is the resolved value from `~/.config/ivy/box_id` (see §2 Box identity).
- Stored in Git (e.g. `ivy-state` branch or subdir); no server.
- Dashboard can show: e.g. `platinumplatypus ✅ clean`, `macbook-pro ⚠️ agents_doc drift`, `office-linux ❌ git dirty`.

### Command
- **ivy ui** — launch TUI dashboard + wizard.

---

## 12. Configuration (Keep It Minimal)

- **Not** a 300-line YAML monster.
- **Global / shared:** e.g. `garden/ivy.yaml` (what the garden contains: beds, items, selectors).
- **Local (never committed):** e.g. `~/.config/ivy/ivy.local.yaml` or `ivy.local.yaml` — garden paths, default profile, box-specific paths (e.g. vault_path).
- **Multi-garden registry:** e.g. `~/.config/ivy/ivy.yaml` — list of gardens (git remote or local path), default profile per box, box tags.

Example minimal schema (conceptual):

```yaml
garden:
  path: ~/.ivy/gardens/work

artifacts:
  - name: agents_doc
    source: docs/AGENTS.md
    beds:
      - ~/projects/chrona/AGENTS.md
      - ~/projects/lily/AGENTS.md
    direction: two_way
    conflict_policy: prompt

beds:
  - name: cursor_commands
    src: assets/cursor/
    dest: "{{ project_root }}/.cursor/commands"
    direction: one_way
```

---

## 13. CLI Surface

### Core
- **ivy sync** — plan + apply (and optionally push then pull then apply)
- **ivy plan** — dry-run with diff
- **ivy status** — what's installed, drift, conflicts, last sync
- **ivy doctor** — diagnose common problems

### Setup / growth
- **ivy init** — create Garden skeleton (canon/garden layout).
- **ivy init bed** — run from inside a directory or project to register it as a **bed**. Writes **`.ivy/bed.yaml`** in that directory (Cut 001). Bed metadata is isolated and removable; we do not mix it into the repo’s main `ivy.yaml` unless explicitly intended. After that, Ivy can sync to this location.
- **ivy add item ...** — (optional sugar)
- **ivy contexts** — show detected context (hostname, os, profile, project)

### Bidirectional
- **ivy pull** — pull and apply
- **ivy push** — collect changes from beds, update source, commit, push to canon
- **ivy watch** — (later) file watcher + optional auto-pull

### UI
- **ivy ui** — launch TUI dashboard + wizard

### Power-user flags
- `--profile work`, `--garden work`, `--project .`, `--dry-run`, `--only cursor_commands`, `--explain`
- **ivy status --boxes** — (later) read cross-box registry

---

## 14. Ship Cuts (Phased Delivery)

**North star:** Multi-garden + profiles + cross-box; not all on day one. *"Architect for B, implement A first."*

### Ship Cut 001 — Local deterministic sync
- uv-installable CLI; single Garden (or minimal multi-garden shape).
- **ivy init** (Garden skeleton), **ivy init bed** (register a directory as a bed), **ivy sync**, **ivy plan**, **ivy status**.
- **Bed registration (Cut 001):** `ivy init bed` writes **`.ivy/bed.yaml`** in the project root only. Bed metadata is isolated and removable; we do not mix it into the repo’s main `ivy.yaml`.
- Git garden support; `--ff-only` pull behavior.
- Layered config: at least global + machine + project; beds registered via `ivy init bed`.
- Two beds: **Cursor commands** + **Codex** (and/or one-way "docs" e.g. AGENTS.md).
- No bidirectional promotion, no auto-pull, no cross-box dashboard yet; data structures designed for them.

### Ship Cut 002 — Bidirectional for mapped artifacts
- Artifact mapping: source ↔ beds.
- Drift detection (source changed vs bed changed).
- **ivy push**, **ivy pull**; conflict policy (prompt / abort / source wins / bed wins).
- Safe Git guards (clean working tree checks).
- Optional: profiles + packs, templating, Obsidian vault as bed/source, **ivy status** drift refinement.

### Ship Cut 003 — Cross-box status (no servers)
- Each box writes `status/<box_id>.json` (box_id from `~/.config/ivy/box_id`); commit to e.g. `ivy-state` branch on push.
- **ivy status --boxes** reads registry; TUI shows multi-box health.
- Optional: secrets integration, remote sources (release artifacts, HTTP with checksum), plugin beds.

### Ship Cut 004 — Auto-pull / watch
- **ivy watch** (file watcher + debounce); auto-pull polling.
- OS integration: macOS LaunchAgent, Windows Task Scheduler, Linux systemd user service.
- **ivy auto-install** for login/shell/scheduled hooks.
- Strict safety: never overwrite dirty beds; never pull into dirty working tree.

### Ship Cut 005 — TUI wizard + dashboards
- **ivy ui**: dashboard, artifact detail view, wizard to add mappings and beds, conflict resolution UX.

---

## 15. Garden Layout (Proposal)

```
ivy-garden/
  ivy.yaml                 # global config
  assets/
    cursor/commands/
    codex/prompts/
    obsidian/templates/
    git/
  overlays/
    platform/
      macos.yaml, windows.yaml, linux.yaml
    machines/
      platinumplatypus.yaml, macbook-pro.yaml
    profiles/
      work.yaml, personal.yaml, teaching.yaml
    projects/
      chrona-network.yaml, lily.yaml
  templates/
    .gitconfig.j2, cursor_command.md.j2
  manifests/
    base.yaml, llm.yaml, writing.yaml
```

Multiple garden roots possible, e.g. `~/.ivy/gardens/work`, `~/.ivy/gardens/personal`.

---

## 16. Drift Detection Engine

- Per file: content hash, last_applied hash, origin (source vs bed), last_modified.
- Compare: source vs bed, bed vs last_applied, source vs last_applied.
- Outcomes: bed-only edits, source-only edits, true conflicts, no-op.

### Where does last_applied live?

To know *direction* of drift (source changed vs bed changed vs both), Ivy must remember what it last wrote to each bed. That is **last_applied** (e.g. hash of the content last applied). It has to live somewhere:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Local state file** | `~/.config/ivy/state.json` (or per-garden under `~/.config/ivy/`) | One place; machine-specific; not in canon; auditable | One file to manage; must survive Ivy upgrades |
| **Sidecar files** | Per-bed metadata (e.g. `.ivy-applied.json` next to deployed files) | Distributed with the bed; no global state | Pollutes beds; many files; some beds are dirs (e.g. `.cursor/commands/`) not single files |
| **Stored in garden** | e.g. `state/<box_id>.json` in the garden repo | Versioned with garden | **Dangerous**: machine state in canon; merge conflicts; different boxes overwrite each other |
| **Derived purely from hashes** | Don’t store last_applied; only compare current source hash to current bed hash | No extra state; stateless | Cannot distinguish “source changed” from “bed changed” when both differ — so you lose conflict direction and safe prompts |

**Decision:** **Local state file.** Use a single state file (e.g. `~/.config/ivy/state.json` or `~/.config/ivy/<garden-id>.json`) that records, per artifact/bed path, the last_applied hash (and optionally origin, last_modified). Machine-specific, not in the garden, one place to back up or reset. Do not store last_applied in the garden. Do not rely on “derived only” if we want bidirectional semantics and conflict direction.

---

## 17. Obsidian

- Ivy does **not** implement Obsidian Sync.
- Ivy treats the Obsidian vault as a **source folder** or **bed** (e.g. install templates into vault). If Obsidian Sync keeps the vault in sync, Ivy benefits.
- Ivy can manage "portable Obsidian templates/plugins config packs" by installing into the vault.

---

## 18. Capability Packs (Later)

- Named bundles: e.g. `pack: llm-writing`, `pack: python-dev`, `pack: research-notes`, `pack: gt-teaching`.
- Each pack installs a coherent set of assets across tools.
- **ivy sync --pack python-dev**, **ivy sync --pack research-notes**.
- Turns Ivy into "identity provisioning for your workflow."

---

# Decisions (critical five)

The five that most shape the product — **decided**:

1. **Default: copy (not symlink).** Symlink is opt-in per bed or artifact. Copy is safe, portable, and works everywhere; drift detection and promotion handle bidirectional.
2. **Auto-commit is off by default.** `ivy push` updates the source in the garden working tree; the user runs `git commit` and `git push` themselves (or an explicit opt-in e.g. `ivy push --commit` if we add it). No commit without explicit user action.
3. **Default conflict policy: prompt (super cautious).** Stop, show diff, offer choices. Configurable per artifact or globally to **abort**, **source wins**, **bed wins**, or **merge**. We can relax defaults later.
4. **Engine first, CLI usage.** Build the core engine and CLI stable; TUI comes later as a layer on top.
5. **Scope will be big eventually; grow slowly.** Ship narrow (Cursor, Codex, a few doc types) first. Scope grows only in **defined ship cuts**, not ad hoc — so “big eventually” stays intentional.

---

# Open Questions

Decide these to lock scope, safety, and UX. Everything else can evolve.

---

## Scope & identity

1. **What is Ivy explicitly NOT?**
   **Decided** — See §1: Ivy is not a secret vault (she resolves secrets when syncing); she may manage `.zshrc` and arbitrary configured paths; she does not auto-run scripts from gardens. Boundary: "distributes declarative artifacts only, no arbitrary code execution."

2. **Strict scope vs ambitious scope?**
   **Decided** — See Decisions (critical five) #5: scope big eventually, grow slowly; scope grows only in defined ship cuts.

3. **Disciplined tool vs magical companion?**
   **Decided** — A) Disciplined infrastructure tool. See §1 “Default stance (intentional)”: conservative defaults, automation opt-in; tone is explicit, not accidental.

---

## Safety & defaults

4. **Default: copy or symlink?**
   **Decided** — Copy. See Decisions (critical five) #1.

5. **Does Ivy auto-commit by default?**
   **Decided** — No. See Decisions (critical five) #2 and §10 (ivy push).

6. **How cautious is default conflict policy?**
   **Decided** — Prompt (super cautious); configurable. See Decisions (critical five) #3 and §10 Conflict handling.

7. **Overwrite without confirmation?**
   When does Ivy overwrite (dirty bed, dirty Git)? Never without explicit user action, or allow opt-in automation?

---

## Git & state

8. **Git strategy:**
   One branch per garden? Separate "state branch" for box status (`ivy-state`)? Commit style (Ivy-generated vs user)? Signed commits? Standardized auto-commit messages?

9. **Box identity:**
   **Decided** — See §2 Box: default hostname; override via local config; append short random suffix on collision; store final box ID in `~/.config/ivy/box_id`. Resolved once and persisted so VMs/clones get distinct IDs.

---

## Performance & scale

10. **State and hashing:**
    **Decided** — See §16: last_applied lives in a **local state file** (e.g. `~/.config/ivy/state.json` or per-garden). Not in the garden; not sidecars; not derived-only. Hash + state file for drift direction and conflict semantics.

---

## Platform & security

11. **Permissions and cross-platform:**
    Windows path separators, NTFS vs POSIX, executable bits, case sensitivity, long path limits, symlink privileges on Windows. Lowest common denominator vs platform-specific adapters?

12. **Security model:**
    Compromised garden repo? Malicious file writing to `~/.ssh/config`? Auto-pull overwriting something sensitive? Path allowlist? Optional "safe mode"? Explicit opt-in for sensitive beds?

---

## Build order & audience

13. **Engine-first or UI-first?**
    **Decided** — Engine first, CLI usage. See Decisions (critical five) #4.

14. **If open source:**
    Config syntax for humans or power users only? Document like Terraform (declarative, modules) or like a dotfile manager (friendly, copy-paste)? Tone and UX for devs, AI workflow people, researchers, power note-takers.

---

## Summary of "critical five"

All five are **decided**; see **Decisions (critical five)** above.

1. Default: **copy** (symlink opt-in).
2. **Auto-commit: off by default** (ivy push updates working tree only; user commits).
3. Default conflict policy: **prompt** (super cautious); configurable.
4. **Engine first, CLI**; TUI later.
5. **Scope: big eventually, grow slowly** — only in defined ship cuts.

---

*Source: ideas/chats/initial_ideas.html (chat export). Official copy: docs/FEATURES_PLAN.md. Last organized: 2025-02-20.*
