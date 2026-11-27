# Logseq Writing Guide: Tech Lead Depth, Taste & Structure (v2.1)

> **Core Philosophy**: A Logseq graph is a human second brain and human-in-the-loop control center, not an append-only machine log. Every page must read as if authored by a **Senior Engineer / Tech Lead** documenting a critical system: comprehensive, authoritative, scannable, and packed with concrete technical context for teammates reading it six months from now.

Inspired by Notion's curated memory layer (`makenotion/lore`), Obsidian's CLI-first skill (`kepano/obsidian-skills`), and Cline's "Stable vs. Active" split, this guide prevents **Memory Rot** while insisting on real technical depth over shallow executive summaries.

---

## 1. The Non-Negotiable Rules of Taste

### Rule 1: Senior Engineer / Tech Lead Technical Depth
Do not write shallow 5-bullet blurbs. When documenting a repository on `projects: <project>` or an active initiative on `<project>: <branch>`, provide the technical depth expected of a Senior Tech Lead:
- Concrete component responsibilities, file touchpoints, and directory maps.
- Exact data models, TypeScript interfaces, configuration keys, default values, and thresholds.
- Step-by-step end-to-end execution and message flows.
- Runnable CLI build, test, run, and debugging commands.
- Concrete architectural failure modes, concurrency constraints, and trade-offs.

### Rule 2: Zero Duplication Between Design and Decisions
A common failure mode is repeating architectural mechanics in both the design section and the decisions section. Keep them strictly orthogonal:
- **`🏗️ Technical Design & End-to-End Flow` explains HOW the system works**:
  - The runtime sequence of operations.
  - Data structures, state transitions, and file boundaries.
  - Payload schemas, API endpoints, and event listeners.
- **`⚖️ Key Engineering Decisions & Trade-offs` explains WHY we chose Design A over Design B**:
  - The ADR (Architecture Decision Record) rationale.
  - What alternatives were explicitly evaluated and rejected.
  - Why the chosen pattern is superior despite its costs.
  - What concrete engineering trade-off or penalty was accepted (e.g. higher latency, additional process spawn, stricter memory footprint).
*Never restate the mechanics of the feature under Decisions; focus purely on the rationale, rejected alternatives, and accepted cost.*

### Rule 3: Project Conventions Must Belong to the Target Project
When documenting `## 📏 Engineering Conventions & Architectural Invariants` on `projects: <project>`:
- **STRICT INVARIANT**: Never paste generic Logseq memory rules (e.g. "use colon titles", "avoid property drawers") into another project's conventions!
- Document the target repository's **actual engineering conventions**:
  - Runtime architecture (e.g. Node.js ESM, Bun, Go, Python, Rust).
  - Error handling philosophy (e.g. error wrapping with context, Result types, fail-fast vs recover).
  - Concurrency model & locking discipline (e.g. mutexes, channel pipelines, database isolation).
  - Testing & typing invariants (e.g. Vitest coverage gates, strict TypeScript flags, no `any`).
  - Logging & telemetry standards (e.g. structured JSON to stderr, stdout reserved for machine pipes).

### Rule 4: No Wrapper Bullets
**Never make a parent bullet solely to hold a single child sentence.**
* ❌ **Bad (Machine habit)**:
  * `**What this project is**`
    * `A shared memory layer for AI agents.`
* ✅ **Good (Human taste)**:
  * `**What this is**: A shared, human-explorable memory layer for AI agents across multiple IDE harnesses.`
* **When to use sub-bullets**: Only add nested children when there are **two or more distinct sub-points** (such as multiple alternative options, separate trade-offs, or distinct verification steps).

### Rule 5: Let Content Choose Its Shape
Do not force every section into identical bullet templates:
* **Overview / Context**: 2–4 crisp, authoritative sentences directly beneath the heading.
* **Flow / Sequence**: A numbered list (`1. ...`, `2. ...`) tracing step-by-step data transformations.
* **Decisions**: ADR-style bold headings (`**Decision: Option A vs Option B**`) with concise sub-bullets for Rejected Alternatives, Rationale, and Accepted Trade-off.
* **Touchpoints & Schemas**: Code blocks and structured inline code for interfaces, config flags, and file paths.

