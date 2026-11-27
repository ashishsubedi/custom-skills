#!/usr/bin/env bash
set -euo pipefail

# setup.sh — link the manim-explainer skill across agent harnesses and check tools
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="manim-explainer"
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

for hdir in "${HARNESS_DIRS[@]}"; do
  mkdir -p "$hdir"
  target="$hdir/$SKILL_NAME"
  rm -rf "$target"
  ln -sfn "$SKILL_DIR" "$target"
  echo "  🔗 $target"
done

echo ""
echo "=== Dependency check ==="
find_bin() {
  local label="$1" fallback="$2" cmd="$3"
  local resolved=""
  if [[ -n "$fallback" && -x "$fallback" ]]; then
    resolved="$fallback"
  elif command -v "$cmd" >/dev/null 2>&1; then
    resolved="$(command -v "$cmd")"
  fi
  if [[ -n "$resolved" ]]; then
    echo "  ✅ $label: $resolved"
  else
    echo "  ⚠️  $label not found (override via env or install into PATH)"
  fi
}

find_bin "manim" "${MANIM_BIN:-$HOME/.venvs/manim/bin/manim}" "manim"
find_bin "python3 (PIL/Manim)" "${MANIM_PY:-$HOME/.venvs/manim/bin/python}" "python3"
find_bin "python3 (TTS)" "${TTS_PY:-}" "python3"
find_bin "ffmpeg" "${FFMPEG_BIN:-}" "ffmpeg"
find_bin "ffprobe" "${FFPROBE_BIN:-}" "ffprobe"
find_bin "pdflatex" "${PDFLATEX_BIN:-/Library/TeX/texbin/pdflatex}" "pdflatex"

echo ""
echo "✅ $SKILL_NAME linked and ready."
