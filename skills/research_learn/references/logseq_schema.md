# Research Memory — Logseq 2.0 DB Schema & Journal Protocol

This is the memory layer for the `research_learn` skill. It lives inside your main Logseq 2.0 DB graph (`logseq-sync`), strictly scoped to `paper:`, `concept:`, `thesis:` pages, research tags, and the `📚 [[Research & Learning Activity]]` subtree on today's journal. Never read, modify, or list unrelated personal notes or tasks. Everything on research pages is agent-maintained except the explicitly human-owned zone on paper pages.

## 1. Graph target resolution

Resolve the graph name, in order:

1. `$RESEARCH_LOGSEQ_GRAPH` (environment override)
2. contents of `~/.config/research_learn/graph` (created by `setup.sh`, default `logseq-sync`)
3. contents of `~/.config/logseq_memory/graph`
4. literal `logseq-sync`

```bash
GRAPH="${RESEARCH_LOGSEQ_GRAPH:-$(cat "$HOME/.config/research_learn/graph" 2>/dev/null || cat "$HOME/.config/logseq_memory/graph" 2>/dev/null || echo logseq-sync)}"
```

Never switch the user's active graph. Pass `--graph "$GRAPH"` on every `logseq` command. Read-only preflight:

```bash
logseq graph list                       # confirm "$GRAPH" exists
logseq graph info --graph "$GRAPH"      # confirm DB graph
```

## 2. Logseq 2.0 DB invariants (non-negotiable)

| Rule | Why | Enforcement |
| :--- | :--- | :--- |
| **Flat colon page titles only** | Slashes are illegal in Logseq 2.0 DB titles | `paper: <slug>`, `concept: <topic-slug>`, `thesis: <area-slug>`, `agent: core`. Never `paper/foo`. |
| **Real `[[links]]`** | `--content` drops `:block/refs` | Create/replace any block containing `[[...]]` via `--blocks` or `--blocks-file`. |
| **Page-level tags** | `--update-tags` on `upsert block` tags every heading block instead of the page | Tag pages with `logseq upsert page --page "<title>" --update-tags '[...]'`. Only pass `--update-tags` to `upsert block` for block-specific tags like `#thesis-gap`. |
| **Zero property drawers** | Journal/activity blocks must stay clean | Never attach `project:`, `branch:`, `slot-key:` etc. to journal blocks. |
| **In-place section updates** | No duplicate headings | Locate heading block `--id`, remove obsolete children, insert updated children at that heading. |
| **Scoped queries only** | Privacy inside `logseq-sync` | Never `logseq list task` graph-wide. Scope strictly to `#learn-paper`, `#learn-concept`, `#learn-thesis` and today's journal. |

Tag vocabulary (bootstrapped by `setup.sh`): `learn-paper`, `learn-concept`, `learn-thesis`, `covered`, `shaky`, `recalled-cold`, `thesis-gap`.

## 3. Page templates

### 3.1 `paper: <slug>` — canonical page

`slug` comes from `zotero-bridge item <itemKey>` (citekey-independent `<author>-<year>-<words>`). Use `--blocks-file` so `[[paper: ...]]`, `[[concept: ...]]` and `zotero://` links register as real refs.