### Rule 6: Explain, Don't Diff
**Describe behavior, architectural boundaries, and intent — not raw git diffs.**
* Do not dump uncontextualized lists of modified files or function names (`git log --stat` dumps).
* File and function references must be supporting details within an architectural narrative explaining component ownership and message propagation.
* **The Teammate Test**: *Would a senior engineer joining the team next week understand how this subsystem works, why it was designed this way, and how to operate it without opening the source code or reading git commit histories?*

### Rule 7: Link Generously with Real `[[links]]`
* Connect concepts, components, and pages using `[[wiki-links]]` so Logseq automatically builds a rich, bidirectional Linked References graph.
* **Link format**: Always use colon separators (`[[projects: <project>]]`, `[[<project>: <branch>]]`). Never use slashes (`projects/branch` renders as broken literal text in Logseq 2.0 DB).
* **CLI Requirement**: Always insert content containing `[[links]]` using the CLI's `--blocks` or `--blocks-file` flag so `:block/refs` are correctly indexed in Datascript. (Using `--content` drops page references).

### Rule 8: Consistent Header Icons
Always prefix section titles with standard icons for instant visual recognition:
* **Project pages**:
  - `## 🧭 System Overview & Design Philosophy`
  - `## 🏗️ System Architecture & Module Map`
  - `## 💾 State, Config & Storage Layout`
  - `## 🛠️ Operational Runbook (Build, Run, Test, Debug)`
  - `## 📏 Engineering Conventions & Architectural Invariants`
  - `## 🧠 Sharp Edges & Permanent Gotchas`
  - `## 🌿 Active Branches & Worktrees`
  - `## 🏁 Completed Branches & Architecture History`
* **Branch pages**:
  - `## 🎯 Context, Problem & Goals`
  - `## 🏗️ Technical Design & End-to-End Flow`
  - `## ⚖️ Key Engineering Decisions & Trade-offs`
  - `## 🧪 Verification, Testing & Operational Usage`
  - `## 🚧 Status, Open Questions & Next Steps`
* **Global rules**:
  - `## 🤖 Agent Identity & Role`
  - `## 📐 Global Engineering Conventions`
  - `## 🧠 Self-Updating Memory`

### Rule 9: Collapsed Reference Blocks by Default
To maintain a clean page entrance, set `:block/collapsed? true` on reference/background sections (`🧭 System Overview`, `🏗️ System Architecture`, `💾 State & Config`, `🛠️ Operational Runbook`, `📏 Engineering Conventions`, `🧠 Sharp Edges`) so they open collapsed by default.
* Leave `🌿 Active Branches & Worktrees` expanded (`:block/collapsed? false`) so current activity is instantly visible on first load.

### Rule 10: Co-Authoring & Respect for Human Notes
* The agent edits **only** the section blocks it created under its own headings.
* **Never overwrite, modify, or delete top-level blocks or notes written by the human.**
* When a human leaves rough scratch notes on a branch page, the agent should read them, reference them, or expand upon them in its own designated section without disturbing the human's scratch blocks.

---

## 2. Technical Clarity & Sentence Limits (Light STE)

All agents writing in Logseq must apply a **Light ASD-STE100 (Simplified Technical English)** standard (~80% compliance).

STE eliminates ambiguous words, convoluted syntax, and marketing fluff while allowing ample technical room for deep explanations.

### 2.1 Sentence Limits: Technical Room vs Action Brevity
- **Complex Technical Explanations & Schemas**: Sentences may extend up to **35–40 words** when explaining intricate runtime flows, data transformations, subsystem boundaries, config keys, thresholds, or ADR trade-offs.
- **Procedural Steps & Instructions**: Keep action steps concise (**maximum 20 words**).
- **Rule of Thumb**: Prefer clarity and precision over artificial truncation. If breaking a technical description hurts precision, keep it unified up to 40 words. If it wanders beyond 40 words or combines multiple unrelated actions, split it.

