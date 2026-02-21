
## Ivy — Guiding Principles

Ivy is a distributed capability sync engine.
She exists to keep workflows consistent across projects and machines — safely, deterministically, and transparently.

These principles guide all architectural and implementation decisions.

---

## 1. Declarative, Not Imperative

Ivy distributes **declarative artifacts**.

She:

* Copies files
* Renders templates
* Resolves values
* Detects drift
* Applies deterministic changes

She does **not**:

* Execute arbitrary scripts from gardens
* Run user-defined post-sync commands
* Act as a deployment orchestrator

The garden describes *what should exist*.
Ivy makes reality match the description.

---

## 2. Garden Is Source of Truth

The canon (Git-backed garden) is authoritative.

* The garden holds the source for artifacts.
* Targets are deployments of those artifacts.
* In two-way mode, targets may promote changes back to the garden — but the garden remains canonical.

Project copies are **derived artifacts**, not independent sources.

---

## 3. Copy by Default

Default behavior is **copy**, not symlink.

Copy:

* Is portable across platforms
* Works on Windows without special permissions
* Avoids accidental shared state
* Keeps drift detection explicit

Symlink or hardlink may be supported as opt-in modes per artifact or target.

---

## 4. Conservative by Default

Ivy defaults are intentionally cautious.

* No auto-commit without explicit configuration
* No silent overwrite of dirty targets
* No force pushes
* No implicit merges

When conflicts occur, Ivy:

* Stops
* Shows a diff
* Prompts for resolution

Automation is opt-in. Safety is default.

---

## 5. Explicit Git Behavior

Ivy runs Git commands intentionally and transparently.

* `git pull --ff-only` is used to avoid merge commits.
* `ivy push` is the command family for bed->garden promotion and (when enabled) git publishing.
* `ivy push` default behavior: promotes content to the garden working tree only.
* Explicit publish flags (`ivy push --commit --push`) run `git add`, `git commit`, and `git push` (never force push).
* Git working tree cleanliness is checked before pull or push.
* Ivy never rewrites history.

Git is used as:

* Change history
* Cross-box propagation layer
* Optional status registry

Git is not abstracted away; it is respected.

---

## 6. Layered, Deterministic Configuration

Configuration precedence is fixed and explicit:

```
global < garden < profile < platform < box < project < CLI
```

Later layers override earlier ones.

Config merges are deterministic and testable.

No hidden magic. No implicit fallbacks.

---

## 7. Bidirectional Is Explicit

One-way and two-way artifacts are explicitly configured.

* `one_way`: garden → targets
* `two_way`: source ↔ targets

Bidirectional sync is:

* Explicitly declared per artifact
* Drift-detected
* Conflict-aware
* Never silently resolved

Editing targets is supported — but always safely promoted back to source before canon update.

---

## 8. Secrets Are Resolved, Not Stored

Ivy is not a vault.

* She does not store plaintext secrets in the garden.
* She does not generate or manage secrets.
* She resolves placeholders at sync time from approved backends (1Password, Bitwarden, OS keychain, env allowlist, gitignored local file).

The garden contains shape, not sensitive data.

---

## 9. Engine First, Interface Second

The core sync engine must be correct and stable before any TUI.

* CLI is primary interface.
* TUI is a thin layer over engine APIs.
* Watch mode is convenience, not correctness.

If the engine is correct, all interfaces remain thin.

---

## 10. Multi-Box by Design, Single-Box First

Ivy is designed for:

* Multiple gardens
* Multiple profiles
* Multiple boxes
* Cross-box visibility

But she ships in slices.

Architecture supports future expansion; implementation grows in defined ship cuts.

---

## 11. No Surprises

Ivy must be predictable.

Running the same command in the same state must produce the same result.

Output must be explainable:

* Why this artifact?
* Why this target?
* Why this change?

`--dry-run`, `--diff`, and `--explain` are first-class.

---

## 12. Small Core, Composable Growth

The core engine should remain small and focused.

New capabilities:

* Add targets
* Add selectors
* Add backends
* Add UI

They do not bloat the core.

Complexity is layered, not entangled.

---

# Ivy’s Personality

Ivy is:

* Quiet
* Disciplined
* Conservative
* Deterministic
* Cross-machine
* Context-aware

She spreads capabilities like ivy spreads on stone — steadily, predictably, and without drama.

