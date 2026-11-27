"""Reusable 3Blue1Brown-style Manim primitives, safe-zone chrome, and SubbeatScene."""
import os
import platform
import numpy as np
from manim import *

# Palette (3B1B-inspired deep slate + luminous semantic hues)
BG = "#0B111E"
PANEL = "#121B2E"
BORDER_DIM = "#334366"
TXT = "#F0F4FA"
MUTED = "#8FA3C4"
BLUE = "#58C4DD"
TEAL = "#2EC4B6"
YELLOW = "#F7D060"
AMBER = "#F59E0B"
GREEN = "#4ADE80"
RED = "#F87171"
PURPLE = "#C084FC"

_IS_MAC = platform.system() == "Darwin"
FONT_SANS = os.getenv("MANIM_FONT_SANS", "SF Pro Display" if _IS_MAC else "Sans")
FONT_MONO = os.getenv("MANIM_FONT_MONO", "Menlo" if _IS_MAC else "Monospace")

STAGE_CENTER = np.array([0.0, 0.22, 0.0])


class SubbeatScene(Scene):
    """Base Manim Scene providing audio-locked micro-beat timing and leak-free stage clearing."""

    def init_subbeats(self):
        self.stage = VGroup()
        self.header = None
        self.marks = {"scenes": {}, "subbeats": {}}
        self._sb_used = 0.0
        self.timings = {}

    def put(self, *mobs):
        for m in mobs:
            self.stage.add(m)
        return mobs[0] if len(mobs) == 1 else mobs

    def p(self, *anims, rt: float = 1.0, **kw):
        rt = max(0.05, float(rt))
        self.play(*anims, run_time=rt, **kw)
        self._sb_used += rt

    def w(self, dt: float):
        dt = float(dt)
        if dt > 0.015:
            self.wait(dt)
            self._sb_used += dt

    def play_sb(self, sid: str, fn):
        info = self.timings["subbeats"][sid]
        target = info["duration"] + info["pad"]
        self._sb_used = 0.0
        self.marks["subbeats"][sid] = {"start": round(self.time, 4)}
        fn(target)
        rem = target - self._sb_used
        if rem > 0.015:
            self.wait(rem)
        self.marks["subbeats"][sid]["end"] = round(self.time, 4)

    def clear_except_header(self, rt: float = 0.22):
        """Fade and remove all mobjects except header (catches ReplacementTransform targets)."""
        mobs = [m for m in self.mobjects if m is not self.header]
        if mobs:
            self.p(FadeOut(Group(*mobs)), rt=rt)
            self.remove(*mobs)
        self.stage = VGroup()

    def clear_stage(self, rt: float = 0.28):
        """Fade and wipe every mobject on screen between major scenes."""
        mobs = list(self.mobjects)
        if mobs:
            self.p(FadeOut(Group(*mobs)), rt=rt)
        self.clear()
        self.stage = VGroup()
        self.header = None


def label_text(text: str, size: int = 22, color=TXT, weight=NORMAL, mono: bool = False):
    return Text(text, font=FONT_MONO if mono else FONT_SANS, font_size=size, color=color, weight=weight)


def make_header(chapter: str, frac: float) -> VGroup:
    dot = Dot(radius=0.06, color=BLUE).move_to([-6.45, 3.56, 0])
    chap = label_text(chapter, size=18, color=MUTED, weight=SEMIBOLD, mono=True).next_to(dot, RIGHT, buff=0.14)
    rail_w = 3.2
    rail_bg = RoundedRectangle(
        corner_radius=0.03, width=rail_w, height=0.07,
        stroke_width=0, fill_color=BORDER_DIM, fill_opacity=0.65,
    ).move_to([4.95, 3.56, 0])
    fill_w = max(0.08, rail_w * np.clip(frac, 0.02, 1.0))
    rail_fg = RoundedRectangle(
        corner_radius=0.03, width=fill_w, height=0.07,
        stroke_width=0, fill_color=BLUE, fill_opacity=0.95,
    ).align_to(rail_bg, LEFT).set_y(rail_bg.get_y())
    sep = Line([-6.6, 3.26, 0], [6.6, 3.26, 0], stroke_width=1.0, color=BORDER_DIM, stroke_opacity=0.55)
    return VGroup(dot, chap, rail_bg, rail_fg, sep)