### 2.2 Core Principles of Technical STE
1. **One Thought Per Bullet**: State one technical concept, reason, or step per bullet. Do not chain multiple distinct steps with run-on conjunctions.
2. **Active Voice & Present Tense**:
   - ✅ **Active**: "The storage adapter flushes dirty blocks to disk using atomic rename."
   - ❌ **Passive**: "Dirty blocks are flushed to disk by the storage adapter using atomic rename."
3. **Imperative Mood for Instructions**: Begin procedural runbook steps with direct imperative verbs: `Run`, `Build`, `Verify`, `Inspect`, `Deploy`, `Query`.
4. **Condition Before Action**: "If the socket times out after 5,000ms, abort the connection and retry with exponential backoff."
5. **No Ambiguous Marketing Fluff**: Eliminate empty adjectives like *seamlessly*, *robust*, *blazing-fast*, *effortlessly*, *powerful*. Replace them with concrete benchmarks, SLAs, and technical invariants.

---

## 3. Before vs After: Concrete Tech Lead Examples

### Example 1: Project Overview & Architecture

#### ❌ Before (Shallow 3-bullet stub)
```markdown
## 🧭 Overview
- A universal agent memory system.
- Uses Node.js and Logseq CLI.
- Runs across multiple IDEs.
```
*Why this fails*: Zero engineering depth. Tells a teammate nothing about the architecture, execution model, persistence strategy, or runtime boundaries.

#### ✅ After (Tech Lead System Architecture & Philosophy)
```markdown
## 🧭 System Overview & Design Philosophy
- **System Purpose**: [[agent_memory]] is a shared, human-explorable memory layer and task orchestration control center for AI coding agents across Antigravity, Claude Code, Cursor, and Codex. It persists long-term architectural knowledge and active branch context directly in the user's local Logseq 2.0 graph.
- **Core Philosophy**:
  - Human Understanding First: All pages must be written for a human reading them six months later, eliminating machine telemetry and raw commit diffs.
  - Pure Skill Architecture: Zero background daemons, zero HTTP wrappers, and zero intermediate databases; operations execute directly against the official Logseq 2.0 CLI (`logseq`).
  - Definition-of-Done Discipline: Memory synchronization is treated with the same rigor as compilation, linting, and type checking, running before any coding turn concludes.
- **Primary Technology Choices**:
  - Runtime: Node.js 20+ ESM and POSIX shell scripts for portability.
  - Storage & Transport: Native Logseq 2.0 CLI (`logseq`) querying and mutating local Datascript graph entities via SQLite storage.
```
*Why this succeeds*: Teaches the reader the architecture, guiding principles, and concrete technology stack with authoritative clarity.

---

## 2. Example 2: Technical Design vs Decisions & Trade-offs (Zero Duplication)

#### ❌ Before (Duplicate descriptions and shallow rationale)
```markdown
## 🔍 How it works
- We use in-place block updates because appending blocks creates duplicates and makes pages ugly. We query the block ID and replace the children.

## ⚖️ Decisions & Trade-offs
- **In-place updates**: We decided to update blocks in-place instead of appending because appending causes duplicates and makes pages ugly.
```
*Why this fails*: Both sections say the exact same thing. Neither gives technical details of the implementation or concrete ADR analysis.

#### ✅ After (Orthogonal Technical Flow vs ADR Analysis)
```markdown
## 🏗️ Technical Design & End-to-End Flow
- **In-Place Section Replacement Routine**:
  1. Inspect target page hierarchy with `logseq show --graph "$GRAPH" --page "$BRANCH_PAGE" --level 2 --output json`.
  2. Locate target section header block (e.g. `## 🏗️ Technical Design & End-to-End Flow`) and extract its numeric `db/id`.
  3. Extract all immediate child `db/id`s belonging to the section header.
  4. Execute atomic deletion of existing child blocks via `logseq remove block --id '[<id1>, <id2>]'`.
  5. Read updated outline markdown from prepared temporary payload file.
  6. Insert replacement children under heading block using `logseq upsert block --target-id <HEADING_ID> --pos last-child --blocks-file <PATH>`.
