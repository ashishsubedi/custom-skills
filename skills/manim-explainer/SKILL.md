---
name: manim-explainer
description: >-
  Create 3Blue1Brown-style animated explainer videos (Manim + word-synced narration +
  burned-in & SRT subtitles) for research papers, systems architectures, and technical
  topics, including required background foundations. Use when the user asks to visually
  explain papers or concepts, generate a Manim video with synced audio and subtitles,
  or improve an existing technical animation headlessly in the background.
---

# Manim Explainer — 3B1B Paper & Topic Video Pipeline

Produce clear, visual-first technical explainer videos that teach both the **required background foundations** and the **core paper/topic mechanisms**, with sub-second synced narration, non-overlapping subtitles, and headless background verification.

## Core Doctrine (Why Most AI Videos Fail)

1. **No context-free clip art**: Never show unlabeled shapes (`A`, `B`, `C`), mysterious squares, or prose walls. Every diagram must carry self-evident labels, concrete token/data examples, equations (`MathTex`), matrices, or plots.
2. **Teach the background first**: Never jump straight into Paper X's novel trick. Start from first principles—show what existing systems do, *why* they break mathematically or physically (the invariant violations), and carry **one concrete running example** across every chapter.
3. **Continuous visual sync (never freeze a slide)**: Break every scene into **4–12 s micro-beats** (`subbeats`) of 1–2 spoken sentences. Every sub-beat animates for the exact duration of its audio clip (`~95%` motion, `< 0.5 s` settle) instead of playing 3 s of animation and freezing for 25 s.
4. **Separate TTS pronunciation from display subtitles**: Store `"tts"` (phonetic expansions like `v-L-L-M`, `T-T-F-T`, `K-V`, `O of N squared`) separately from `"sub"` (`vLLM`, `TTFT`, `O(N²)`) in `beats.json` so narration sounds natural while subtitles stay crisp and technical.
5. **Verify visually in the background**: Never launch GUI preview windows (`manim -p`, `open`, QuickTime) and always run heavy renders with `nice -n 10`. Always run a fast 480p15 smoke pass, extract keyframes, inspect them with `read_file` to catch ghost objects or text collisions, fix them, and *then* render 1080p30.

---

## End-to-End 5-Phase Workflow

