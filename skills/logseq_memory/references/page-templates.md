# Page Templates: Skeletons for Logseq Memory Surfaces

All pages in Logseq 2.0 use **flat colon titles** (e.g. `projects: <project>`, `<project>: <branch>`, `agent: core`). Never use slashes.

### Visual Ergonomics Standard:
1. **Consistent Header Icons**: Always include standard icons for instant visual recognition across pages.
2. **Collapsed Reference Sections**: At page creation or update, set `:block/collapsed? true` on reference/background headings (`System Overview`, `System Architecture`, `State & Config`, `Operational Runbook`, `Engineering Conventions`, `Sharp Edges`) so pages open cleanly. Keep `Active Branches & Worktrees` expanded (`:block/collapsed? false`).
3. **Generous Spacing**: Add blank lines between top-level section blocks and avoid cramping inline links and badges.

---

## 1. Branch Deep-Dive (`<project>: <branch>`)

Written as a **Senior Engineer / Tech Lead Feature Design Doc / RFC**. Provides comprehensive technical depth, clear runtime execution flow, concrete schemas, ADR trade-offs, and verification commands.

```markdown
- ## 🎯 Context, Problem & Goals
  - **Problem Statement**: Clear, authoritative description of the bottleneck, bug, or missing capability prompting this branch.
  - **Prior Limitation**: How the system behaved previously and why that behavior was insufficient or error-prone.
  - **Explicit Goals**:
    - Deliver concrete capability X with deterministic runtime behavior.
    - Guarantee backwards compatibility with subsystem Y.
  - **Non-Goals**: Explicitly out-of-scope items to prevent scope creep.

- ## 🏗️ Technical Design & End-to-End Flow
  - **Runtime Execution Flow**:
    1. Caller triggers entry point function `executeAction()` in `src/core/runner.ts`.
    2. Subsystem validates inbound payload against schema `ActionPayloadSchema` using Zod.
    3. Storage adapter dispatches batch write to disk, acquiring file lock via `fs.promises.flock`.
    4. Event bus emits `action:completed` notification to connected listeners.
  - **Data Models, Schemas & Interfaces**:
    - `interface SessionConfig { id: string; graph: string; ttlMs: number; mode: 'strict' | 'relaxed'; }`
    - Config keys: `SESSION_TIMEOUT_MS` (default: `600000`), `SYNC_CONCURRENCY` (default: `4`).
  - **Component & File Touchpoints**:
    - `src/core/runner.ts`: Orchestrates execution lifecycle and handles process signal trapping.
    - `src/storage/db.ts`: Manages atomic state persistence and transaction boundaries.
    - `test/runner.test.ts`: Unit and regression test suite for execution failures.

- ## ⚖️ Key Engineering Decisions & Trade-offs
  - **Decision: In-Place Block Updates vs Append-Only Log**:
    - **Rejected Alternatives**: Appending timestamped markdown chunks to page bottoms.
    - **Rationale**: Logseq outliner graphs become unreadable when duplicate headings accumulate; in-place replacement preserves outline hierarchy and `:block/refs` link graphs.
    - **Accepted Trade-off**: Requires a two-step query-then-mutate CLI interaction, increasing mutation latency by ~150ms per section.
  - **Decision: Pure Skill Invocation vs Background Daemon**:
    - **Rejected Alternatives**: Long-running Node.js daemon with local HTTP server.
    - **Rationale**: Eliminates daemon port conflicts, orphan process leaks, and external runtime dependencies across different developer machines.
    - **Accepted Trade-off**: Each CLI invocation spawns a fresh process rather than reusing an open connection pool.

- ## 🧪 Verification, Testing & Operational Usage
  - **Verification Commands**:
    - `pnpm test`: Runs entire unit and integration test suite.
    - `node test/graph-lint.mjs`: Validates all Logseq graph invariants and link integrity.
  - **Test Suite Coverage**:
    - `test/unit/runner.test.ts`: Verifies edge cases for detached HEAD and worktree paths.
    - `test/e2e/sync.test.ts`: End-to-end multi-turn simulation asserting zero property drawer pollution.
  - **Operational Usage & Config Examples**:
    - Run manually: `./bin/run-check --graph "logseq-sync" --verbose`
  - **Failure Modes & Fallbacks**:
    - If CLI binary is missing, falls back to `~/.local/bin/logseq` before failing gracefully with exit code 0 to protect git commit workflows.

- ## 🚧 Status, Open Questions & Next Steps
  - **Completed**:
    - [x] Schema migration and test harness configuration.
    - [x] In-place section replacement routine verified with zero link degradation.
  - **Remaining**:
    - [ ] Add benchmark script for 10,000 block pages.
  - **Open Questions (#needs-human)**:
    - Should cache invalidation happen on git checkout or on initial orient? Awaiting benchmark comparison.
```

