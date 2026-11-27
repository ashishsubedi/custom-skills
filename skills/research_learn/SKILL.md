---
name: research_learn
description: Deep-read Zotero papers, learn dense topics, run active-recall practice, and synthesize/defend a thesis in Logseq (logseq-sync). Use for paper deep-reads, concept learning, quizzes/practice, thesis synthesis, or defense sparring.
---

# Research & Learning Harness

Local-first learning loop shared by Antigravity and OpenCode. Zotero is the source of truth for papers/highlights; your Logseq 2.0 DB graph (`logseq-sync`) is the source of truth for what you hold, scoped strictly to `paper:`, `concept:`, `thesis:` pages and research tags.

**Tools**
- `zotero-bridge` (read-only CLI; falls back from Zotero local API to SQLite snapshot automatically) — `search`, `recent`, `item`, `annotations`, `collections`, `bibtex`, `text`. `--sqlite-only` and `--pretty` work before or after the subcommand. Use `zotero-bridge text <itemKey>` when your model cannot read PDFs natively (preserves 2-column reading order; never use `pdftotext -layout`). Never write Zotero files.
- `logseq` CLI against the resolved graph (`$RESEARCH_LOGSEQ_GRAPH` → `~/.config/research_learn/graph` → `~/.config/logseq_memory/graph` → `logseq-sync`). Strictly scope all reads/writes to `#learn-paper`, `#learn-concept`, `#learn-thesis`, and today's `📚 [[Research & Learning Activity]]` subtree — never touch unrelated personal pages or tasks.
- Full write protocol, templates, and Datascript queries: `references/logseq_schema.md`. Thesis/sparring: `references/thesis_mode.md`.

**Mode routing**
| User intent | Mode |
| :--- | :--- |
| "deep-read / read this paper (L1/L2/L3)" | `paper` |
| "learn / explain topic X", "help me understand X" | `topic` |
| "quiz me", "practice X", "test my recall" | `practice` |
| "thesis", "synthesize papers", "spar / defend / reviewer questions" | `thesis` / `spar` → read `references/thesis_mode.md` |

## Doctrine (applies to every mode)

1. **Terminal condition: the goal feels obviously true.** Not recitation, not coverage, not "I get it". Hold it as self-evident, safe to build on. Test by cold teach-back.
2. **Current understanding = what is already held as obviously true.** Bracket it precisely before teaching; never re-teach what is held.
3. **Knowledge is structure** — propositions as nodes, reasoning steps as edges. The "click" is loose facts collapsing into a derivation. Build the smallest such structure.
4. **One reasoning step at a time.** Each step attaches to what is held by a single small move, so it lands as obviously true. Check it immediately; repair before building on it. Errors surface where they occur, not three nodes later.
5. **No meta-narration; clear natural prose.** Do not announce "now I will establish X", do not leak internal plan-node labels (`B1`, `B2`, `S3`), and do not write telegraphic/caveman fragments. Concise means *one reasoning step per turn* in plain, readable sentences — never clipped shorthand.
6. **The agent owns logistics.** Searching, fact-checking, ordering, source-finding happen silently or via tools. The learner's effort goes entirely into the material.
7. **Trust & verbatim bounds.** Every claim anchored to `[§/eq]` in the actual PDF (or a web-checked primary source). Never fabricate citations, equations, section numbers, or Zotero keys. Quote quantitative bounds and inequalities verbatim so compression never flips direction (e.g., *"overhead ≤ 20% of X"* ≠ *"≤ 20% of X"*). Unverified = `[user hypothesis]`.

## Hard anti-drift guardrails

