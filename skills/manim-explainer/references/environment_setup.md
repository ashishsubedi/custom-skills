# Environment, Setup & Troubleshooting Reference

## 1. Prerequisites & Discovery

Discover installed binaries dynamically (override with environment variables when using isolated virtual environments):

```bash
MANIM_BIN="${MANIM_BIN:-$(command -v manim || echo "$HOME/.venvs/manim/bin/manim")}"
MANIM_PY="${MANIM_PY:-$(command -v python3)}"
TTS_PY="${TTS_PY:-$(command -v python3)}"
```

| Component | Purpose | Typical Packages / Tools |
| :--- | :--- | :--- |
| **Manim Renderer** | 2D mathematical & diagram animation | `manim` (Community Edition `>=0.18`), `numpy`, `scipy` |
| **Subtitle & Image Engine** | Pill subtitle rendering & keyframe audit | `Pillow` (`PIL`) |
| **LaTeX (`MathTex`)** | Vectorized math equations (`MathTex`, `Tex`) | TeX Live / MacTeX (`pdflatex`, `latex`, `dvisvgm`) |
| **TTS Engine** | Word-synced speech + `WordBoundary` cues | `edge-tts` (primary) or `kokoro` (local offline fallback) |
| **PDF Reader** | Primary-source text & diagram inspection | `pymupdf` (`fitz`), `pypdf`, or `pdftotext` |
| **Media Muxer** | Audio delay mix, loudness norm, overlay, probe | `ffmpeg`, `ffprobe` |

### Fresh Setup Example (macOS / Linux)

```bash
# 1. Create a dedicated venv for Manim + TTS + PDF tools
python3 -m venv ~/.venvs/manim
~/.venvs/manim/bin/pip install manim pillow numpy scipy edge-tts pymupdf

# 2. System media + LaTeX dependencies (macOS Homebrew example)
brew install ffmpeg
# Install BasicTeX / MacTeX (or texlive-latex-extra + dvisvgm on Linux) for MathTex
```

### Portable Fonts
- **Subtitles (`assemble_video.py`)**: Checks `--font`, then `/System/Library/Fonts/SFNS.ttf` (macOS), `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` (Linux), and falls back to Pillow's built-in font.
- **Manim Labels (`manim_primitives.py`)**: Defaults to `MANIM_FONT_SANS` (`SF Pro Display` on macOS, `Sans` elsewhere) and `MANIM_FONT_MONO` (`Menlo` on macOS, `Monospace` elsewhere). Override via environment variables if desired.

---

## 2. Background Execution Discipline (Non-Disruptive)

- **Never open GUI windows**: Never pass `-p` / `--preview` to `manim`, and never launch desktop media players during verification.
- **CPU priority**: Prefix `build_audio.py`, `manim render`, and `assemble_video.py` with `nice -n 10` and redirect output (`> render.log 2>&1`) so interactive laptop usage stays responsive.
- **Two-stage render loop**:
  1. **Smoke pass (`480p @ 15fps`)**: `nice -n 10 "$MANIM_BIN" render -q l -r 854,480 --fps 15 scene.py <SceneClass>`
     - Extract 2 frames per scene (`30%`, `78%`) and inspect with `read_file`.
  2. **Final pass (`1080p @ 30fps`)**: `nice -n 10 "$MANIM_BIN" render -r 1920,1080 --fps 30 scene.py <SceneClass>`
     - Run `assemble_video.py`, then inspect `verification.txt` and final 1080p frames.

---

## 3. Known Sharp Edges & Fixes

1. **`ffmpeg` `ass=` / `drawtext=` filter fails (`No option name near 'subtitles.ass'`)**:
   - Minimal `ffmpeg` builds (including default Homebrew `ffmpeg`) often omit `libass` and `libfreetype`. `scripts/assemble_video.py` avoids both by pre-rendering each subtitle cue once via Pillow onto a `1920x155` RGBA strip and piping raw RGBA frames into `ffmpeg`'s `overlay=0:925` filter.
2. **Manim `Sector` keyword error (`got multiple values for 'outer_radius'`)**:
   - Recent Manim Community versions forward `radius` to `AnnularSector(outer_radius=...)`. Always call `Sector(radius=..., ...)`, never `outer_radius=...`.
3. **Ghost objects persisting across scenes**:
   - `ReplacementTransform(old, new)` removes `old` from `Scene.mobjects` and inserts `new` outside `self.stage`. Always clear scenes via `Group(*self.mobjects)` + `self.clear()` (`SubbeatScene.clear_stage()`).
4. **Offline TTS fallback (`Kokoro-82M`)**:
   - If running offline without `edge-tts`, local neural TTS (`kokoro`) works at `24 kHz` in a single persistent process, using word-proportional clause timing when `WordBoundary` metadata is absent.
5. **Technical acronyms in TTS**:
   - Neural voices can misread bare uppercase tokens (`vLLM`, `TTFT`, `HKVD`, `PML`). Keep `"tts"` strings phonetic (`v-L-L-M`, `T-T-F-T`, `H-K-V-D`, `P-M-L`) and `"sub"` strings clean (`vLLM`, `TTFT`, `HKVD`, `PML`).