```markdown
- ## 📌 Paper Card & Readiness
  - Title: <Full Paper Title> (<Authors>, <Year>)
  - Zotero: `key:<ITEM_KEY>` | [Open in Zotero](zotero://select/library/items/<ITEM_KEY>) | [Open PDF](zotero://open-pdf/library/items/<ATTACH_KEY>)
  - Reading Depth: `L2 (Method)` | Readiness: `Yellow -> Bridged`
  - BibTeX / Overleaf Key: `<bibtex_key_or_unset>`
- ## ✍️ My Notes, Ideas & Critiques
  - *(Human-owned zone — write freely here; agent reads for context and NEVER overwrites)*
- ## 🖍️ Promoted Highlights & Margin Questions
  - *(Only high-signal or questioned highlights promoted from Zotero; full set always read on-demand)*
  - "[Eq. 4 scaling factor...]" — [p. 4](zotero://open-pdf/library/items/<ATTACH_KEY>?page=4) | Margin note: *Why $\sqrt{d_k}$ instead of $d_k$?*
- ## 🔗 Lineage Chain & Context
  - Problem Context: <1-2 sentences on why the field cared>
  - Builds On: [[paper: <ancestor-1>]] — <specific limitation it inherited>
  - Extends / Challenges: [[paper: <ancestor-2>]] — <exact contrast>
- ## 🧪 Claims, Assumptions & Limitations (Source-Anchored)
  - Claim: <atomic claim> `[§3.2, Eq. 4]`
    - Relies on assumption: <explicit/implicit assumption>
    - Fragility / Failure Mode: <where it breaks — incorporates user critique>
- ## 🧠 Extracted Propositions & Linked Concepts
  - [[concept: <slug-1>]] — <1-line proposition learned from this paper>
- ## 🗣️ Cold Teach-Back Snapshot
  - <YYYY-MM-DD>: <concise record of user's cold explanation + remaining fuzzy spots>
```

**Human-ownership rule:** before any upsert, read the existing `## ✍️ My Notes, Ideas & Critiques` subtree and re-emit it verbatim. Never replace, reorder, or summarize it. Only agent sections are rewritten.

Write pattern (page-level tag + real links via `--blocks-file`):

```bash
logseq upsert block --graph "$GRAPH" \
  --target-page "paper: vaswani-2017-attention" \
  --pos last-child --blocks-file ./paper_blocks.md
logseq upsert page --graph "$GRAPH" \
  --page "paper: vaswani-2017-attention" \
  --update-tags '["learn-paper"]'
```

### 3.2 `concept: <topic-slug>`

```markdown
- ## 💡 Propositions & Intuition
  - <Atomic proposition 1 — compact, high-precision for low-token cross-session reuse>
- ## ⛓️ Reasoning Chains (Dependencies)
  - Requires: [[concept: <prereq-1>]], [[concept: <prereq-2>]]
  - Leads To: [[concept: <derived-1>]]
  - Grounded In: [[paper: <slug>]] `[§/eq]`
- ## 🎯 Mastery & Practice Signals
  - Last Probed / Practiced: `<YYYY-MM-DD>` | Confidence: `<%>`
  - Known Confusion / Cliff: <specific misconception surfaced during probing>
```

Tag the **page** with `learn-concept` plus exactly one mastery tag (`covered`, `shaky`, or `recalled-cold`). When changing mastery state, remove the old mastery tag with `--remove-tags`:

```bash
logseq upsert block --graph "$GRAPH" --target-page "concept: tied-embeddings" \
  --pos last-child --blocks-file ./concept_blocks.md
logseq upsert page --graph "$GRAPH" --page "concept: tied-embeddings" \
  --update-tags '["learn-concept" "shaky"]'
```

### 3.3 `thesis: <area-slug>`

```markdown
- ## 🎯 Research Question & Scope
  - <Question this thesis area must answer; non-goals>
- ## 🧩 Cross-Paper Comparison Matrix
  - [[paper: A]] — assumes <X>; reports <result>
  - [[paper: B]] — shows <X> breaks under <Y>; reports <result>
- ## 🔥 Tension / Gap Edges
  - [[paper: A]] assumes X ↔ [[paper: B]] shows X breaks under Y — `#thesis-gap`: <defensible question>
- ## 🛡️ Defense Q&A Log
  - <YYYY-MM-DD>: <adversarial reviewer/advisor question> -> <best answer + weak spot>
- ## 📚 Citation Anchors
  - [[paper: A]] -> `\cite{<zotero-bibtex-key>}` (Overleaf `references.bib`)