---

## 2. Evergreen Project Page (`projects: <project>`)

Written as a **Senior Engineer / Tech Lead System Architecture & Runbook**. Central technical reference for the repository across all branches and worktrees.

```markdown
- ## 🧭 System Overview & Design Philosophy
  - **System Purpose**: Authoritative 2–4 sentence summary of what this system does, its primary business/technical problem, and its role in the larger engineering ecosystem.
  - **Core Philosophy**: Guiding principles (e.g. human-first readability, zero background daemons, crash-early invariants, stateless CLI interactions).
  - **Primary Technology Choices**:
    - Runtime: Node.js 20+ ESM / TypeScript 5.4.
    - Transport: Native Logseq 2.0 CLI (`logseq`) targeting local Datascript DB.
    - Storage: SQLite-backed Logseq graph storage with Git synchronization.

- ## 🏗️ System Architecture & Module Map
  - **Directory & Subsystem Map**:
    - `src/core/`: Central state machine, task dispatcher, and lifecycle orchestration.
    - `src/storage/`: Database adapters, query compilers, and transaction managers.
    - `src/cli/`: Command-line parsing, argument validation, and output formatters.
    - `references/`: Human and agent reference manuals and writing taste guidelines.
  - **End-to-End Request/Data Flow**:
    1. Agent invokes entry script or CLI trigger with target parameters.
    2. Subsystem resolves project root via `git rev-parse --git-common-dir` and active branch.
    3. Storage module queries Datascript database via CLI transport for existing entity tree.
    4. Mutator applies in-place block updates preserving `:block/refs` link metadata.
    5. Formatter verifies markdown invariants and outputs human-readable confirmation.

- ## 💾 State, Config & Storage Layout
  - **State Persistence**:
    - Logseq graph database (`~/.logseq/graphs/<graph-name>`) storing native Datascript entities.
    - Active graph preference stored in `~/.config/logseq_memory/graph` (fallback `~/.config/logseq-memory/graph`).
  - **Configuration Schemas & Environment Keys**:
    - `LOGSEQ_GRAPH`: Overrides default graph selection.
    - `LOGSEQ_CLI`: Custom path to logseq CLI binary (defaults to `logseq` or `~/.local/bin/logseq`).
  - **Storage Paths & File Formats**:
    - `pages/*.md`: Markdown source files backed by Logseq DB index.
    - `journals/*.md`: Daily journal records organized by date.

- ## 🛠️ Operational Runbook (Build, Run, Test, Debug)
  - **Build & Dependency Installation**:
    - `pnpm install`: Installs workspace dependencies.
    - `pnpm build`: Compiles TypeScript source to `dist/`.
  - **Running Locally & Dev Modes**:
    - `./setup.sh --graph <graph-name>`: Configures graph symlinks across all agent harnesses.
  - **Testing & Verification**:
    - `node test/graph-lint.mjs`: Read-only graph invariant linter.
    - `pnpm test`: Executes Vitest test suite.
  - **Diagnostic & Debugging Procedures**:
    - Inspect page tree: `logseq show --graph "$GRAPH" --page "<page-title>" --level 3 --output json`
    - Verify task query: `logseq query --graph "$GRAPH" --query '[:find (pull ?b [*]) :where [?t :block/name "agent_task"] [?b :block/tags ?t]]'`

- ## 📏 Engineering Conventions & Architectural Invariants
  - **Project-Specific Conventions** *(Strictly specific to this project, not generic Logseq rules!)*:
    - Error Handling: All storage errors must wrap underlying errors with descriptive subsystem context; never swallow exceptions silently.
    - Concurrency Model: Single-writer file locking pattern for local state files; concurrent writes must acquire `.lock` file with exponential backoff.
    - Typing Discipline: Strict TypeScript; no `any` types allowed in public module APIs without explicit Tech Lead sign-off.
    - Logging: Structured JSON logs to stderr; stdout is reserved exclusively for piped machine output.

- ## 🧠 Sharp Edges & Permanent Gotchas
  - **Colon Page Naming**: Logseq 2.0 DB strictly rejects slashes in page titles and renders `[[a/b]]` as broken literal text. All pages MUST use flat colon titles (`projects: <project>`, `<project>: <branch>`).
  - **Link Preservation via `--blocks`**: Updating an existing block with `--content` drops its `:block/refs` link metadata. Any block containing `[[links]]` MUST be created or replaced via `--blocks` or `--blocks-file`.
  - **Git Worktree Resolution**: Sub-agents running inside linked git worktrees must resolve repository identity via `git-common-dir` to prevent creating fragmented project pages.

- ## 🌿 Active Branches & Worktrees
  - [[<project>: <branch-1>]] — 🔄 Feature description (worktree: `/path/to/worktree`)
  - [[<project>: <branch-2>]] — 🔄 Feature description

- ## 🏁 Completed Branches & Architecture History
  - [[<project>: <merged-branch>]] — ✅ Merged to main on YYYY-MM-DD (Architectural milestone description)
```

> **Collapse Policy**: At page creation or update, set `:block/collapsed? true` on:
> - `🧭 System Overview & Design Philosophy`
> - `🏗️ System Architecture & Module Map`
> - `💾 State, Config & Storage Layout`
> - `🛠️ Operational Runbook (Build, Run, Test, Debug)`
> - `📏 Engineering Conventions & Architectural Invariants`
> - `🧠 Sharp Edges & Permanent Gotchas`
>
> **Leave `🌿 Active Branches & Worktrees` expanded** (`:block/collapsed? false`) so active work is immediately visible upon opening the page.

---

## 3. Global Rules (`agent: core`)

Universal developer preferences and agent operating invariants across all repositories.

```markdown
- ## 🤖 Agent Identity & Role
  - **Autonomous Pairing Partner**: High code quality, human-readable explanations, non-destructive mutations across harnesses.
  - **Human-in-the-Loop**: Transparent decision tracking, dual-channel review loops, and zero blocking CLI hangs.

- ## 📐 Global Engineering Conventions
  - **Clean Markdown in Logseq**: Use Markdown headings (H2/H3) and real `[[links]]`. Never create single-child wrapper bullets.
  - **Worktree Discipline**: Resolve project identities via `git-common-dir` so linked worktrees share the canonical project brain.
  - **Status Allowed**: Use native statuses (`todo`, `doing`, `in-review`, `done`, `canceled`). Never use `waiting`.
  - **Light STE Clarity**: Use active voice, unambiguous verbs, and concise phrasing. Sentences may reach 35–40 words when describing complex technical architectures, schemas, and trade-offs.

- ## 🧠 Self-Updating Memory
  - When a user corrects an operating rule or convention, update this page under the relevant heading.
```

---

## 4. Daily Journal Pulse (`<Month> <Day>, <Year>`)

High-priority triage inbox at the top, concise branch pulse at the bottom.

```markdown
🚨 [In Review] `<project>: <branch>`: Question for human? #needs-human
  - **Why**: Context on why this decision is needed.
  - **Option 1**: Description.
  - **Option 2**: Description.

- 🤖 [[Agent Activity]]
  - [[projects: <project-1>]]
    - [[<project-1>: <branch-1>]] — 🔄 Brief description of active work (14:30)
  - [[projects: <project-2>]]
    - [[<project-2>: <branch-2>]] — ✅ Implementation complete, ready for review (15:15)
```

---

## 5. Agent Command Center (`Agent Command Center`)

Cross-project Kanban dashboard with native Logseq 2.0 `/Query` blocks. `🚨 Needs Human Review` sits at the top for immediate visibility.

```markdown
- ## 🚨 Needs Human Review
- #Query
  - (and (task "In Review") (tags [[agent_task]]))

- ## 🔄 Currently Running
- #Query
  - (and (task "Doing") (tags [[agent_task]]))

- ## 📥 Delegation Queue
- #Query
  - (and (task "Todo") (tags [[agent_task]]))
```

> **Construction Rule**: Create the parent block with `--content ""` and `--update-tags '["Query"]'`, then set `--update-properties '{:logseq.property/query "(and (task \"<Status>\") (tags [[agent_task]]))"}'`. Logseq 2.0 DB automatically generates the child query property block.

---

## 6. Lightweight Area Index (`area: <area>`)

For non-git or `.md`-first workspaces (`career`, `masters`, etc.). Keeps `.md` files on disk as the canonical source of truth for prose while giving Logseq a clean cross-workspace control index.

```markdown
- ## 🎯 Focus & Goals
  - Primary objective, target timeline, and non-negotiable constraints for this area.

- ## 🔗 Workspace Map
  - `~/workspace/<area>/README.md`: Master index and execution plan.
  - `~/workspace/<area>/<doc>.md`: 1-line summary of what lives in this file.

- ## 🚧 Open Decisions & Next Actions
  - [ ] Next concrete action item or `#needs-human` decision.
```
