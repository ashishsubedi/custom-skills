#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"

TARGET_CHOICE=""

# Parse flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET_CHOICE="$2"
            shift 2
            ;;
        --target=*)
            TARGET_CHOICE="${1#*=}"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo "🚀 DeepSeek Vision Bridge Setup"
echo "--------------------------------"

# 1. Python prerequisites
if ! python3 -c "import PIL" &>/dev/null; then
    echo "❌ Python Pillow is required."
    echo "   Install it with:  python3 -m pip install Pillow"
    exit 1
fi

# 2. Platform specific build checks
if [[ "$(uname)" == "Darwin" ]]; then
    if command -v swiftc &>/dev/null; then
        echo "🍏 macOS detected: Compiling native Apple Vision helpers..."
        mkdir -p "$PROJECT_DIR/bin"
        for helper in "$PROJECT_DIR"/src/*.swift; do
            name="$(basename "$helper" .swift)"
            swiftc -O "$helper" -o "$PROJECT_DIR/bin/$name" \
                || echo "ℹ️  Compile failed ($name); will fall back to Tesseract if installed."
        done
    else
        echo "🍏 macOS detected (no Swift compiler). Will use Tesseract fallback if installed."
        echo "   For best OCR, install Xcode Command Line Tools:  xcode-select --install"
    fi
else
    echo "🐧 Linux/Unix detected."
    if ! command -v tesseract &> /dev/null; then
        echo "ℹ️  Note: Tesseract OCR was not found on your system."
        echo "   ASCII layout processing will work natively, but OCR text extraction requires Tesseract."
        echo "   To install Tesseract on Linux:"
        echo "     • Ubuntu/Debian:  sudo apt install tesseract-ocr"
        echo "     • RHEL/Fedora:    sudo dnf install tesseract"
        echo "     • Arch Linux:     sudo pacman -S tesseract"
    else
        echo "✅ Found Tesseract OCR installed."
    fi
fi

# 3. Ensure bin script is executable
chmod +x "$PROJECT_DIR/bin/deepseek-vis"

# 3. Create symlink in user binary folder for PATH execution
mkdir -p "$BIN_DIR"
ln -sf "$PROJECT_DIR/bin/deepseek-vis" "$BIN_DIR/deepseek-vis"
echo "✅ Linked binary executable to $BIN_DIR/deepseek-vis"
echo ""

# 4. Framework Detection
DETECTED_NAMES=()
DETECTED_PATHS=()

add_target() {
    local name="$1"
    local path="$2"
    DETECTED_NAMES+=("$name")
    DETECTED_PATHS+=("$path")
}

# OpenCode (primary)
if [[ -d "$HOME/.config/opencode" ]] || [[ -d "$HOME/.local/share/opencode" ]] || command -v opencode &>/dev/null; then
    add_target "opencode" "$HOME/.config/opencode/skills/deepseek-vis"
fi

# Pi
if [[ -d "$HOME/.pi" ]] || [[ -d "$HOME/.agents" ]] || command -v pi &>/dev/null; then
    if [[ -d "$HOME/.pi" ]]; then
        add_target "pi" "$HOME/.pi/agent/skills/deepseek-vis"
    else
        add_target "pi" "$HOME/.agents/skills/deepseek-vis"
    fi
fi

if [[ ${#DETECTED_NAMES[@]} -eq 0 ]]; then
    echo "⚠️  No specific agent configuration directories detected."
    echo "   Installed CLI binary to $BIN_DIR/deepseek-vis."
    exit 0
fi

# 5. Handle Target Selection
SELECTED_INDICES=()

if [[ -n "$TARGET_CHOICE" ]]; then
    TARGET_LOWER="$(echo "$TARGET_CHOICE" | tr '[:upper:]' '[:lower:]')"
    if [[ "$TARGET_LOWER" == "all" ]]; then
        for i in "${!DETECTED_NAMES[@]}"; do
            SELECTED_INDICES+=("$i")
        done
    else
        for i in "${!DETECTED_NAMES[@]}"; do
            if [[ "${DETECTED_NAMES[$i]}" == "$TARGET_LOWER" ]]; then
                SELECTED_INDICES+=("$i")
            fi
        done
    fi
    if [[ ${#SELECTED_INDICES[@]} -eq 0 ]]; then
        echo "❌ Unknown target '$TARGET_CHOICE'."
        echo "   Available detected targets on your system: ${DETECTED_NAMES[*]} (or 'all')"
        exit 1
    fi
else
    # Interactive Selection if tty available
    if [ -t 0 ]; then
        echo "🔍 Detected the following AI Agent frameworks on your system:"
        for i in "${!DETECTED_NAMES[@]}"; do
            echo "   [$((i+1))] ${DETECTED_NAMES[$i]} (${DETECTED_PATHS[$i]})"
        done
        echo "   [a] All detected frameworks"
        echo ""
        read -p "Select framework to install into [1-${#DETECTED_NAMES[@]} or 'a']: " user_input

        if [[ "$user_input" == "a" || "$user_input" == "A" ]]; then
            for i in "${!DETECTED_NAMES[@]}"; do
                SELECTED_INDICES+=("$i")
            done
        elif [[ "$user_input" =~ ^[0-9]+$ ]] && [ "$user_input" -ge 1 ] && [ "$user_input" -le "${#DETECTED_NAMES[@]}" ]; then
            SELECTED_INDICES+=("$((user_input-1))")
        else
            echo "⚠️  Invalid selection. Defaulting to installing into all detected frameworks."
            for i in "${!DETECTED_NAMES[@]}"; do
                SELECTED_INDICES+=("$i")
            done
        fi
    else
        # Non-interactive default: install to all detected
        for i in "${!DETECTED_NAMES[@]}"; do
            SELECTED_INDICES+=("$i")
        done
    fi
fi

# 6. Perform Installation to Selected Frameworks
install_skill_to() {
    local target_dir="$1"
    mkdir -p "$target_dir/src" "$target_dir/bin"
    cp "$PROJECT_DIR/SKILL.md" "$target_dir/SKILL.md"
    cp "$PROJECT_DIR/package.json" "$target_dir/package.json" 2>/dev/null || true
    # Only source files (skip __pycache__, and mac_ocr recompiles on demand)
    for f in "$PROJECT_DIR"/src/*.py "$PROJECT_DIR"/src/*.swift; do
        cp "$f" "$target_dir/src/"
    done
    cp "$PROJECT_DIR/bin/deepseek-vis" "$target_dir/bin/"
    chmod +x "$target_dir/bin/deepseek-vis"
    echo "  ├─ ✅ Installed skill into: $target_dir"
}

echo "📦 Deploying skill to selected target(s):"
for idx in "${SELECTED_INDICES[@]}"; do
    install_skill_to "${DETECTED_PATHS[$idx]}"
done

echo ""
echo "🎉 Installation Complete!"
echo "   Test execution with:"
echo "     deepseek-vis <image_path>"
