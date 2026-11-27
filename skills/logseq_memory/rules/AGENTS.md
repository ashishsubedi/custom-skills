# Logseq Agent Memory — Universal Cross-Harness Rules & Definition of Done

These rules apply across all workspaces (git repositories and `.md`-first research/planning areas) and agent sessions (Antigravity, OpenCode, Claude Code, Cursor, Codex).
Every agent must treat Logseq memory operations as non-negotiable lifecycle gates with the same strictness as compilation, linting, and type checking.

## 1. Context Discovery & Graph Target
- **Target Graph**: Read graph preference from `~/.config/logseq_memory/graph` (fallback to `~/.config/logseq-memory/graph` or `logseq-sync`). Overridable via `$LOGSEQ_GRAPH`.
- **Git Code Repositories**:
  - Derive `$PROJECT` from:
    ```bash
    basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
    ```
  - Derive `$BRANCH_SLUG` from:
    ```bash
    git branch --show-current | tr '/' '-'
    ```
    (Fallback to worktree directory name if detached HEAD).
  - Canonical pages: `projects: <project>` and `<project>: <branch>`.
- **Non-Git / `.md`-First Areas (e.g. `career`, `thesis`, `Masters`)**:
  - When `git rev-parse` fails (outside a git repo), derive `$AREA` from the lowercased workspace folder name (e.g. `career`, `thesis`, `masters`).
  - If `projects: <area>` already exists in Logseq, orient on it; otherwise use the lightweight **`area: <area>`** surface.
- **Canonical Surfaces**: Flat colon names only: `projects: <project>`, `<project>: <branch>`, `area: <area>`, `agent: core`. Slashes are strictly illegal in Logseq 2.0 page titles.

## 2. Mandatory Lifecycle Gates (Definition of Done)

### Gate 1 — Session Start Orient & Bootstrap (First Turn)
Before modifying code or project/research docs in any workspace:
1. Resolve `$GRAPH` and workspace mode (git `$PROJECT`/`$BRANCH_SLUG` or non-git `$AREA`).
2. Inspect `agent: core` and either `projects: <project>` + `<project>: <branch>` (git mode) or `area: <area>` (area mode; or `projects: <area>` if pre-existing) via `logseq show`.
3. Scan for active agent tasks via targeted Datascript query:
   ```bash
   logseq query --graph "$GRAPH" --query '[:find (pull ?b [:db/id :block/title :block/created-at :block/updated-at {:logseq.property/status [:block/title :db/ident]} {:block/tags [:block/title :block/name]} {:block/page [:block/title :block/name]} {:block/refs [:block/title :block/name]}]) :where [?t :block/name "agent_task"] [?b :block/tags ?t]]'
   ```
4. Check for open review tasks (`#agent_task` + `#needs-human`) or late-answered reviews marked `done` by the human in Logseq (harvest decisions into the branch/area page and clean the prompt). If an open `todo` task matches the current project/area/branch, claim it (`--status doing`).
5. **Bootstrap Invariant**:
   - In git code repos: if `projects: <project>` does not exist or is a shallow stub (< 6 structured sections), inspect the codebase and bootstrap it into a Senior Engineer / Tech Lead System Architecture & Runbook page.
   - In non-git / `.md`-first workspaces: if `area: <area>` (and `projects: <area>`) does not exist, bootstrap the lightweight 3-section `area: <area>` index pointing to canonical `.md` files on disk. Never duplicate full `.md` prose into Logseq.

### Gate 2 — Automatic Progress Sync (Pre-Commit & Pre-Reply Gate)
Treat Logseq memory synchronization with the same strictness as compilation, linting, and type checking:
- **Triggers**: Whenever you complete a feature, fix, or research/planning milestone, make a key decision, execute `git commit`, or are about to finish a working turn:
  1. **Update Branch or Area Page**:
     - Git code repos: sync `<project>: <branch>` in place (5-part RFC).
     - Non-git / `.md`-first areas: sync `area: <area>` in place (3-part lightweight index + links to changed `.md` files; or `<area>: main` / `projects: <area>` if pre-existing).
  2. **Update Today's Daily Journal Pulse**: Under `🤖 [[Agent Activity]]` -> `[[projects: <project>]]` (or `[[area: <area>]]`) on today's Daily Journal page, replace the 1-line pulse:
     `- [[<project>: <branch>]] — <status_icon> <one-sentence description> (<HH:MM>)` (or `- [[area: <area>]] — <status_icon> <one-sentence description> (<HH:MM>)`)
     Keep the journal entry to exactly one line with zero child bullets.
