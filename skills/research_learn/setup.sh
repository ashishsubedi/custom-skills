#!/usr/bin/env bash
set -euo pipefail

# setup.sh — install the research_learn skill pack (called by ../../install.sh)
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="research_learn"
HARNESS_DIRS=(
  "$HOME/.agents/skills"
  "$HOME/.gemini/config/skills"
  "$HOME/.gemini/antigravity/skills"
  "$HOME/.config/opencode/skills"
  "$HOME/.claude/skills"
  "$HOME/.cursor/skills"
  "$HOME/.codex/skills"
)

echo "=== Setting up $SKILL_NAME ==="

# 1. Link the skill into every harness (install.sh delegates to this script).
for hdir in "${HARNESS_DIRS[@]}"; do
  mkdir -p "$hdir"
  target="$hdir/$SKILL_NAME"
  rm -rf "$target"
  ln -sfn "$SKILL_DIR" "$target"
  echo "  🔗 $target"
done

# 2. zotero-bridge CLI shim (read-only Zotero access, stdlib only).
mkdir -p "$HOME/.local/bin"
ln -sfn "$SKILL_DIR/scripts/zotero_bridge.py" "$HOME/.local/bin/zotero-bridge"
chmod +x "$SKILL_DIR/scripts/zotero_bridge.py"
echo "  🔗 $HOME/.local/bin/zotero-bridge"

# 3. Target Logseq graph preference (defaults to logseq-sync; never switch active graph).
mkdir -p "$HOME/.config/research_learn"
GRAPH_FILE="$HOME/.config/research_learn/graph"
if [[ -n "${RESEARCH_LOGSEQ_GRAPH:-}" ]]; then
  GRAPH="$RESEARCH_LOGSEQ_GRAPH"
  printf '%s\n' "$GRAPH" > "$GRAPH_FILE"
  echo "  📝 graph preference set from RESEARCH_LOGSEQ_GRAPH: $GRAPH"
else
  if [[ -f "$GRAPH_FILE" ]]; then
    GRAPH="$(tr -d '\r\n' < "$GRAPH_FILE")"
  elif [[ -f "$HOME/.config/logseq_memory/graph" ]]; then
    GRAPH="$(tr -d '\r\n' < "$HOME/.config/logseq_memory/graph")"
    printf '%s\n' "$GRAPH" > "$GRAPH_FILE"
  else
    GRAPH="logseq-sync"
    printf '%s\n' "$GRAPH" > "$GRAPH_FILE"
  fi
  [[ -n "$GRAPH" ]] || GRAPH="logseq-sync"
  echo "  📝 graph: $GRAPH ($GRAPH_FILE)"
fi

# 4. Create the graph if missing; do NOT call `logseq graph switch`.
if command -v logseq >/dev/null 2>&1; then
  if logseq graph list -o json 2>/dev/null | python3 -c '
import json, sys
data = json.load(sys.stdin).get("data", {})
sys.exit(0 if sys.argv[1] in data.get("graphs", []) else 1)
' "$GRAPH"; then
    echo "  ✅ Logseq graph '$GRAPH' exists"
  else
    echo "  ➕ Creating Logseq graph '$GRAPH' (active graph unchanged)"
    logseq graph create --graph "$GRAPH"
  fi

  # 5. Bootstrap the canonical tag vocabulary.
  for tag in learn-paper learn-concept learn-thesis covered shaky recalled-cold thesis-gap; do
    logseq upsert tag --graph "$GRAPH" --name "$tag" >/dev/null
  done
  echo "  🏷️  Tags ready in '$GRAPH'"
else
  echo "  ⚠️  logseq CLI not found; skipping graph/tag setup (install it and re-run)"
fi

# 6. OpenCode slash commands (only when OpenCode config exists).
if [[ -d "$HOME/.config/opencode" ]]; then
  CMD_DIR="$HOME/.config/opencode/commands"
  mkdir -p "$CMD_DIR"
  cat > "$CMD_DIR/paper.md" <<'EOF'
---
description: Deep-read a Zotero paper (research_learn paper mode)
---
Use the `research_learn` skill in **paper** mode. Target: `$ARGUMENTS`.
Pull metadata/highlights with `zotero-bridge`, run the Pre-Flight Readiness Gate, teach one reasoning step at a time, then upsert `paper: <slug>` and today's journal pulse in Logseq (`logseq-sync`). Ask for Reading Depth (L1/L2/L3) if not specified.
EOF
  cat > "$CMD_DIR/learn.md" <<'EOF'
---
description: Learn a topic with the minimal dependency DAG (research_learn topic mode)
---
Use the `research_learn` skill in **topic** mode. Topic: `$ARGUMENTS`.
Probe current understanding, draw the minimal dependency Mermaid DAG, run Predict → Teach → Check one step at a time, then extract `concept: <topic-slug>` and today's journal pulse in Logseq (`logseq-sync`).
EOF
  cat > "$CMD_DIR/practice.md" <<'EOF'
---
description: Active-recall practice on research concepts (research_learn practice mode)
---
Use the `research_learn` skill in **practice** mode. Cluster: `$ARGUMENTS`.
Query Logseq (`logseq-sync`) for `#shaky`/`#covered` `#learn-concept` pages, tune difficulty (Composition of Demands × Cue Familiarity), minimal hints only, then update page mastery tags and today's journal pulse.
EOF
  echo "  ⌨️  OpenCode commands installed in $CMD_DIR"
fi

echo "🎉 $SKILL_NAME setup complete."