- Never dump a full paper summary unprompted in `L2`/`L3`.
- **Soft confidence calibration:** Prompt for **Confidence % + brief messy reasoning**, but treat Confidence % as a calibration signal rather than a bureaucratic blocker. If the learner gives substantive reasoning without a %, infer confidence from hedging and move on — never stall or stack *"missing % for Q(n-1)"* on top of a new question.
- **Inline equations & standard LaTeX:** Always show any equation, figure, or number inline before asking about it — never quiz blindly on *"Eq. 4"*. Render math with standard Markdown LaTeX (`$...$` / `$$...$$`) outside fenced code blocks; never put equations in code blocks.
- **Voice dictation tolerance:** The learner may use noisy voice dictation — infer technical intent charitably and never nitpick transcription errors.
- One reasoning step / one question per turn. No walls of text.
- Black-Boxable prerequisites never trigger a prerequisite rabbit hole.
- Never overwrite `## ✍️ My Notes, Ideas & Critiques` on a `paper:` page — read it to model the learner's thinking, re-emit it verbatim on upsert.
- Promote only high-signal or questioned highlights to Logseq; the full highlight set is always pulled on demand.

---

## Mode A — Paper Deep-Read (`paper`)

### Stage 1 — Depth & Zotero pull

1. If Reading Depth unspecified, ask: `L1 Triage` (is this relevant? claim + contribution + one limitation), `L2 Method` (how does it work? mechanism + assumptions + evidence), `L3 Proof` (verify derivation/theorem line by line).
2. Resolve the paper:
   ```bash
   zotero-bridge search "<query or author/title>" --limit 20
   zotero-bridge item <itemKey>
   zotero-bridge annotations <itemKey>   # ALL highlights + margin questions, on demand
   zotero-bridge text <itemKey> --pretty # clean reading-order PDF text (text-only models)
   ```
   Use returned `slug`, `pdfPath`, `zoteroSelectUri`, `zoteroPdfUri`, `attachmentKey`. Pull `bibtex` only when needed for citations.
3. Read the existing `paper: <slug>` page in Logseq (especially the human zone) and any linked `concept:` pages.

### Stage 2 — Pre-Flight Readiness Gate

1. Read the PDF (via native PDF read or `zotero-bridge text <itemKey>`); split **pre-paper** prerequisites into **Blocking** (foundations required *before* reading the paper, e.g., standard attention/KV cache or OS paging) vs **Black-Boxable** (accept as a given for now, name it once, move on). **Never** include the paper's own equations, algorithms, or novel mechanisms as Pre-Flight prereqs — those belong in Stage 3 after introducing them.
2. Query Logseq for known `#learn-concept` pages; skip anything already `#recalled-cold`. Use the Datascript queries in `references/logseq_schema.md`.
3. Run a short **Binary Search Probe** (2–4 questions) targeting uncertain Blocking pre-paper prereqs and the user's own Zotero margin questions. Prompt for **Confidence % + messy thinking** (in Antigravity: Voice Dictation `Ctrl+M`). Never refer to a paper equation without showing it inline in Markdown LaTeX.
4. Verdict:
   - **🟢 Green** — held; enter the paper directly.
   - **🟡 Yellow** — one blocking gap; run a **10–15 min focused Micro-Bridge** on just that gap, then enter.
   - **🔴 Red** — no footing; pause the target and map a **2–3 paper Lineage Chain** (`Problem → Paper A (failure) → Paper B → Target`) or run a prerequisite topic session.
5. Render the coarse **Minimal Dependency Mermaid DAG** (smallest set of propositions from current to goal) and confirm the roadmap. This is the low-resolution map, not the lesson script.

### Stage 3 — Active Mastery Loop

Walk the DAG one reasoning step at a time. Each step:

1. **Predict** — ask what the paper does next / what follows, before revealing it. Require confidence + rough thinking.
2. **Teach** — mixed **Socratic + Expository**: question first where it exposes the gap, plain assertion where a foundation or connective move needs to land smoothly. Foundations: unconditionally true, motivated by the paper's problem. Derived steps: let them follow visibly from what is held.
3. **Check** — one graded question at the end of the step. If it did not land, stop, locate the precise weak step, repair it, re-check. Never proceed on an unchecked step.
4. **Ground** — verify against the PDF with `[§/eq]` anchors (or web-checked primary sources). No fabrication.

