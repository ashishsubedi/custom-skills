# Storyboard & Visual Design Guide (3B1B Explainer Standard)

Use this reference when designing `beats.json` and `scene.py` for papers, algorithms, or systems talks.

---

## 1. The Background-First Story Arc

Every great visual technical explainer answers **"Why was this invented?"** before **"How does it work?"**:

| Act | Goal | Visual Strategy |
| :--- | :--- | :--- |
| **1. Baseline & Bottleneck** | Show how the standard system works today | Concrete pipeline or data flow + cost scaling ($O(N^2)$ matrix, bandwidth wall, thrashing sawtooth) |
| **2. Concrete Running Example** | Ground abstract tensors in human-readable inputs | 2–4 short readable lines (`"Derek lives in Thenum"` / `"Where does Derek work?"`) reused across all scenes |
| **3. Physical / Math Barriers** | Prove *why* naive fixes fail | One dedicated visual metaphor per barrier (2D rotation clock for RoPE, dark off-diagonal block for missing cross-attention, towering softmax spike for sinks) |
| **4. Design Spectrum** | Orient the viewer before diving into papers | Horizontal spectrum axis + 2–3 minimalist method cards showing the trade-off axis |
| **5. Mechanism Deep-Dives** | Reveal *how* each paper solves the barriers | Step-by-step transformations: schema rulers, pilot pass bar charts, layer-wise dimension shrinkage, dual-lane Gantt pipelines, boundary patches |
| **6. Honest Limits & Synthesis** | Show failure cases, scaling crossover, and domain impact | Asymptotic curves (`O(0.15N²)` OOM vs. `O(kN)` linear), explicit caveat visual, target runtime tie-in |

---

## 2. Proven Visual Metaphors (Replace Blank Boxes)

- **Tokens & Positions**: Rounded pill strip (`token_row`) with actual short words and token index subscripts (`0, 1, 2...`).
- **KV Cache / Memory Blocks**: `kv_block` showing distinct `K` (cyan/blue) and `V` (teal) stripe lanes inside a dark panel card plus token range subtitle (`0..511`).
- **Causal Attention & Cross-Chunk Loss**: `attention_matrix` drawing an $N \times N$ lower-triangular grid—diagonal chunk triangles vs. off-diagonal cross-attention rectangles (`YELLOW` when populated, pitch-dark `PANEL` with `RED` border when missing).
- **Rotary Embeddings / Phase**: `rope_clock` 2D unit circle with angle arc, rotating key vector arrow, and relative wedge `Sector` between $\mathbf{q}_m$ and $\mathbf{k}_n$.
- **Distributions & Sinks**: `labeled_bars` with explicit baseline, bottom token labels, and top numeric weights; `Transform(bars_pre, bars_post)` animates softmax redistribution live.
- **Pipelining & Overlap**: Stacked horizontal Gantt tracks (`GPU Compute` over `PCIe/SSD Load`) aligned vertically so overlapping phases are self-evident.
- **Asymptotic Scaling**: Manim `Axes` with plotted `O(N²)`, `O(0.15·N²)`, and `O(k·N)` curves, plus explicit OOM dot/marker.

---

## 3. Coordinate Safe Zones (`1920x1080` -> `14.22 x 8.0`)

Never place visual elements outside the stage box:

```
y = +4.00 ┌───────────────────────────────────────────────┐
          │ Top Header: chapter tag + progress rail       │ y in [+3.32, +3.85]
y = +3.26 ├───────────────────────────────────────────────┤
          │                                               │
          │ Main Visual Stage                             │ x in [-6.55, +6.55]
          │ (Equations, matrices, clocks, charts, blocks) │ y in [-2.70, +3.18]
          │                                               │
y = -2.85 ├───────────────────────────────────────────────┤
          │ Subtitle Safe Zone (1920x155 RGBA pill bar)   │ y in [-3.95, -2.85]
y = -4.00 └───────────────────────────────────────────────┘
```

---

## 4. Micro-Beat Choreography Rules

1. **Keep `subbeats` short (`4–12 s`, 1–2 sentences)**: Break dense ideas into sequential sub-beats inside one persistent scene so diagrams evolve in lockstep with each clause.
2. **Budget animations to `U = T - 0.30` on clearing beats**: Reserve `0.28 s` inside the final sub-beat of a scene for `clear_stage(rt=0.28)` so cumulative timing never drifts past the audio budget.
3. **Never scale bars over their own labels**: Always pass `scale_factor=1.04` (instead of default `1.2`) when calling `Indicate()` on chart bars that have top/bottom labels.
4. **Always inspect `MathTex` width & UTF-8**: Keep LaTeX commands pure ASCII inside `MathTex(r"...")` (use `-` and `\times`, not `−` or `×`); use UTF-8 symbols freely inside `Text(...)` / subtitle strings.
5. **Kill ghost mobjects**: Whenever `ReplacementTransform` or `always_redraw` is used, `self.stage` loses track of the new target object. Always clear via `clear_except_header()` or `clear_stage()`, which collect `self.mobjects` directly and call `self.clear()`.
