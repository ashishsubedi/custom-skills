# 👁️ DeepSeek Vision Bridge (`deepseek-vis`)

Vision for text-only LLMs (DeepSeek etc). Recovers images pasted into agent harness sessions directly from harness storage — no clipboard — converts them to ASCII layouts, OCRs text (macOS Apple Vision / Tesseract), overlays text at spatial coordinates.

## Requirements
- Python 3.8+ + Pillow (`python3 -m pip install Pillow`)
- macOS: Xcode CLT for Apple Vision (`xcode-select --install`), optional
- Linux/Windows: [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)

## Install
```bash
git clone https://github.com/ashishsubedi/deepseek-vis.git
cd deepseek-vis
./install.sh             # interactive
./install.sh --target opencode   # or pi / all
```
Installs CLI to `~/.local/bin` and skill to:
- OpenCode → `~/.config/opencode/skills/deepseek-vis`
- Pi → `~/.pi/agent/skills/deepseek-vis`

Other harnesses: copy `SKILL.md`, `src/`, `bin/` into the skills dir manually.

## Usage
```bash
deepseek-vis                           # auto-harvest pasted images from active harness
deepseek-vis clipboard                 # harvest directly from OS clipboard
deepseek-vis --harness <opencode|pi>   # specify explicit harness
deepseek-vis a.png b.png               # specific image files
```

| Option | Description |
|--------|-------------|
| `-w <INT>` | ASCII width (default 90; 120 complex UIs, 60 icons) |
| `-m <mode>` | `hybrid` (default) / `ascii` / `ocr` / `overlay` |
| `--json` | raw JSON |
| `--no-edge` | disable edge-sharpening |

## Files
```
SKILL.md          # skill definition (auto-loaded by harnesses)
install.sh        # installer (opencode, pi)
bin/deepseek-vis  # CLI entry
src/
  main.py       # CLI + source resolution (harness > file paths)
  harvest.py    # recover pasted images from harness storage
  ascii.py      # image → ASCII layout
  ocr.py        # Apple Vision / Tesseract OCR
  overlay.py    # OCR text overlaid on ASCII grid
  mac_ocr.swift # macOS Apple Vision helper (compile-on-demand)
```

## Tests
```bash
python3 -m unittest discover tests
```

## Uninstall
```bash
rm ~/.local/bin/deepseek-vis
rm -rf ~/.config/opencode/skills/deepseek-vis ~/.pi/agent/skills/deepseek-vis
```

## License
[MIT](LICENSE)