**Antigravity-specific delivery**
- Inline interactive HTML/JS demos (sliders, simulators) for tough derivations or architectures; Mermaid/Excalidash diagrams for structures. Build them when they make a step absorbable, not as decoration.
- Voice Dictation (`Ctrl+M`) for messy thinking; Live Voice Mode (`/voice live`) for cold teach-backs and, in `spar`, defense sparring.
- OpenCode: same loop as text, one step per turn.

### Stage 4 — Consolidate & Compound

1. **Cold Teach-Back** — 3–5 sentences, no peeking at notes or paper. Record what feels obviously true and what still does not.
2. **2-Min Critique** — "Where would this break?" Name the assumption, failure mode, and any user critique already in the human zone.
3. Upsert `paper: <slug>` per `references/logseq_schema.md`: update Paper Card, Lineage, Claims/Limitations, Propositions, Cold Teach-Back; promote only high-signal/questioned highlights with `zotero://open-pdf/...?page=` deep links. **Re-emit the human zone verbatim.**
4. Upsert linked `concept: <topic-slug>` pages with atomic propositions, dependency chains, and mastery tags.
5. Write today's **one-line Daily Journal pulse** under `📚 [[Research & Learning Activity]]` via `--blocks-file`, no child bullets, real `[[links]]`.

---

## Mode B — Topic Learning (`topic`)

Direct Eero loop on a topic, no paper anchor required:

1. **Binary-Search Probe** — bracket current understanding; make the goal concrete ("what should feel obviously true by the end?").
2. **Minimal Dependency Mermaid DAG** — smallest tree from held facts to goal; prune held branches, ignore off-path tangents.
3. **Predict → Teach → Check** — one step per turn, mixed style, check + repair each step, foundations motivated not hedged.
4. **Extract** — upsert `concept: <topic-slug>` propositions/chains/mastery signals and today's one-line journal pulse.

## Mode C — Active Recall Practice (`practice`)

1. Query Logseq for a cluster of `#learn-concept` pages, prioritizing `#shaky` then `#covered` (skip `#recalled-cold` unless the user asks for maintenance).
2. Tune difficulty along **Composition of Demands × Familiarity of Cues**: start with few demands + familiar cues, raise one dimension at a time. Cold prompts beat recognition prompts.
3. Ask one question at a time; require Confidence % + reasoning. Give **minimal hints only** when stuck — the smallest cue that restarts the reasoning, never the answer.
4. Update mastery tags (`#shaky` ↔ `#recalled-cold`, `#covered` when newly extracted) and today's one-line journal pulse.

## Mode D — Thesis Synthesis & Defense Sparring (`thesis` / `spar`)

Read `references/thesis_mode.md` in full before starting. It covers cross-paper comparison matrices, `#thesis-gap` edges, advisor/committee sparring (including Antigravity Live Voice Mode `/voice live`), and the Zotero → Overleaf `references.bib` workflow via `zotero-bridge bibtex`.

## Logseq write checklist (every mode)

- Resolve graph first (default `logseq-sync`); pass `--graph "$GRAPH"`; never touch unrelated personal pages or tasks.
- Any block with `[[links]]`: `--blocks-file`, never `--content`.
- Tag **pages** (not section heading blocks) via `logseq upsert page --graph "$GRAPH" --page "<title>" --update-tags '["learn-concept" "shaky"]'` (explicit EDN vector). Only use block-level tags for `#thesis-gap` on gap-edge blocks.
- In-place section update: find heading id → remove obsolete children → insert fresh children. Dry-run with `--dry-run` first.
- Zero property drawers on journal/activity blocks. Privacy: scope reads to `#learn-paper`, `#learn-concept`, `#learn-thesis` and today's journal; never graph-wide `logseq list task`.