```

Tag the **page** with `learn-thesis` via `logseq upsert page`, and tag individual gap-edge blocks with `thesis-gap`.

### 3.4 Today's Daily Journal — one-line pulse

Under `📚 [[Research & Learning Activity]]` (separate from `🤖 [[Agent Activity]]`), keep exactly **one line per interacted paper/concept/thesis per day**, zero child bullets. Omitting `--target-page` on `logseq upsert block` targets today's journal automatically (Logseq formats journal titles like `Nov 25th, 2026`). Revisit same day -> update that line in place via its block `--id`, or append a new item under the existing heading with `--target-id <heading-id>`.

```markdown
- 📚 [[Research & Learning Activity]]
  - [[paper: vaswani-2017-attention]] — 🟡 L2 Method: bridged scaled softmax, completed §3.2 + critique (14:20)
  - [[concept: tied-embeddings]] — ✅ Practice: recalled cold on gradient accumulation (16:05)
  - [[thesis: efficient-inference]] — 🔥 Sparring: defended gap edge vs. reviewer Q3 (17:40)
```

```bash
# First research pulse of the day (omitting --target-page writes to today's journal):
logseq upsert block --graph "$GRAPH" --pos last-child --blocks-file ./journal_pulse.md
# Subsequent pulse same day (under existing 📚 [[Research & Learning Activity]] heading id):
logseq upsert block --graph "$GRAPH" --target-id <heading-id> --pos last-child --blocks-file ./pulse_line.md
```

Status icons: 🟢 Green / entered · 🟡 Yellow / bridged · 🔴 Red / lineage detour · ✅ recalled-cold · ⚠️ shaky · 🔥 thesis sparring.

## 4. Datascript queries (read-only)

All commands target `$GRAPH`. Scope every query to research tags or today's journal.

Known concept pages + mastery tags (skip `#recalled-cold` when probing):

```bash
logseq query --graph "$GRAPH" --output json --query \
'[:find (pull ?p [:db/id :block/title {:block/tags [:block/title :block/name]}])
 :where [?t :block/name "learn-concept"] [?p :block/tags ?t]]'
```

Shaky / covered concept pages for Practice mode:

```bash
logseq query --graph "$GRAPH" --output json --query \
'[:find (pull ?p [:db/id :block/title {:block/tags [:block/title :block/name]}])
 :where [?lc :block/name "learn-concept"] [?p :block/tags ?lc]
        [?m :block/name "shaky"] [?p :block/tags ?m]]'
```

Topic clusters — concept pages linked from a given paper page:

```bash
logseq query --graph "$GRAPH" --output json --query \
'[:find (pull ?c [:db/id :block/title {:block/tags [:block/title :block/name]}])
 :where [?p :block/name "paper: vaswani-2017-attention"]
        [?b :block/page ?p] [?b :block/refs ?c]
        [?lc :block/name "learn-concept"] [?c :block/tags ?lc]]'
```

Existing human notes on a paper page (read before any upsert):

```bash
logseq show --graph "$GRAPH" --page "paper: vaswani-2017-attention"
logseq query --graph "$GRAPH" --output json --query \
'[:find (pull ?b [:db/id :block/title :block/created-at])
 :where [?p :block/name "paper: vaswani-2017-attention"]
        [?b :block/page ?p] [?b :block/title ?title]
        [(clojure.string/includes? ?title "My Notes")]]'
```

Thesis gap edges across the graph:

```bash
logseq query --graph "$GRAPH" --output json --query \
'[:find (pull ?b [:db/id :block/title {:block/page [:block/title]}])
 :where [?t :block/name "thesis-gap"] [?b :block/tags ?t]]'
```

## 5. Safe in-place section update (no duplicate headings)

1. Find the heading block id with `logseq query` (Note: Logseq strips the markdown `## ` prefix from `:block/title`, so match the heading text itself, e.g. `"Claims, Assumptions"`).
2. Remove obsolete children of that heading:

```bash
logseq remove block --graph "$GRAPH" --id <old-child-id>
```

3. Re-insert fresh children beneath the heading, preserving any human-owned subtree verbatim:

```bash
logseq upsert block --graph "$GRAPH" --target-id <heading-id> --pos first-child \
  --blocks-file ./section_children.md
```

4. Dry-run before real writes:

```bash
logseq upsert block --graph "$GRAPH" --target-page "paper: vaswani-2017-attention" \
  --blocks-file ./paper_blocks.md --dry-run
```

`--blocks-file` is mandatory whenever the payload contains `[[links]]`; `--update-tags` must be an explicit EDN vector. Never use property drawers.