- **Interface & Schema**:
  - Section Payload: Standard Markdown outline where top-level list items become direct children of the H2 heading block.
  - Link Graph Invariant: All blocks containing `[[wiki-links]]` are ingested via `--blocks` or `--blocks-file` to trigger automatic `:block/refs` population in Datascript.

## ⚖️ Key Engineering Decisions & Trade-offs
- **Decision: In-Place Section Updates vs Append-Only Work Logs**:
  - **Rejected Alternatives**: Appending timestamped markdown chunks to the bottom of the page or maintaining separate per-session log files.
  - **Rationale**: Append-only logs cause catastrophic outliner rot in Logseq, creating duplicate H2 headings that break navigation and overwhelm human readers. In-place updates maintain a clean, evergreen living document.
  - **Accepted Trade-off**: Requires two sequential CLI roundtrips (read-and-parse followed by remove-and-insert), adding ~200ms of mutation latency compared to blind appends.
```
*Why this succeeds*: `Technical Design` explains the exact execution mechanics and interfaces. `Decisions & Trade-offs` provides genuine ADR analysis (rejected alternatives, rationale, and accepted cost) without repeating the operational steps.

---

## Example 3: Operational Runbook & Project Conventions

#### ❌ Before (Pasting generic Logseq rules into project conventions)
```markdown
## 📏 Conventions & Invariants
- Use colon titles like projects: foo.
- Do not use property drawers.
- Link pages with double brackets.
```
*Why this fails*: Violates Rule 3. These are Logseq memory invariants, not the conventions of the project being built!

#### ✅ After (Project-specific engineering invariants and exact runbook)
```markdown
## 🛠️ Operational Runbook (Build, Run, Test, Debug)
- **Dependency Installation & Build**:
  - `pnpm install --frozen-lockfile`: Installs pinned dependencies across the monorepo workspace.
  - `pnpm build`: Compiles TypeScript packages with `tsc -b`.
- **Testing Suites**:
  - `pnpm test`: Runs Vitest across all unit and integration suites.
  - `node test/graph-lint.mjs`: Runs the read-only Logseq graph integrity linter against the active graph.
- **Diagnostic Inspection**:
  - Inspect graph schema: `logseq query --graph "$GRAPH" --query '[:find (pull ?b [*]) :where [?b :block/name "agent_task"]]'`

## 📏 Engineering Conventions & Architectural Invariants
- **Fail-Fast Configuration**: All environment variables and config files must be validated on startup using Zod schemas; missing keys throw fatal configuration errors immediately rather than failing during runtime requests.
- **Error Context Wrapping**: Catch blocks must wrap lower-level storage or network exceptions with domain context (e.g. `throw new StorageError("Failed to flush session buffer", { cause: err })`).
- **Strict Concurrency Locking**: Multi-process mutations to local cache files must acquire a POSIX advisory lock via `flock` before writing, timing out after 5,000ms.
```
*Why this succeeds*: Documents the actual project's operational commands and engineering invariants.

---

## 4. Project Page vs Branch Page Roles (Stable vs. Active Split)

| Dimension | `projects: <project>` (Evergreen System Architecture) | `<project>: <branch>` (Feature Design Doc / RFC) |
| :--- | :--- | :--- |
| **Lifespan** | Permanent (persists across years of codebase evolution) | Ephemeral (active while branch/initiative is in progress) |
| **Audience** | Any engineer or agent joining the repo; system architecture overview | Tech Lead reviewing the PR or engineer resuming work on this feature |
| **Core Content** | • System purpose & design philosophy<br>• Module map & end-to-end data flows<br>• State, config & storage layouts<br>• Operational build/test/debug runbook<br>• Project-specific engineering invariants<br>• Sharp edges & permanent gotchas<br>• Active & completed branch indexes | • Context, problem statement, goals & non-goals<br>• Technical design, runtime flow & component touchpoints<br>• Concrete data models, interfaces & config schemas<br>• Key engineering decisions & ADR trade-offs<br>• Verification commands & test suite coverage<br>• Status, remaining milestones & open questions |
| **Update Frequency** | Rare (major architectural shifts, merged branches) | Mandatory (session start orient, pre-commit, pre-reply gate) |