### Phase 1 — Deep-Dive & Background Mapping (Before Writing Code)
1. **Read primary sources**: Extract text directly from local PDFs (`fitz` / `pymupdf`, `pdftotext` without `-layout`, or `zotero-bridge text <itemKey>`) and any user notes. Do not rely on second-hand summaries for equations, layer-by-layer mechanics, or quantitative bounds.
2. **Establish the prerequisite chain**: Map what background the viewer needs *before* the target paper(s) make sense:
   - *Baseline mechanism* (how the standard system works and its cost/complexity)
   - *Physical/mathematical barriers* (what breaks and why, demonstrated geometrically or with a matrix/counterexample)
   - *Design spectrum* (how each paper/approach trades off assumptions, compute, and accuracy)
   - *Target system connection* (if applicable, tie back to the user's project/research context)
3. **Select a concrete running example**: Pick one intuitive example (e.g., a 2-hop QA snippet or a tiny state-machine trace) and reuse it consistently from Problem -> Barriers -> Solutions -> Trade-offs.

### Phase 2 — Micro-Beat Storyboard (`beats.json`)
Author `beats.json` as an ordered list of scenes (`8–14` scenes, `~4–10 min` total), each containing `2–5` short `subbeats`:
```json
[
  {
    "id": "01_hook",
    "chapter": "01 · THE PREFIX WALL",
    "subbeats": [
      {
        "id": "01a",
        "tts": "Before a model emits one word, it reads the prompt in parallel and builds Key and Value tensors.",
        "sub": "Before an LLM emits a word, it builds Key and Value tensors across every layer.",
        "visual": "Tokens glide in -> L1..LN stack -> K|V columns grow upward."
      }
    ]
  }
]
```
See [references/storyboard_and_visuals.md](./references/storyboard_and_visuals.md) for visual metaphor templates (2D vector clocks, lower-triangular attention matrices, dual-lane pipelines, scaling curves) and coordinate safe-zone rules.

### Phase 3 — Synthesize Narration & Word-Level Timings
Run the bundled `edge-tts` (`en-US-AndrewNeural` + `WordBoundary`) pipeline using the Python environment that has `edge-tts` installed (`$TTS_PY` or `python3`):
```bash
nice -n 10 "${TTS_PY:-python3}" \
  skills/manim-explainer/scripts/build_audio.py \
  --work-dir <video_dir> --voice en-US-AndrewNeural --rate "+5%"
```
- Outputs `audio/<sid>.wav` (`24 kHz` mono PCM), `audio/<sid>.words.json`, and `timings.json` (exact durations + clause-split subtitle cues anchored to `WordBoundary` timestamps).
- For offline fallback (`Kokoro-82M`) and environment setup, see [references/environment_setup.md](./references/environment_setup.md).

### Phase 4 — Choreograph Manim Scenes & 480p Smoke Audit
1. Subclass `SubbeatScene` from [scripts/manim_primitives.py](./scripts/manim_primitives.py) (or copy its helpers locally if standalone scripts are preferred).
2. **Enforce strict frame safe-zones** (`14.22 x 8.0` Manim canvas):
   - **Header bar**: `y ∈ [+3.32, +3.85]`
   - **Visual stage**: `x ∈ [-6.55, +6.55]`, `y ∈ [-2.70, +3.18]`
   - **Subtitle safe-zone**: `y ∈ [-3.95, -2.85]` — **keep completely empty of diagrams** (`1920x155` overlay at `y=925`).
3. **Prevent ghost leaks**: Always use `self.clear_except_header()` / `self.clear_stage()` (which fade `Group(*self.mobjects)` and call `self.clear()`), because `ReplacementTransform` targets are not tracked in `self.stage`.
4. **Prevent `Indicate` label collisions**: Pass `scale_factor=1.04` on bar-chart `Indicate(...)` animations so bars do not stretch over their value labels.
5. **Fast 480p15 smoke pass + visual audit**:
   ```bash
   nice -n 10 "${MANIM_BIN:-manim}" render \
     -q l -r 854,480 --fps 15 scene.py <SceneClass> > smoke.log 2>&1
   ```
   Extract 2 frames per scene (`30%` and `78%`) and inspect them with `read_file`. Fix every overlap, clipped `MathTex`, or stale mobject before rendering 1080p.

### Phase 5 — Final 1080p30 Render, Subtitle Burn & Headless Verification
1. Render full `1920x1080 @ 30fps` headlessly under `nice -n 10`:
   ```bash
   nice -n 10 "${MANIM_BIN:-manim}" render \
     -r 1920,1080 --fps 30 scene.py <SceneClass> > render.log 2>&1
   ```
2. Assemble frame-locked audio (`adelay` using Manim's exact `video_timings.json`), apply broadcast loudness normalization (`-16 LUFS`), generate `subtitles.srt`, burn crisp Pillow dark-pill RGBA subtitles into the bottom strip, probe streams, and extract final verification frames:
   ```bash
   nice -n 10 "${MANIM_PY:-python3}" \
     skills/manim-explainer/scripts/assemble_video.py \
     --work-dir <video_dir> \
     --raw media/videos/scene/1080p30/<SceneClass>.mp4 \
     --out <output_1080p.mp4>
   ```
   *(Uses Pillow RGBA pipe + `ffmpeg overlay` so subtitle burning works even when `ffmpeg` omits `libass`/`drawtext`.)*
3. **Verify before reporting**: Read `verification.txt` (`ffprobe` stream codecs/fps/duration, `volumedetect` mean/max dB) and inspect representative final 1080p frames with `read_file` to confirm subtitle legibility and zero diagram collisions.

---

## Bundled Files
- [scripts/build_audio.py](./scripts/build_audio.py) — Concurrent `edge-tts` synthesis, `WordBoundary` cue splitting, silence trimming, `timings.json`.
- [scripts/assemble_video.py](./scripts/assemble_video.py) — Exact `adelay` audio mux, `-16 LUFS` `loudnorm`, `subtitles.srt`, Pillow RGBA subtitle burn, `ffprobe` + keyframe extractor.
- [scripts/manim_primitives.py](./scripts/manim_primitives.py) — 3B1B palette, safe-zone helpers (`make_header`, `token_row`, `kv_block`, `attention_matrix`, `rope_clock`, `labeled_bars`, `badge`), and `SubbeatScene` base class.
- [references/storyboard_and_visuals.md](./references/storyboard_and_visuals.md) — Narrative blueprint, visual design rules, and 3B1B anti-patterns.
- [references/environment_setup.md](./references/environment_setup.md) — Portable Python/Manim/TTS/LaTeX/FFmpeg setup, background flags, and known platform quirks.
- [setup.sh](./setup.sh) — Per-skill installer linking `manim-explainer` into all harness skill roots and checking environment dependencies.
