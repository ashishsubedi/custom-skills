#!/usr/bin/env bash
set -euo pipefail

# setup.sh — Cross-platform setup for Logseq Agent Memory v2.1
# Supports selecting an existing graph or creating a new dedicated agent graph (e.g. logseq-agent).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
CONFIG_DIR="$HOME/.config/logseq_memory"
LEGACY_CONFIG_DIR="$HOME/.config/logseq-memory"
CONFIG_FILE="$CONFIG_DIR/graph"
OS_TYPE="$(uname -s)"
LOGSEQ_CMD="$(command -v logseq || echo "$LOCAL_BIN/logseq")"

# Default graph preference
SELECTED_GRAPH="${LOGSEQ_GRAPH:-}"

# Parse optional command-line flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --graph|-g)
      SELECTED_GRAPH="$2"
      shift 2
      ;;
    --new-graph)
      SELECTED_GRAPH="${2:-logseq-agent}"
      CREATE_NEW=true
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--graph <graph-name>] [--new-graph [<graph-name>]]"
      exit 1
      ;;
  esac
done

echo "============================================================"
echo "  Logseq Agent Memory v2.1 Setup (OS: $OS_TYPE)"
echo "============================================================"

# 1. Clean up deprecated CLI wrapper if present
if [ -e "$LOCAL_BIN/logseq-mem" ] || [ -L "$LOCAL_BIN/logseq-mem" ]; then
  rm -f "$LOCAL_BIN/logseq-mem"
  echo "🧹 Removed deprecated $LOCAL_BIN/logseq-mem"
fi

# 2. Graph selection (Interactive if terminal attached and graph not specified)
mkdir -p "$CONFIG_DIR"