- **Pre-Reply Enforcement**: You MUST execute this sync in the same turn **before** delivering your response to the user. Never wait for the user to remind you.

### Gate 3 — Documentation Standards (Code Repos vs. Lightweight Areas)
Do not write shallow bullet blurbs, and never force software RFC templates onto non-code planning/research areas:

1. **`projects: <project>` (Tech Lead System Architecture & Runbook + Agent Extras)**:
   - `## 🧭 System Overview & Design Philosophy`: System intent, design philosophy, primary technology choices, and architectural boundaries.
   - `## 🏗️ System Architecture & Module Map`: Directory map, subsystem responsibilities, and step-by-step end-to-end request/data flows.
   - `## 💾 State, Config & Storage Layout`: Persistence mechanisms, schema structures, environment keys, and storage paths.
   - `## 🛠️ Operational Runbook (Build, Run, Test, Debug)`: Exact runnable CLI commands for build, dev, test suites, and diagnostic inspection.
   - `## 📏 Engineering Conventions & Architectural Invariants`: Strictly project-specific conventions (e.g. error handling, layering rules, typing discipline). Never copy-paste generic Logseq memory rules here!
   - `## 🧠 Sharp Edges & Permanent Gotchas`: Non-obvious failure modes, race conditions, platform constraints, and performance pitfalls.
   - `## 🌿 Active Branches & Worktrees`: Live index of active branches (`:block/collapsed? false`).
   - `## 🏁 Completed Branches & Architecture History`: Historical log of merged initiatives and architectural evolution.

2. **`<project>: <branch>` (5-Part Tech Lead Feature Design Doc / RFC)**:
   - `## 🎯 Context, Problem & Goals`: Problem statement, prior bottleneck/limitation, explicit goals and non-goals.
   - `## 🏗️ Technical Design & End-to-End Flow`: Step-by-step runtime execution flow, data models / schemas / interfaces, and component touchpoints.
   - `## ⚖️ Key Engineering Decisions & Trade-offs`: ADR-style breakdown (Decision, Rejected Alternatives, Rationale, Accepted Trade-off). Must explain *why*, not repeat *how*.
   - `## 🧪 Verification, Testing & Operational Usage`: Concrete verification commands, automated test suites, configuration examples, and failure modes.
   - `## 🚧 Status, Open Questions & Next Steps`: Completed vs remaining work, and open questions awaiting human input (`#needs-human`).

3. **`area: <area>` (Lightweight 3-Part Index for Non-Git / `.md`-First Workspaces)**:
   - `## 🎯 Focus & Goals`: Current objectives, target dates, and active constraints.
   - `## 🔗 Workspace Map`: File paths and 1-line descriptions of canonical `.md` files on disk (keep `.md` as source of truth; do not copy-paste `.md` prose).
   - `## 🚧 Open Decisions & Next Actions`: Next concrete steps and `#needs-human` questions.

## 3. Privacy Boundary & Scoped Queries
- **Never run unconstrained `logseq list task` across the user's graph.** Personal tasks, reading lists, and private notes are strictly confidential and out-of-scope.
- Always scope task queries to `#agent_task` via Datascript or inspect blocks attached to the active project/branch and today's Daily Journal page.

## 4. Universal Invariant Protection (`agent: core`)
- Never write transient, task-specific notes, branch logs, or code diffs to `agent: core`.
- Only update `agent: core` when the user explicitly provides enduring, cross-project engineering rules, conventions, or developer preferences.

## 5. Clean Logseq 2.0 Invariants
- **No Property Drawers**: Never attach property drawers or keys (`project:`, `branch:`, `slot-key:`) to journal or activity blocks.
- **Real Links via `--blocks` / `--blocks-file`**: Any block containing `[[links]]` must be created or replaced via `--blocks` or `--blocks-file` to preserve `:block/refs` in Logseq's Datascript database. Updating an existing block with `--content` drops links.
- **Flat Colon Titles**: All pages use colon separators (`projects: <project>`, `<project>: <branch>`, `agent: core`). Slashes are illegal in Logseq 2.0 DB titles.
- **In-Place Section Updates**: Locate heading IDs, remove obsolete child blocks, and insert updated child blocks. Never append duplicate section headings.
