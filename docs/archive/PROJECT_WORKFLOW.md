# Ivy — Project workflow (GitHub Projects + story-first)

How we run the project: **story-first, user-facing value**, with tasks as implementation units. Work is tracked in **GitHub Projects (v2)**; agents (or humans) create structured issues and move them through a clear state machine.

---

## 1. Model: Story → Tasks

- **Story** = one user-facing outcome. No tech. Clear “done.”
  - Format: *As a ___ I want ___ So that ___*
  - Acceptance criteria = what “done” means.
- **Tasks** = implementation work under that story. Tech lives here; tasks link to the parent story.

We track **value flow** (stories across the board), not code flow. Tasks are filtered or grouped under stories.

---

## 2. GitHub Project board

Use **GitHub Projects (v2)** (table/kanban), not Classic.

**Suggested name:** e.g. *Ivy Control Room*, *Ivy Work Tracker*.

### Custom fields

| Field           | Type        | Values |
|----------------|-------------|--------|
| **Status**     | Single select | Backlog, Ready, In Progress, Review, Needs Rework, Done, Blocked |
| **Work type**  | Single select | Story, Task, Bug, Research, Design, Infrastructure |
| **Ship cut**   | Single select | Cut 001, Cut 002, Cut 003, Cut 004, Cut 005 *(optional; maps to §14 ship cuts)* |
| **Owner**      | Single select | Agent name or “Human” *(optional for now)* |
| **Effort**     | Single select | XS, S, M, L, XL *(optional)* |

Status is the state machine. Ship cut lets you filter by phase (e.g. “only Cut 001 stories”).

### Labels

- `story` — user-facing value unit
- `task` — implementation unit (child of a story)
- `bug`
- `research`

