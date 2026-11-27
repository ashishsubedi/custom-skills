#!/usr/bin/env bash
set -euo pipefail

# install.sh — Link custom skills from this repository into AI coding agent harnesses
# Supported harnesses:
#  - Universal Agents (~/.agents/skills)
#  - Google Antigravity (~/.gemini/antigravity/skills)
#  - OpenCode (~/.config/opencode/skills)
#  - Claude Code (~/.claude/skills)
#  - Cursor (~/.cursor/skills)
#  - OpenAI Codex (~/.codex/skills)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"

echo "=== Installing Custom Agent Skills from $REPO_ROOT ==="

HARNESS_DIRS=(
  "$HOME/.agents/skills"
  "$HOME/.gemini/config/skills"
  "$HOME/.gemini/antigravity/skills"
  "$HOME/.config/opencode/skills"
  "$HOME/.claude/skills"
  "$HOME/.cursor/skills"
  "$HOME/.codex/skills"
)

# Ensure each harness skill root exists
for hdir in "${HARNESS_DIRS[@]}"; do
  mkdir -p "$hdir"
done

# Iterate over each skill directory in skills/ (skip alias symlinks)
for skill_path in "$SKILLS_DIR"/*; do
  [ -L "$skill_path" ] && continue
  if [ -d "$skill_path" ] && [ -f "$skill_path/SKILL.md" ]; then
    skill_name="$(basename "$skill_path")"
    echo ""
    echo "📦 Configuring skill: $skill_name..."

    # If the skill provides a dedicated setup script, execute it
    if [ -x "$skill_path/setup.sh" ]; then
      echo "  ⚙️  Running dedicated setup script for $skill_name..."
      (cd "$skill_path" && ./setup.sh < /dev/null) || {
        echo "  ⚠️  setup.sh for $skill_name reported a warning or exit code, continuing..."
      }
    else
      # Standard symlink across all harnesses
      for hdir in "${HARNESS_DIRS[@]}"; do
        target="$hdir/$skill_name"
        rm -rf "$target"
        ln -sfn "$skill_path" "$target"
        echo "  🔗 Linked to $target"
      done
    fi
  fi
done

echo ""
echo "🎉 All custom skills are now linked and available across your agent environments!"