def token_row(words, colors=None, indices=None, font_size=15, pill_h=0.44, buff=0.09):
    pills = VGroup()
    colors = colors or [BLUE] * len(words)
    for i, (w, c) in enumerate(zip(words, colors)):
        t = label_text(w, size=font_size, color=TXT, mono=True)
        box = RoundedRectangle(
            corner_radius=0.07, width=max(0.62, t.width + 0.24), height=pill_h,
            stroke_color=c, stroke_width=1.8, fill_color=c, fill_opacity=0.16,
        )
        t.move_to(box.get_center())
        grp = VGroup(box, t)
        if indices is not None:
            grp.add(label_text(str(indices[i]), size=11, color=MUTED, mono=True).next_to(box, DOWN, buff=0.06))
        pills.add(grp)
    pills.arrange(RIGHT, buff=buff, aligned_edge=UP)
    return pills


def kv_block(title: str, subtitle: str = "", color=BLUE, w=2.3, h=1.45, cols=8, k_color=None, v_color=None):
    kc, vc = k_color or color, v_color or TEAL
    outer = RoundedRectangle(
        corner_radius=0.10, width=w, height=h,
        stroke_color=color, stroke_width=2.2, fill_color=PANEL, fill_opacity=0.92,
    )
    hdr = label_text(title, size=18, color=color, weight=BOLD).move_to(outer.get_top() + DOWN * 0.24)
    stripe_w = min(0.14, (w - 0.55) / (cols * 1.45))
    gap = stripe_w * 0.45
    k_row = VGroup(*[Rectangle(width=stripe_w, height=0.22, stroke_width=0, fill_color=kc, fill_opacity=0.82) for _ in range(cols)]).arrange(RIGHT, buff=gap)
    v_row = VGroup(*[Rectangle(width=stripe_w, height=0.22, stroke_width=0, fill_color=vc, fill_opacity=0.72) for _ in range(cols)]).arrange(RIGHT, buff=gap)
    k_grp = VGroup(label_text("K", size=12, color=kc, mono=True), k_row).arrange(RIGHT, buff=0.10)
    v_grp = VGroup(label_text("V", size=12, color=vc, mono=True), v_row).arrange(RIGHT, buff=0.10)
    kv_grid = VGroup(k_grp, v_grp).arrange(DOWN, buff=0.09).move_to(outer.get_center() + DOWN * 0.08)
    g = VGroup(outer, hdr, kv_grid)
    if subtitle:
        g.add(label_text(subtitle, size=12, color=MUTED, mono=True).next_to(outer, DOWN, buff=0.08))
    return g


def attention_matrix(n: int, chunk_bounds, cell: float = 0.22, gap: float = 0.03, mode: str = "full", sink_cols=None, repaired_rows=None):
    sink_cols, repaired_rows = set(sink_cols or []), set(repaired_rows or [])

    def chunk_of(idx):
        for ci, (s, e) in enumerate(chunk_bounds):
            if s <= idx < e:
                return ci
        return len(chunk_bounds) - 1

    grid, cells = VGroup(), {}
    step = cell + gap
    w = n * step - gap
    for r in range(n):
        cr = chunk_of(r)
        for c in range(n):
            cc = chunk_of(c)
            if c > r:
                col, op = BG, 0.25
            elif mode == "full":
                col, op = (BLUE, 0.65) if cr == cc else (YELLOW, 0.72)
            elif mode == "isolated":
                col, op = (BLUE, 0.70) if cr == cc else (PANEL, 0.35)
            elif mode == "sinks":
                col, op = (PURPLE, 0.92) if c in sink_cols else ((BLUE, 0.45) if cr == cc else (PANEL, 0.32))
            elif mode == "legolink":
                if r in repaired_rows:
                    col, op = GREEN, 0.85
                elif c in sink_cols:
                    col, op = BLUE, 0.35
                else:
                    col, op = (BLUE, 0.60) if cr == cc else (TEAL, 0.55)
            else:
                col, op = BLUE, 0.60
            sq = Square(side_length=cell, stroke_color=BORDER_DIM, stroke_width=0.6, fill_color=col, fill_opacity=op)
            sq.move_to([-w / 2 + cell / 2 + c * step, w / 2 - cell / 2 - r * step, 0])
            grid.add(sq)
            cells[(r, c)] = sq
    return VGroup(SurroundingRectangle(grid, color=BORDER_DIM, stroke_width=1.4, buff=0.06), grid), cells


