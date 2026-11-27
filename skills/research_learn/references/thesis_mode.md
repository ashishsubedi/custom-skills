# Thesis Mode — Cross-Paper Synthesis & Defense Sparring (Phase 2)

Open this reference when the user invokes `thesis` or `spar`. Same Logseq graph (`logseq-sync`), same Zotero library — nothing new to install. Follow `references/logseq_schema.md` for every write (flat colon titles, `--blocks-file`, page-level tags via `logseq upsert page`, zero property drawers, `#learn-thesis` scope).

## 1. `thesis: <area-slug>` — cross-paper synthesis

**Scope.** Pick one thesis area (e.g. `efficient-llm-inference`). Gather every `paper: <slug>` tagged `#learn-paper` that belongs to the Zotero `Thesis` collection:

```bash
zotero-bridge search "" --collection Thesis --limit 100
logseq query --graph "$GRAPH" --output json --query \
'[:find (pull ?p [:db/id :block/title])
 :where [?t :block/name "learn-paper"] [?p :block/tags ?t]]'
```

**Build the comparison matrix** from the `## 🧪 Claims, Assumptions & Limitations` section of each paper page. Columns: paper (as `[[paper: <slug>]]`), claim, explicit assumption, reported result, failure mode, source anchor `[§/eq]`. Keep cells atomic and source-anchored — never invent a section number or equation; if unverified, write `[user hypothesis]` and check the PDF.

**Surface Tension / Gap edges.** A gap edge has the exact shape:

```
[[paper: A]] assumes X  ↔  [[paper: B]] shows X breaks under Y  →  #thesis-gap : <defensible question>
```

Rules:
- Both endpoints must be real `[[paper: ...]]` refs in the graph (write via `--blocks-file`).
- State the assumption `X` and the breaking condition `Y` concretely; "different setup" is not a gap.
- Each edge must yield one answerable research question, tagged `thesis-gap` on the block:

```bash
logseq upsert block --graph "$GRAPH" --target-page "thesis: efficient-llm-inference" \
  --pos last-child --blocks-file ./gap_edges.md \
  --update-tags '["thesis-gap"]'
logseq upsert page --graph "$GRAPH" --page "thesis: efficient-llm-inference" \
  --update-tags '["learn-thesis"]'
```

**Promote gaps to questions.** For every `#thesis-gap` edge, ask: what measurement or experiment would distinguish A's assumption from B's failure? Record it under `## 🎯 Research Question & Scope`. Keep the agent's job to logistics — the human supplies the judgment.

## 2. `spar` — Advisor / Committee Defense Sparring

Adapt Practice mode into adversarial viva/reviewer Q&A:

1. Select 2–3 papers from the thesis area (prioritize nodes tagged `#thesis-gap` or `#shaky`).
2. Generate one hard question per standing: reviewer (method validity), advisor (why this matters), committee (what breaks in practice). Demand **Confidence % + messy thinking** before giving feedback — same probe discipline as Paper mode.
3. Run one exchange at a time. Mixed Socratic + Expository: ask first, then repair the specific weak step. No walls of text. Never accept "I basically get it".
4. Log the exchange under `## 🛡️ Defense Q&A Log` on `thesis: <area-slug>`: question, best answer, remaining weak spot. Update mastery tags and today's journal pulse ([`📚 [[Research & Learning Activity]]`](logseq_schema.md#34-todays-daily-journal--one-line-pulse)).

**Antigravity Live Voice Mode.** For realistic defense pressure, run `/voice live` and conduct the sparring out loud:
- Let the user answer cold, with no paper or notes on screen.
- Listen for hedging ("I think maybe…") — that is the signal to stop and repair the shaky step, not to move on.
- Use Voice Dictation (`Ctrl+M`) for the user's messy thinking and for your own scratch hypotheses; clean up only after the reasoning is held.
- End with one sentence: the claim that now feels obviously true, and the one that still does not.

OpenCode has no voice mode — run the same sparring as text, one question per turn.

## 3. Zotero → Overleaf citations (zero Better BibTeX)

1. In Overleaf: **Upload → From Zotero** → select the Zotero `Thesis` collection. Overleaf generates `references.bib` and keeps it in sync with Zotero (one-click refresh).
2. Pull the matching Zotero BibTeX key for each cited paper:

```bash
zotero-bridge bibtex <itemKey>            # Zotero local API ?format=bibtex when running
zotero-bridge --sqlite-only bibtex <itemKey>   # offline synthesized entry when closed
# -> {"backend": ..., "itemKey": ..., "bibtexKey": "potamitis_2025_cache_saver", "bibtex": "..."}
```

3. Put that key into both `paper: <slug>` (`## 📌 Paper Card & Readiness` → `BibTeX / Overleaf Key`) and the thesis page's `## 📚 Citation Anchors` as `\cite{<key>}`. When Zotero is running, keys come from Zotero's own exporter and match Overleaf's synced `references.bib` exactly. The `--sqlite-only` fallback synthesizes a deterministic key for offline drafting — verify it against `references.bib` before writing `\cite{...}` into Overleaf.
4. Verify a claim's anchor before citing: `[§3.2, Eq. 4]` on the paper page must match the PDF. Never fabricate a key — if `bibtex` returns no key, leave `<unset>` and fix the Zotero metadata first.

Optional later upgrade: Better BibTeX can change key formatting without touching any Logseq page, since pages are keyed by deterministic slug + immutable Zotero `itemKey`, never by citekey.

## 4. Guardrails

- No full paper dumps; one reasoning step / one reviewer question per turn.
- No claim without `[§/eq]`, clickable `zotero://` anchor, or explicit `[user hypothesis]`.
- Never overwrite `## ✍️ My Notes, Ideas & Critiques` on any `paper:` page.
- Never touch unrelated personal notes/tasks in `logseq-sync` or write to Zotero DB files.
- Phase 2 is additive: if the user has not locked a thesis topic, stay in Paper/Topic/Practice modes.
