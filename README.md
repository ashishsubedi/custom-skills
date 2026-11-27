# Custom Agent Skills 🧠⚡️

A centralized repository of custom AI coding agent skills across harnesses: **Antigravity**, **OpenCode**, **Claude Code**, **Cursor**, **Codex**, and the open **Agent Skills (`npx skills`)** ecosystem.

Maintained by [@ashishsubedi](https://github.com/ashishsubedi).

---

## 📚 Skill Catalog

| Skill | Directory | Description | Harnesses |
| :--- | :--- | :--- | :--- |
| **`logseq_memory`** | [`skills/logseq_memory`](./skills/logseq_memory) | Human-first universal agent memory and cross-harness control center in Logseq 2.0. Orient at session start, sync branch narratives in-place, manage `#needs-human` reviews, and distill architecture. | Antigravity, Claude Code, Cursor, Codex, OpenCode |
| **`deepseek-vis`** | [`skills/deepseek-vis`](./skills/deepseek-vis) | Vision processing bridge for text-only LLMs. Recovers pasted images from harness session storage, converts to high-clarity ASCII layouts, and runs Apple Vision OCR with exact spatial coordinates. | Antigravity, Claude Code, Cursor, Codex, OpenCode, Pi |
| **`fittrack`** | [`skills/fittrack`](./skills/fittrack) | Fitness and nutrition tracking: log meals, inspect macros and calories, review workout adherence, and check AI coach targets via FitTrack MCP. | Antigravity, Claude Code, Cursor, Codex |
| **`research_learn`** | [`skills/research_learn`](./skills/research_learn) | Local-first paper deep-read, active-recall practice, and thesis synthesis harness backed by read-only `zotero-bridge` and scoped Logseq 2.0 DB pages. | Antigravity, Claude Code, Cursor, Codex, OpenCode |
| **`manim-explainer`** | [`skills/manim-explainer`](./skills/manim-explainer) | 3Blue1Brown-style animated explainer video pipeline for papers and topics (background-first storyboard, `edge-tts` `WordBoundary` sync, Manim safe-zone primitives, Pillow RGBA subtitle burn, and headless verification). | Antigravity, Claude Code, Cursor, Codex, OpenCode |

---

## 🚀 Quickstart & Installation

### Install All Skills

Link all custom skills in this repository into your active agent environments in one command:

```bash
./install.sh
```

This symlinks the skills (and delegates to per-skill `setup.sh` scripts where present) into:
- Universal Agents: `~/.agents/skills/`
- Google Antigravity: `~/.gemini/config/skills/` and `~/.gemini/antigravity/skills/`
- OpenCode: `~/.config/opencode/skills/`
- Claude Code: `~/.claude/skills/`
- Cursor: `~/.cursor/skills/`
- OpenAI Codex: `~/.codex/skills/`

### Install or Configure an Individual Skill

Each skill with a `setup.sh` can also be installed individually:

```bash
./skills/manim-explainer/setup.sh
./skills/research_learn/setup.sh
./skills/logseq_memory/setup.sh
```

---

## 📁 Repository Structure

```text
custom-skills/
├── README.md                         # Repository documentation and skill catalog
├── install.sh                        # Universal installer across agent harnesses
├── .gitignore                        # Ignored local files & OS metadata
└── skills/                           # Custom skills directory
    ├── deepseek-vis/                 # Vision/ASCII/OCR bridge for text-only models
    │   ├── SKILL.md
    │   ├── bin/
    │   └── src/
    ├── fittrack/                     # Nutrition & workout tracking via FitTrack MCP
    │   ├── SKILL.md
    │   ├── bridge.js
    │   ├── mcp_config.json
    │   └── plugin.json
    ├── logseq_memory/                # Logseq 2.0 Universal Agent Memory v2.1
    │   ├── SKILL.md
    │   ├── plugin.json
    │   ├── setup.sh
    │   ├── rules/AGENTS.md
    │   └── references/
    ├── manim-explainer/              # 3B1B paper/topic Manim + TTS video pipeline
    │   ├── SKILL.md
    │   ├── setup.sh
    │   ├── scripts/
    │   ├── references/
    │   └── tests/
    └── research_learn/               # Zotero + Logseq paper deep-read & sparring
        ├── SKILL.md
        ├── setup.sh
        ├── scripts/zotero_bridge.py
        ├── references/
        └── tests/
```

---

## 🛠️ Adding a New Custom Skill

To add a new skill to this repository:

1. **Create the skill folder**:
   ```bash
   mkdir -p skills/<new-skill-name>
   ```

2. **Add `SKILL.md`**:
   Ensure valid YAML frontmatter with `name` and `description`:
   ```markdown
   ---
   name: <new-skill-name>
   description: <Clear description explaining when and why the agent should activate this skill>
   ---

   # Skill Title

   Procedural guidance, guardrails, and instructions...
   ```

3. **Add bundled resources (optional)**:
   - `references/`: Reference manuals, schemas, or cheat sheets.
   - `scripts/`: Executable helper scripts.
   - `tests/`: Unit tests for helper scripts.
   - `setup.sh`: Optional per-skill installer.

4. **Link and test**:
   ```bash
   ./install.sh
   ```

5. **Commit and push**:
   ```bash
   git add skills/<new-skill-name>
   git commit -m "feat(skills): add <new-skill-name> skill"
   git push origin main
   ```

---

## 📄 License

Personal custom skills repository — created for autonomous workflow augmentation.