def rope_clock(angle: float = 0.0, radius: float = 0.85, color=BLUE, vec_label: str = "k"):
    circle = Circle(radius=radius, color=BORDER_DIM, stroke_width=1.8)
    ax_h = Line([-radius * 1.15, 0, 0], [radius * 1.15, 0, 0], color=BORDER_DIM, stroke_width=1.0)
    ax_v = Line([0, -radius * 1.15, 0], [0, radius * 1.15, 0], color=BORDER_DIM, stroke_width=1.0)
    tip = radius * 0.88 * np.array([np.cos(angle), np.sin(angle), 0])
    arr = Arrow(ORIGIN, tip, buff=0, color=color, stroke_width=4.0, max_tip_length_to_length_ratio=0.22)
    dot = Dot(tip, radius=0.055, color=color)
    arc = Arc(radius=radius * 0.42, start_angle=0, angle=angle if abs(angle) > 0.05 else 0.05, color=color, stroke_width=2.5)
    lab = label_text(vec_label, size=15, color=color, mono=True).next_to(circle, DOWN, buff=0.14)
    return VGroup(circle, ax_h, ax_v, arc, arr, dot, lab)


def labeled_bars(heights, bar_labels, colors, max_h: float = 2.1, bar_w: float = 0.46, gap: float = 0.16, val_labels=None):
    scale = max_h / max(max(heights) if heights else 1.0, 1e-6)
    total_w = len(heights) * bar_w + max(0, len(heights) - 1) * gap
    baseline = Line([-total_w / 2 - 0.25, 0, 0], [total_w / 2 + 0.25, 0, 0], color=BORDER_DIM, stroke_width=1.8)
    bars_grp, labs_grp, vals_grp = VGroup(), VGroup(), VGroup()
    x = -total_w / 2 + bar_w / 2
    for i, (h, lb, c) in enumerate(zip(heights, bar_labels, colors)):
        bh = max(0.06, h * scale)
        rect = RoundedRectangle(corner_radius=0.04, width=bar_w, height=bh, stroke_color=c, stroke_width=1.5, fill_color=c, fill_opacity=0.80)
        rect.move_to([x, bh / 2, 0])
        bars_grp.add(rect)
        labs_grp.add(label_text(lb, size=13, color=MUTED, mono=True).next_to(rect, DOWN, buff=0.12))
        if val_labels is not None:
            vals_grp.add(label_text(val_labels[i], size=13, color=c, mono=True).next_to(rect, UP, buff=0.08))
        x += bar_w + gap
    return VGroup(baseline, bars_grp, labs_grp, vals_grp), bars_grp, vals_grp


def badge(text: str, color=BLUE, size: int = 16, fill_op: float = 0.16):
    t = label_text(text, size=size, color=color, weight=SEMIBOLD, mono=True)
    box = RoundedRectangle(
        corner_radius=0.09, width=t.width + 0.34, height=t.height + 0.22,
        stroke_color=color, stroke_width=1.8, fill_color=color, fill_opacity=fill_op,
    )
    t.move_to(box.get_center())
    return VGroup(box, t)
