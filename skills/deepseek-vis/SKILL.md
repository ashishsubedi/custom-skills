---
name: deepseek-vis
description: >
  Vision processing bridge for text-only models (e.g. DeepSeek). Recovers images pasted into the
  active agent harness session directly from harness storage — with no clipboard dependency, so
  multiple pasted images are all captured — converts them to high-clarity ASCII art layouts,
  performs native macOS Apple Vision OCR (or Tesseract fallback), and overlays recognized text onto
  exact spatial coordinates in the ASCII grid. Use whenever you need to analyze, inspect, read, or
  describe images: UI screenshots, diagrams, mockups, forms, documents, error screens, or ANY image
  pasted into the harness or provided as a file path. Ideal when a text-only model cannot see image
  input directly. Works across harnesses (OpenCode, Pi, and any registered harvester) and falls
  back through them automatically.
---

# DeepSeek Vision Bridge Skill

This skill equips text-only LLMs (such as DeepSeek) with visual comprehension by encoding images into structured ASCII layouts combined with OCR text and spatial coordinates.

The ASCII art preserves layout structure (containers, bounding boxes, shapes, and their spatial arrangement). The OCR table provides every recognized text string with its position and confidence. Together they let you reason about an image's content, layout, and text without ever seeing pixels.

## When To Use

Trigger this skill whenever:
- The user pastes an image into the harness and you receive `[Image N]` markers or cannot read the image directly.
- The user asks you to look at, analyze, read, describe, or interpret a screenshot, UI mockup, diagram, document, or any image.
- You need to extract text from an image (forms, buttons, labels, error messages, logs).
- The user references an image file path and wants it understood or reproduced (e.g. turn a mockup into code).

Do NOT use for: images already readable as text (SVG treated as text), or when the model already has vision and can see the image directly.

## How to Execute Vision Analysis

### 1. From Pasted Images (any harness) — preferred

When the user pastes one or more images into the harness, recover **all** of them from harness storage by passing the harness you are currently running under:

```bash
deepseek-vis --harness opencode
# OR when running under Pi:
deepseek-vis --harness pi
```

Always pass the harness you are operating from. With no explicit file paths, `deepseek-vis` finds every image pasted into the current session:

- **OpenCode (v1):** reads the active session's `part` table in `~/.local/share/opencode/opencode.db` and extracts the raw pixels of every image attachment.
- **Pi:** reads `$PI_SESSION_FILE` and loads each `pi-clipboard-*.png` file referenced by the paste path.
- **System Clipboard:** captures images directly from OS clipboard (`deepseek-vis clipboard` or `--harness clipboard`).

If you omit `--harness` or pass an unknown harness name, `deepseek-vis` automatically evaluates all known harvesters and selects candidate images from the most recently updated source. Passing `clipboard` as a positional argument (`deepseek-vis clipboard`) harvests directly from the OS clipboard.

Multiple pasted images are all captured and labeled `Image 1/N`, `Image 2/N`, ... each with its own ASCII layout and OCR table. **Do not run the command once per pasted image** — run it once and process every section.

If no images are recovered, tell the user and ask them to re-paste the image or provide the file path.

### 2. From an Image File Path

When the image is at a known path (user gave `~/Desktop/shot.png`, or `@`-referenced a file):

```bash
deepseek-vis /path/to/image.png [more.png ...]
```

Any number of file paths are supported; each is analyzed and labeled `Image 1/N`, `Image 2/N`, etc.

### Command Line Options

- `-w`, `--width <INT>`: Target ASCII width in characters (default: `90`). Use `120` for complex UIs/diagrams, `60` for simple icons/logos.
- `-m`, `--mode <hybrid|overlay|ascii|ocr>`:
  - `hybrid` (default): ASCII layout with embedded text overlay + OCR table.
  - `overlay`: ASCII grid with OCR text embedded directly at exact spatial coordinates.
  - `ascii`: pure visual layout ASCII art.
  - `ocr`: pure text and bounding boxes table.
- `--harness <name>`: which agent harness pasted images came from (opencode, pi, or any registered harness). Falls back through all known harnesses if unknown or omitted.
- `--json`: output raw JSON data for programmatic consumption.
- `--no-edge`: disable contrast/edge sharpening filter.

## Interpreting the Vision Output

1. **ASCII Layout & Overlay:**
   - Lines, boxes, borders, and shapes represent visual container boundaries.
   - Text rendered inside ASCII blocks indicates actual UI buttons, headers, labels, or text fields positioned at that exact visual location.
   - Dense characters (`@`, `#`, `%`) = dark regions; sparse characters (`.`, `:`) = light/empty regions.

2. **OCR Spatial Table:**
   - **Region:** qualitative placement (`Top-Left`, `Center-Right`, `Bottom-Center`, etc.).
   - **Position:** character grid coordinates `(col,row)` matching the ASCII grid so you can locate text in the layout.
   - **Conf:** OCR accuracy percentage — treat low-confidence text cautiously.

3. **Synthesis & Response Strategy:**
   - Describe the overall layout structure first (e.g. "dialog box with a top header and two action buttons").
   - Reference exact text and its position (e.g. "center-left is a 'SUBMIT' button, right of it a 'CANCEL' button").
   - When reproducing a UI, translate both the text content AND the spatial arrangement from the ASCII layout.
   - If OCR misses text, infer from the ASCII shapes and say what you inferred vs read.

## Output Format Example

```
## Image Analysis: `Pasted Image`
**Grid:** 90x22

### ASCII Layout & Overlay
<ASCII art with text embedded at position>

### OCR Text & Coordinates
| # | Region | Position | Text | Conf |
|---|--------|----------|------|------|
| 1 | Top-Left | (5,2) | `DeepSeek Vision Test` | 100% |
```

## Notes

- Works offline; ASCII conversion is local, OCR is local (Apple Vision on macOS, Tesseract elsewhere).
- Requires Python 3.8+ and Pillow. On Linux/Windows, Tesseract must be installed for OCR; ASCII layout works without it.
- Clipboard is deliberately NOT used; harness storage is more reliable for multiple pasted images.