if [ -z "$SELECTED_GRAPH" ]; then
  # Read existing stored preference if available
  STORED_GRAPH=""
  if [ -f "$CONFIG_FILE" ]; then
    STORED_GRAPH="$(cat "$CONFIG_FILE" | tr -d '[:space:]')"
  elif [ -f "$LEGACY_CONFIG_DIR/graph" ]; then
    STORED_GRAPH="$(cat "$LEGACY_CONFIG_DIR/graph" | tr -d '[:space:]')"
  fi

  # Discover available graphs via CLI
  AVAILABLE_GRAPHS=()
  if command -v logseq >/dev/null 2>&1 || [ -x "$LOGSEQ_CMD" ]; then
    RAW_GRAPHS="$("$LOGSEQ_CMD" graph list --output json 2>/dev/null || true)"
    if [ -n "$RAW_GRAPHS" ]; then
      while IFS= read -r g; do
        [ -n "$g" ] && AVAILABLE_GRAPHS+=("$g")
      done < <(echo "$RAW_GRAPHS" | grep -o '"graph-name":"[^"]*"' | cut -d'"' -f4 || true)
    fi
  fi

  if [ -t 0 ] && [ ${#AVAILABLE_GRAPHS[@]} -gt 0 ]; then
    echo ""
    echo "Graph Configuration:"
    echo "  1) Use an existing graph"
    echo "  2) Create and use a new dedicated graph (e.g. logseq-agent)"
    read -r -p "Select option [1/2] (default: 1): " OPT_CHOICE
    OPT_CHOICE="${OPT_CHOICE:-1}"

    if [ "$OPT_CHOICE" = "2" ]; then
      read -r -p "Enter new graph name (default: logseq-agent): " NEW_NAME
      SELECTED_GRAPH="${NEW_NAME:-logseq-agent}"
      echo "📦 Creating new graph '$SELECTED_GRAPH'..."
      "$LOGSEQ_CMD" graph create --graph "$SELECTED_GRAPH" 2>/dev/null || true
    else
      echo ""
      echo "Available graphs:"
      for i in "${!AVAILABLE_GRAPHS[@]}"; do
        echo "  $((i+1))) ${AVAILABLE_GRAPHS[$i]}"
      done
      DEFAULT_INDEX=1
      # Prefer logseq-sync as default if present
      for i in "${!AVAILABLE_GRAPHS[@]}"; do
        if [ "${AVAILABLE_GRAPHS[$i]}" = "logseq-sync" ]; then
          DEFAULT_INDEX=$((i+1))
          break
        fi
      done
      read -r -p "Select graph [1-${#AVAILABLE_GRAPHS[@]}] (default: $DEFAULT_INDEX): " G_INDEX
      G_INDEX="${G_INDEX:-$DEFAULT_INDEX}"
      if [[ "$G_INDEX" =~ ^[0-9]+$ ]] && [ "$G_INDEX" -ge 1 ] && [ "$G_INDEX" -le ${#AVAILABLE_GRAPHS[@]} ]; then
        SELECTED_GRAPH="${AVAILABLE_GRAPHS[$((G_INDEX-1))]}"
      else
        SELECTED_GRAPH="${G_INDEX}"
      fi
    fi
  else
    # Non-interactive fallback
    SELECTED_GRAPH="${STORED_GRAPH:-logseq-sync}"
  fi
fi

# Persist chosen graph configuration
echo "$SELECTED_GRAPH" > "$CONFIG_FILE"
echo "{\"graph\":\"$SELECTED_GRAPH\",\"updated\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$CONFIG_DIR/config.json"
mkdir -p "$LEGACY_CONFIG_DIR"
echo "$SELECTED_GRAPH" > "$LEGACY_CONFIG_DIR/graph"
echo "📁 Graph set to: '$SELECTED_GRAPH' (saved in $CONFIG_FILE)"

# Switch CLI default graph
if command -v logseq >/dev/null 2>&1 || [ -x "$LOGSEQ_CMD" ]; then
  "$LOGSEQ_CMD" graph switch --graph "$SELECTED_GRAPH" 2>/dev/null || true
fi

# 3. Install official logseq-cli skill using 'logseq skill install'
TARGET_SKILL_DIR="$HOME/.agents/skills/logseq-cli"
INSTALLED_OK=false

if [ -x "$LOGSEQ_CMD" ] || command -v logseq >/dev/null 2>&1; then
  echo "📦 Installing official logseq-cli skill via '$LOGSEQ_CMD skill install --global'..."
  if "$LOGSEQ_CMD" skill install --global >/dev/null 2>&1; then
    INSTALLED_OK=true
    echo "✅ Official logseq-cli skill installed via logseq CLI"
  fi
fi

# Fallback: if 'logseq skill install' could not locate source in asar/runtime, locate and copy portably
if [ "$INSTALLED_OK" = false ] && [ ! -f "$TARGET_SKILL_DIR/SKILL.md" ]; then
  CANDIDATE_DIRS=(
    "/Applications/Logseq.app/Contents/Resources/.agents/skills/logseq-cli"
    "/opt/Logseq/resources/.agents/skills/logseq-cli"
    "/usr/share/logseq/resources/.agents/skills/logseq-cli"
    "${XDG_DATA_HOME:-$HOME/.local/share}/logseq/resources/.agents/skills/logseq-cli"
    "$HOME/Logseq/.agents/skills/logseq-cli"
  )

  FOUND_SRC=""
  for dir in "${CANDIDATE_DIRS[@]}"; do
    if [ -d "$dir" ] && [ -f "$dir/SKILL.md" ]; then
      FOUND_SRC="$dir"
      break
    fi
  done

  # Search system roots if not in standard candidate dirs
  if [ -z "$FOUND_SRC" ]; then
    SEARCH_ROOTS=()
    [ -d "/Applications" ] && SEARCH_ROOTS+=("/Applications")
    [ -d "/opt" ] && SEARCH_ROOTS+=("/opt")
    [ -d "/usr/share" ] && SEARCH_ROOTS+=("/usr/share")
    [ -d "$HOME/.local" ] && SEARCH_ROOTS+=("$HOME/.local")
    
    if [ ${#SEARCH_ROOTS[@]} -gt 0 ]; then
      FOUND_SRC="$(find "${SEARCH_ROOTS[@]}" -maxdepth 6 -type d -name "logseq-cli" 2>/dev/null | head -n 1 || true)"
    fi
  fi

  if [ -n "$FOUND_SRC" ] && [ -f "$FOUND_SRC/SKILL.md" ]; then
    mkdir -p "$HOME/.agents/skills"
    cp -R "$FOUND_SRC" "$HOME/.agents/skills/"
    if [ -x "$LOGSEQ_CMD" ] || command -v logseq >/dev/null 2>&1; then
      "$LOGSEQ_CMD" skill install --global >/dev/null 2>&1 || true
    fi
    echo "✅ Installed logseq-cli skill from $FOUND_SRC"
  fi
fi

# 4. Symlink logseq-memory skill and global rules across agent harnesses
link_path() {
  local target_path="$1"
  local harness_name="$2"
  mkdir -p "$(dirname "$target_path")"
  rm -rf "$target_path"
  ln -sfn "$SCRIPT_DIR" "$target_path"
  echo "✅ Linked skill to $harness_name ($target_path)"
}

link_file() {
  local src_file="$1"
  local target_file="$2"
  local desc="$3"
  mkdir -p "$(dirname "$target_file")"
  rm -f "$target_file"
  ln -sfn "$src_file" "$target_file"
  echo "✅ Linked $desc ($target_file)"
}

# 4.1 Universal Agents standard (~/.agents)
link_path "$HOME/.agents/skills/logseq_memory" "Universal Agents (~/.agents/skills/logseq_memory)"
rm -rf "$HOME/.agents/skills/logseq-memory" "$HOME/.agents/skills/agent-memory" 2>/dev/null || true
link_file "$SCRIPT_DIR/rules/AGENTS.md" "$HOME/.agents/rules/logseq_memory.md" "universal global rule to ~/.agents"
rm -f "$HOME/.agents/rules/logseq-memory.md" 2>/dev/null || true

# 4.2 Google Antigravity (~/.gemini)
# Single canonical plugin bundle provides both the skill and the auto-sync AGENTS.md rule across all workspaces
mkdir -p "$HOME/.gemini/config/plugins/logseq_memory/rules"
mkdir -p "$HOME/.gemini/config/plugins/logseq_memory/skills"
ln -sfn "$SCRIPT_DIR/plugin.json" "$HOME/.gemini/config/plugins/logseq_memory/plugin.json"
ln -sfn "$SCRIPT_DIR/rules/AGENTS.md" "$HOME/.gemini/config/plugins/logseq_memory/rules/AGENTS.md"
ln -sfn "$SCRIPT_DIR" "$HOME/.gemini/config/plugins/logseq_memory/skills/logseq_memory"
rm -rf "$HOME/.gemini/config/plugins/logseq-memory" 2>/dev/null || true

# Also maintain single direct skill link in ~/.gemini/config/skills/ & ~/.gemini/antigravity/skills/
ln -sfn "$SCRIPT_DIR" "$HOME/.gemini/config/skills/logseq_memory"
ln -sfn "$SCRIPT_DIR" "$HOME/.gemini/antigravity/skills/logseq_memory"
rm -rf "$HOME/.gemini/config/skills/logseq-memory" "$HOME/.gemini/antigravity/skills/logseq-memory" \
  "$HOME/.gemini/config/skills/agent-memory" "$HOME/.gemini/antigravity/skills/agent-memory" 2>/dev/null || true
echo "✅ Installed global Antigravity plugin (~/.gemini/config/plugins/logseq_memory)"

# 4.3 Claude Code (~/.claude)
link_path "$HOME/.claude/skills/logseq_memory" "Claude Code (logseq_memory)"
rm -rf "$HOME/.claude/skills/logseq-memory" "$HOME/.claude/skills/agent-memory" 2>/dev/null || true
if [ ! -f "$HOME/.claude/CLAUDE.md" ] && [ ! -L "$HOME/.claude/CLAUDE.md" ]; then
  link_file "$SCRIPT_DIR/rules/AGENTS.md" "$HOME/.claude/CLAUDE.md" "global rule to Claude Code"
fi

# 4.4 Cursor (~/.cursor)
link_path "$HOME/.cursor/skills/logseq_memory" "Cursor (logseq_memory)"
rm -rf "$HOME/.cursor/skills/logseq-memory" "$HOME/.cursor/skills/agent-memory" 2>/dev/null || true
if [ ! -f "$HOME/.cursorrules" ] && [ ! -L "$HOME/.cursorrules" ]; then
  link_file "$SCRIPT_DIR/rules/AGENTS.md" "$HOME/.cursorrules" "global rule to Cursor"
fi
mkdir -p "$HOME/.cursor/rules"
link_file "$SCRIPT_DIR/rules/AGENTS.md" "$HOME/.cursor/rules/logseq_memory.mdc" "global rule to ~/.cursor/rules/logseq_memory.mdc"

# 4.5 OpenAI Codex (~/.codex)
link_path "$HOME/.codex/skills/logseq_memory" "Codex (logseq_memory)"
rm -rf "$HOME/.codex/skills/logseq-memory" "$HOME/.codex/skills/agent-memory" 2>/dev/null || true
mkdir -p "$HOME/.codex/rules"
link_file "$SCRIPT_DIR/rules/AGENTS.md" "$HOME/.codex/rules/logseq_memory.md" "global rule to Codex"
rm -f "$HOME/.codex/rules/logseq-memory.md" 2>/dev/null || true
link_file "$SCRIPT_DIR/rules/AGENTS.md" "$HOME/.codex/AGENTS.md" "global AGENTS.md rule to ~/.codex"

# 4.6 OpenCode (~/.config/opencode)
link_path "$HOME/.config/opencode/skills/logseq_memory" "OpenCode (logseq_memory)"
rm -rf "$HOME/.config/opencode/skills/logseq-memory" "$HOME/.config/opencode/skills/agent-memory" 2>/dev/null || true
mkdir -p "$HOME/.config/opencode/rules"
link_file "$SCRIPT_DIR/rules/AGENTS.md" "$HOME/.config/opencode/rules/logseq_memory.md" "global rule to OpenCode (~/.config/opencode/rules/logseq_memory.md)"

OPENCODE_AGENTS="$HOME/.config/opencode/AGENTS.md"
if [ -f "$OPENCODE_AGENTS" ]; then
  python3 -c '
import sys, re
agents_path, rules_path = sys.argv[1], sys.argv[2]
with open(agents_path, "r", encoding="utf-8") as f: content = f.read()
with open(rules_path, "r", encoding="utf-8") as f: rules = f.read().strip()
block = f"<!-- logseq-memory-begin -->\n{rules}\n<!-- logseq-memory-end -->"
if "<!-- logseq-memory-begin -->" in content:
    new_content = re.sub(r"<!-- logseq-memory-begin -->.*?<!-- logseq-memory-end -->", block, content, flags=re.DOTALL)
else:
    new_content = content.rstrip() + f"\n\n{block}\n"
with open(agents_path, "w", encoding="utf-8") as f: f.write(new_content)
' "$OPENCODE_AGENTS" "$SCRIPT_DIR/rules/AGENTS.md"
  echo "✅ Injected Logseq rules block into OpenCode ($OPENCODE_AGENTS)"
elif [ -d "$HOME/.config/opencode" ]; then
  link_file "$SCRIPT_DIR/rules/AGENTS.md" "$OPENCODE_AGENTS" "global AGENTS.md rule to OpenCode"
fi

# Also link logseq-cli into Antigravity & OpenCode global config if present
if [ -d "$HOME/.agents/skills/logseq-cli" ]; then
  mkdir -p "$HOME/.gemini/config/skills"
  ln -sfn "$HOME/.agents/skills/logseq-cli" "$HOME/.gemini/config/skills/logseq-cli"
  echo "✅ Linked logseq-cli skill to Antigravity (~/.gemini/config/skills/logseq-cli)"
  if [ -d "$HOME/.config/opencode" ]; then
    mkdir -p "$HOME/.config/opencode/skills"
    ln -sfn "$HOME/.agents/skills/logseq-cli" "$HOME/.config/opencode/skills/logseq-cli"
    echo "✅ Linked logseq-cli skill to OpenCode (~/.config/opencode/skills/logseq-cli)"
  fi
fi

# 5. Provision Agent Command Center if missing in selected graph
if [ -x "$LOGSEQ_CMD" ] || command -v logseq >/dev/null 2>&1; then
  CHECK_CC="$("$LOGSEQ_CMD" show --graph "$SELECTED_GRAPH" --page "Agent Command Center" --output json 2>/dev/null || true)"
  if [[ "$CHECK_CC" == *"page-not-found"* ]]; then
    echo "🤖 Provisioning Agent Command Center in '$SELECTED_GRAPH'..."
    "$LOGSEQ_CMD" upsert page --graph "$SELECTED_GRAPH" --name "Agent Command Center" --output json >/dev/null 2>&1 || true

    H1=$("$LOGSEQ_CMD" upsert block --graph "$SELECTED_GRAPH" --target-page "Agent Command Center" --pos last-child --blocks "- ## 🚨 Needs Human Review" --output json 2>/dev/null | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
    if [ -n "$H1" ]; then
      Q1=$("$LOGSEQ_CMD" upsert block --graph "$SELECTED_GRAPH" --target-id "$H1" --pos sibling --content "" --update-tags '["Query"]' --output json 2>/dev/null | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
      [ -n "$Q1" ] && "$LOGSEQ_CMD" upsert block --graph "$SELECTED_GRAPH" --id "$Q1" --update-properties '{:logseq.property/query "(and (task \"In Review\") (tags [[agent_task]]))"}' >/dev/null 2>&1 || true

      H2=$("$LOGSEQ_CMD" upsert block --graph "$SELECTED_GRAPH" --target-id "$Q1" --pos sibling --blocks "- ## 🔄 Currently Running" --output json 2>/dev/null | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
      Q2=$("$LOGSEQ_CMD" upsert block --graph "$SELECTED_GRAPH" --target-id "$H2" --pos sibling --content "" --update-tags '["Query"]' --output json 2>/dev/null | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
      [ -n "$Q2" ] && "$LOGSEQ_CMD" upsert block --graph "$SELECTED_GRAPH" --id "$Q2" --update-properties '{:logseq.property/query "(and (task \"Doing\") (tags [[agent_task]]))"}' >/dev/null 2>&1 || true

      H3=$("$LOGSEQ_CMD" upsert block --graph "$SELECTED_GRAPH" --target-id "$Q2" --pos sibling --blocks "- ## 📥 Delegation Queue" --output json 2>/dev/null | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
      Q3=$("$LOGSEQ_CMD" upsert block --graph "$SELECTED_GRAPH" --target-id "$H3" --pos sibling --content "" --update-tags '["Query"]' --output json 2>/dev/null | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
      [ -n "$Q3" ] && "$LOGSEQ_CMD" upsert block --graph "$SELECTED_GRAPH" --id "$Q3" --update-properties '{:logseq.property/query "(and (task \"Todo\") (tags [[agent_task]]))"}' >/dev/null 2>&1 || true
    fi
    echo "✅ Agent Command Center provisioned"
  fi
fi

echo ""
echo "🎉 Setup complete! All harnesses now have the v2.1 pure logseq-memory skill."
echo "Active graph: '$SELECTED_GRAPH'"