Stories move across the board; tasks link to parent story (e.g. “Relates to #123”).

### Board columns (Kanban)

- **Backlog** — inventory; not yet committed.
- **Ready** — committed for this slice; next up.
- **In Progress** — currently being worked.
- **Review** — work done; needs verification.
- **Needs Rework** — sent back.
- **Done** — accepted and closed.

Rule: **Ready = commitment.** Don’t put more in Ready than you’re willing to actively ship.

---

## 3. Horizons (what to put on the board)

Three layers of visibility:

| Horizon | Meaning | On the board |
|---------|--------|---------------|
| **Vision Backlog** | All candidate stories (inventory) | In Backlog, or as issues not yet added to project |
| **Committed slice** | Current ship phase: 1–3 stories | Those stories in Ready / In Progress |
| **In motion** | What’s actually being worked | 1 story In Progress (2 max); its tasks executing |

**Practice:**

1. Create **all stories as issues** (inventory).
2. Add only the **next 2–3 stories** to the Project board for the active ship cut.
3. Mark **one** story as **Ready**.
4. **One** story in **In Progress** at a time.

This keeps strategy visible but execution narrow. Agents (or you) see one Ready and one In Progress — not 50 open stories.

---

## 4. Issue format (structured)

Agents and humans use the same schema so the board stays useful.

### Story issue template

```markdown
## Objective
What needs to be built or changed? (User-facing, no tech.)

## Value (As a … I want … So that …)
As a [role], I want [outcome] so that [benefit].

## Scope
- In scope: …
- Out of scope: …

## Acceptance criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Ship cut
Cut 00X (if applicable)

## Dependencies
Links to other issues or “None.”

## Suggested owner
Agent or Human (optional).
```

Stories get label `story` and Work type **Story**. No implementation details in the story body.

### Task issue template

```markdown
## Parent story
Relates to #___

## Objective
What concrete implementation work is done in this task?

## Technical scope
- …
- …

## Acceptance criteria
- [ ] …

## Dependencies
Other tasks or issues, if any.
```

Tasks get label `task` and Work type **Task**; link to parent story.

---

## 5. How work flows

1. **Propose story** (human or agent) → Backlog.
2. **Human approves** decomposition and scope.
3. **Decompose into tasks** (human or agent); create task issues; link to story.
4. **Commit slice:** move 1–3 stories to the board; set one to **Ready**.
5. **Start work:** move one story to **In Progress**; work its tasks.
6. **Tasks done** → story moves to **Review**.
7. **Human verifies** acceptance criteria → story **Done** (or **Needs Rework**).

Stories are the unit of “done.” Tasks are how we get there.

---

## 6. Mapping to Ivy ship cuts

Ivy’s phased delivery is in [FEATURES_PLAN.md §14](FEATURES_PLAN.md). Use the **Ship cut** field (or a label per cut) so you can filter:

- **Cut 001** — Local deterministic sync (CLI, init, init bed, sync, plan, status; Cursor + Codex beds).
- **Cut 002** — Bidirectional (push, pull, drift, conflict policy).
- **Cut 003** — Cross-box status (box_id, status files, no servers).
- **Cut 004** — Auto-pull / watch (ivy watch, OS integration).
- **Cut 005** — TUI wizard + dashboards (ivy ui).

Stories should be written in user-facing terms; the Ship cut ties them to the phase in the spec.

---

## 7. Story inventory (candidate stories)

Below are **user-facing story ideas** you can turn into GitHub issues when you’re ready. They’re phrased as value, not tech. Add to Backlog as inventory; promote to the board per horizons above.

### Cut 001 — Local deterministic sync

- **User can install Ivy and run a single command to get a working garden** so that they can start syncing without manual setup.
- **User can register a project as a bed** so that Ivy knows where to sync and can manage that location explicitly (isolated, removable).
- **User can sync their garden to Cursor and Codex beds** so that slash commands and prompts are available in their projects.
- **User can run a dry-run (plan)** so that they see what would change before applying.
- **User can see current sync status** so that they know what’s deployed and what’s pending.

### Cut 002 — Bidirectional

- **User can push changes from a bed back to the garden** so that edits in one place flow back to the source.
- **User is prompted when garden and bed both changed** so that they can resolve conflicts explicitly (no silent overwrite).
- **User can see drift (source vs bed)** so that they know what’s out of sync.

### Cut 003 — Cross-box status

- **User can see status across their machines** so that they know what’s applied where without running on each box.
- **User has a stable box identity** so that status and state are consistent across reinstalls and renames.

### Cut 004 — Auto-pull / watch

- **User can run a watch mode** so that changes in the garden are reflected in beds without manual sync.
- **User can install Ivy to run on login/schedule** so that beds stay updated without remembering to run sync.

### Cut 005 — TUI

- **User can use a TUI dashboard** so that they can see state, artifacts, and conflicts in one place.
- **User can add mappings and beds through a wizard** so that setup is guided instead of editing YAML by hand.

---

## 8. Autonomy levels (later)

- **Level 1:** Agent creates issues (e.g. via `gh issue create`); human moves cards. Safest.
- **Level 2:** Agent creates issue, adds to project, sets status/owner; when starting work → In Progress; when done → Review; human approves or sends to Needs Rework.
- **Level 3:** Multiple agents generate work, decompose, create sub-issues, track dependencies, move tickets. Only if the workflow above is strict and followed.

Start at Level 1; evolve when the structure feels right.

---

## 9. Checklist: first-time setup

1. Create a GitHub Project (v2).
2. Add custom fields: Status, Work type, Ship cut (optional), Owner (optional).
3. Add labels: `story`, `task`, `bug`, `research`.
4. Create 2–3 story issues from the inventory (use templates); add to board as Backlog.
5. Set one story to Ready; leave In Progress empty until you start.
6. (Optional) Add issue templates in the repo (e.g. `.github/ISSUE_TEMPLATE/story.md`, `task.md`) so `gh issue create` uses them.

Once this is in place, you can let an agent create structured issues and still keep execution narrow (one Ready, one In Progress) and story-first.

---

## 10. Configuring the board via GitHub CLI

If you use **GitHub CLI** (`gh`) and the project is under your user (or an org you admin), you can add custom fields from the terminal.

**One-time: grant project scope**

```bash
gh auth refresh -s project
```

(Approve in the browser when prompted.)

**Get your project number**

```bash
gh project list --owner @me
```

Use the number in the first column (e.g. `1`, `2`) in the commands below. Replace `N` with that number.

**Add custom fields**

```bash
# Status (state machine)
gh project field-create N --owner @me --name "Status" --data-type "SINGLE_SELECT" \
  --single-select-options "Backlog" --single-select-options "Ready" --single-select-options "In Progress" \
  --single-select-options "Review" --single-select-options "Needs Rework" --single-select-options "Done" --single-select-options "Blocked"

# Work type
gh project field-create N --owner @me --name "Work type" --data-type "SINGLE_SELECT" \
  --single-select-options "Story" --single-select-options "Task" --single-select-options "Bug" \
  --single-select-options "Research" --single-select-options "Design" --single-select-options "Infrastructure"

# Ship cut (optional)
gh project field-create N --owner @me --name "Ship cut" --data-type "SINGLE_SELECT" \
  --single-select-options "Cut 001" --single-select-options "Cut 002" --single-select-options "Cut 003" \
  --single-select-options "Cut 004" --single-select-options "Cut 005"
```

**Repo labels** (in the Ivy repo; run from repo root):

```bash
gh label create "story" --color "0E8A16" --description "User-facing value unit"
gh label create "task" --color "1D76DB" --description "Implementation unit under a story"
gh label create "bug" --color "B60205" --description "Bug"
gh label create "research" --color "C2E0C6" --description "Research / spike"
```

*(Use `gh label list` first; skip if a label already exists.)*

**Note:** Board columns (Backlog, Ready, In Progress, etc.) in Projects v2 are usually created automatically from the **Status** field when you add a board view; if your project already has a different layout, add a view and choose “Board” with Status as the column field in the GitHub UI.
