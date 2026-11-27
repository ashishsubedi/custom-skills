---
name: logseq_memory
description: Human-first agent memory, task dispatcher, and cross-harness control center in Logseq 2.0. Use at session start to orient, scan and pick open or delegated tasks to execute (#agent_task) \#delegate, sync active branch narratives and daily journal pulses, escalate review questions (#needs-human), and distill evergreen project knowledge.
---

# Logseq Agent Memory (v2.1 Pure Skill)

> **Prerequisite**: Read the official `logseq-cli` skill first (`~/.agents/skills/logseq-cli/SKILL.md` or `logseq skill show`). This skill uses the official `logseq` CLI directly with zero helper wrappers or background daemons.

Logseq 2.0 (configured to target your active graph, such as `logseq-sync` or `logseq-agent`) serves as a **human-explorable second brain and human-in-the-loop control center** across Antigravity, Claude Code, Cursor, and Codex. The target graph is configured during `./setup.sh` (or overridden via `$LOGSEQ_GRAPH` / `~/.config/logseq_memory/graph`).

Inspired by the best patterns in agent memory (Obsidian's CLI-first skill, Notion's curated memory layer, and Cline's "Stable vs. Active" split), this skill is designed to prevent **Memory Rot**. Agents record curated architecture, decisions, and authoritative feature narratives—never noisy tool telemetry or raw commit diffs.

---

## 1. The Surfaces

All pages use **colon separators** (or canonical dashboard names like `Agent Command Center`). **Never use slashes** in page names.

| Surface | Page Title | Purpose & Content |
| :--- | :--- | :--- |
| **Command Center** | `Agent Command Center` | **Live Cross-Project Dispatch & Review**: Mission control Kanban using native Logseq 2.0 `/Query` blocks (`🚨 Needs Human Review` on top, `🔄 Currently Running`, `📥 Delegation Queue`). |
| **Daily Journal** | `<Month> <Day>, <Year>` | **Triage & Pulse**: Active review questions pinned at the top (`#agent_task` + `#needs-human`), one clean 1-line pulse per active branch/area at the bottom under `🤖 [[Agent Activity]]`. |
| **Branch Deep-Dive** | `<project>: <branch>` | **Senior Engineer Feature Design Doc / RFC**: 5-part technical specification (`Context & Goals`, `Technical Design & Flow`, `Decisions & Trade-offs`, `Verification & Usage`, `Status & Next Steps`). |
| **Evergreen Project** | `projects: <project>` | **Senior Engineer System Architecture & Runbook**: Long-term architecture, module map, data flows, storage layouts, operational build/test runbook, project conventions, and active worktree directory. |
| **Non-Git / `.md` Area** | `area: <area>` | **Lightweight 3-Part Control Index**: For non-git / `.md`-first areas (`career`, `masters`, etc.). Tracks `Focus & Goals`, `Workspace Map` (pointers to canonical `.md` files without duplicating prose), and `Open Decisions & Next Actions`. |
| **Global Rules** | `agent: core` | **Universal Invariants**: Developer preferences, coding standards, and cross-project rules. |

---

## 2. Mandatory Lifecycle Gates (Definition of Done)

Memory operations are **non-negotiable lifecycle gates** enforced with the same strictness as compilation, linting, and type checking:

```
       ┌──────────────────────────────────────────────────────────────┐
       │ Gate 1: Session Start Orient & Bootstrap (First Turn)        │
       │  • Resolve $GRAPH, $PROJECT, $BRANCH_SLUG                   │
       │  • Read agent: core, projects: <p>, <p>: <b>                │
       │  • Query active #agent_task (claim todo tasks)               │
       │  • Bootstrap missing/stub project pages to Tech Lead depth   │
       └──────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
       ┌──────────────────────────────────────────────────────────────┐
       │ Coding & Architectural Iteration                             │
       │  • Implement features, fixes, refactors, tests               │
       │  • Escalate trade-offs via Dual-Channel Review (Ask)         │
       └──────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
       ┌──────────────────────────────────────────────────────────────┐
       │ Gate 2: Automatic Progress Sync (Pre-Commit / Pre-Reply)     │
       │  • On feature/fix completion, git commit, or end of turn     │
       │  • Update <project>: <branch> (5-part Design Doc) in-place   │
       │  • Replace 1-line Daily Journal pulse under Agent Activity   │
       │  • MUST complete BEFORE responding to the user!              │
       └──────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
       ┌──────────────────────────────────────────────────────────────┐
       │ Distill (On Branch Completion / Merge)                       │
       │  • Promote permanent architecture and gotchas to project     │
       │  • Move branch to Completed Branches on project page         │
       └──────────────────────────────────────────────────────────────┘
```

### 2.1 Gate 1 — Session Start Orient & Bootstrap (First Turn)
Before modifying code or project/research docs in any workspace:
1. Resolve `$GRAPH` and workspace mode:
   - **Git repo**: `$PROJECT=$(basename $(dirname $(git rev-parse --path-format=absolute --git-common-dir)))`, `$BRANCH_SLUG=$(git branch --show-current | tr '/' '-')` (fallback to worktree folder if detached HEAD).
   - **Non-git / `.md`-first folder**: `$AREA=$(basename "$PWD" | tr '[:upper:]' '[:lower:]')`. If `projects: $AREA` already exists, orient on it; otherwise use `area: $AREA`.
2. Read `agent: core` and the active project/branch or area page via `logseq show`.
3. Scan for active agent tasks via targeted Datascript query:
   ```bash
   logseq query --graph "$GRAPH" --query '[:find (pull ?b [:db/id :block/title :block/created-at :block/updated-at {:logseq.property/status [:block/title :db/ident]} {:block/tags [:block/title :block/name]} {:block/page [:block/title :block/name]} {:block/refs [:block/title :block/name]}]) :where [?t :block/name "agent_task"] [?b :block/tags ?t]]' --output json
   ```
4. Check for open reviews (`#agent_task` + `#needs-human`) or late-answered reviews marked `done` by the human in Logseq: harvest decisions into the branch/area page and clean up the prompt. If an open `todo` task matches the current project/area/branch, claim it (`--status doing`).
5. **Bootstrap Invariant**: For git code repos, if `projects: <project>` does not exist or has < 6 sections, bootstrap the Tech Lead System Architecture & Runbook page. For non-git / `.md`-first areas, if `area: <area>` (and `projects: <area>`) does not exist, bootstrap the lightweight 3-section `area: <area>` index pointing to `.md` files on disk.

### 2.2 Gate 2 — Automatic Progress Sync (Pre-Commit & Pre-Reply Gate)
Treat Logseq memory synchronization with the same strictness as compilation, linting, and type checking:
- **Triggers**: Whenever you complete a feature, fix, or research/planning milestone, make a key decision, execute `git commit`, or are about to end a working turn:
  1. **Update `<project>: <branch>` or `area: <area>`**: Sync the 5-part Design Doc (code repos) or 3-part Area Index (non-git `.md` workspaces) in place.
  2. **Update Today's Daily Journal Pulse**: Under `🤖 [[Agent Activity]]` -> `[[projects: <project>]]` (or `[[area: <area>]]`) on today's Daily Journal page, replace the 1-line pulse:
     `- [[<project>: <branch>]] — <status_icon> <one-sentence description> (<HH:MM>)` (or `- [[area: <area>]] — <status_icon> <one-sentence description> (<HH:MM>)`)
     Keep the journal entry to exactly one line with zero child bullets.
- **Pre-Reply Enforcement**: You MUST execute this sync in the same turn **before** delivering your response to the user. Never wait for the user to remind you.

### 2.3 Ask (Dual-Channel Review Prompt)
When facing architectural trade-offs, ambiguous requirements, or breaking changes:
1. **Mirror to Logseq**: Pin an `in-review` task at the top (`--pos first-child`) of today's journal tagged with both `agent_task` and `needs-human` (`--update-tags '["agent_task" "needs-human"]'`), with `Why` and `Options` as open child bullets. This ensures it displays in `Agent Command Center`'s top section (`🚨 Needs Human Review`) and today's journal simultaneously. Fire an optional desktop notification.
2. **Ask in Chat**: Immediately ask the user the same question in your conversational response.
3. **Never block on Logseq**: Continue the conversation; do not hang your execution loop waiting for a background response.

### 2.4 Resolve (Closing Reviews)
- If the human answers in chat: append the decision to `## ⚖️ Key Engineering Decisions & Trade-offs` on `<project>: <branch>`, then delete the journal task block.
- If the human answered earlier in Logseq: auto-harvested during `orient`.

### 2.5 Distill (Evergreen Promotion)
When a branch merges or an architectural pattern becomes permanent:
1. Promote permanent architecture, conventions, and gotchas to `projects: <project>`.
2. Move the branch entry on the project page from `## 🌿 Active Branches & Worktrees` to `## 🏁 Completed Branches & Architecture History`.

---

## 3. Writing Taste & Quality Standards

Read [`references/writing-guide.md`](references/writing-guide.md) before authoring content:
- **Senior Tech Lead Depth**: Provide concrete component responsibilities, file touchpoints, data models, interfaces, config keys, runtime flows, and runbook commands.
- **Zero Duplication Between Design & Decisions**: `🏗️ Technical Design` explains *how the system works*; `⚖️ Key Engineering Decisions & Trade-offs` explains *why we chose Design A over Design B and what cost we accepted*.
- **Project Conventions Must Belong to the Target Project**: Never paste generic Logseq memory rules into another project's conventions; document that project's actual runtime and architectural invariants.
- **Consistent Header Icons**: Always include standard icons (`## 🧭 System Overview & Design Philosophy`, `## 🏗️ System Architecture & Module Map`, `## 💾 State, Config & Storage Layout`, `## 🛠️ Operational Runbook`, `## 📏 Engineering Conventions`, `## 🧠 Sharp Edges`, `## 🌿 Active Branches & Worktrees`, `## 🎯 Context, Problem & Goals`, `## 🏗️ Technical Design & End-to-End Flow`, `## ⚖️ Key Engineering Decisions & Trade-offs`, `## 🧪 Verification, Testing & Operational Usage`, `## 🚧 Status, Open Questions & Next Steps`).
- **Collapsed Blocks by Default**: Set `:block/collapsed? true` on reference/background sections at page creation so pages open cleanly; keep `🌿 Active Branches & Worktrees` expanded (`:block/collapsed? false`).
- **No wrapper bullets**: Never create a parent bullet just to hold one child sentence.
- **Light STE Clarity**: Write active, direct sentences. Sentences may reach 35–40 words when describing complex technical architectures, schemas, and trade-offs.
- **Real links via `--blocks`**: Always write with `--blocks` or `--blocks-file` so `[[links]]` are registered in Logseq's `:block/refs` graph. (Updating an existing block with `--content` drops links).

---

## 4. Extras: Command Center, Delegation, Sign-Off & Follow-Ups

1. **Agent Command Center (`Agent Command Center`)**: Cross-project Kanban control center using native Logseq 2.0 `/Query` blocks:
   - `## 🚨 Needs Human Review`: `(and (task "In Review") (tags [[agent_task]]))` (placed at the top for immediate visibility).
   - `## 🔄 Currently Running`: `(and (task "Doing") (tags [[agent_task]]))`.
   - `## 📥 Delegation Queue`: `(and (task "Todo") (tags [[agent_task]]))`.
2. **Delegation Queue**: When the human creates a `todo` task in Logseq tagged `#agent_task` targeting a project/branch, claim it (`--status doing`), execute it, and mark it `--status done` (or `in-review` if human verification is required) with a completion note.
3. **Human Sign-Off Mode**: For sensitive changes, the agent transitions a task to `--status in-review` with `--update-tags '["agent_task" "needs-human"]'`, moving it to the top of `Agent Command Center` for review before closure.
4. **Agent-Queued Follow-Ups**: When an agent detects out-of-scope debt or follow-up milestones, it creates a `todo` (or `backlog`) task tagged `#agent_task` linked to `[[<project>: <branch>]]`, automatically adding it to the `📥 Delegation Queue` for future sessions.
5. **Rough-Notes Co-Authoring**: If the human leaves unformatted rough notes at the top level of a branch page, expand them into the structured sections while preserving the human's original thoughts.
6. **Self-Updating Rules**: When the human gives cross-project instructions, update `agent: core` under `## 📐 Global Engineering Conventions`.

---

## 5. Detailed References

- [`references/writing-guide.md`](references/writing-guide.md): Concrete before/after examples and quality calibration.
- [`references/cli-recipes.md`](references/cli-recipes.md): Copy-pasteable `logseq` CLI commands for every operation.
- [`references/page-templates.md`](references/page-templates.md): Page schemas and layout skeletons.
