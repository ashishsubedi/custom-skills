"""Unit tests for manim-explainer helper scripts."""
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_audio  # noqa: E402
import assemble_video  # noqa: E402


class TestBuildAudio(unittest.TestCase):
    def test_wrap_two_lines_keeps_short_text(self):
        self.assertEqual(build_audio.wrap_two_lines("Hello world", 44), "Hello world")

    def test_wrap_two_lines_balances_long_text(self):
        txt = "Position-independent caching breaks the strict prefix rule for multi-chunk RAG prompts."
        wrapped = build_audio.wrap_two_lines(txt, 44)
        self.assertEqual(len(wrapped.splitlines()), 2)

    def test_split_sub_clauses_splits_punctuation(self):
        txt = "First sentence here. Second sentence explains why the naive cache breaks completely."
        parts = build_audio.split_sub_clauses(txt, max_chars=50)
        self.assertGreaterEqual(len(parts), 2)
        self.assertEqual(parts[0], "First sentence here.")
        self.assertTrue(all(len(p) <= 50 for p in parts))

    def test_map_clauses_to_words_monotonic(self):
        clauses = ["First clause here.", "Second clause follows."]
        words = [
            {"start": 0.05, "dur": 0.30, "text": "First"},
            {"start": 0.40, "dur": 0.35, "text": "clause"},
            {"start": 0.80, "dur": 0.25, "text": "here"},
            {"start": 1.25, "dur": 0.30, "text": "Second"},
            {"start": 1.60, "dur": 0.35, "text": "clause"},
            {"start": 2.00, "dur": 0.40, "text": "follows"},
        ]
        cues = build_audio.map_clauses_to_words(clauses, words, dur=2.50)
        self.assertEqual(len(cues), 2)
        self.assertLessEqual(cues[0]["end"], cues[1]["start"] + 1e-6)
        self.assertAlmostEqual(cues[1]["end"], 2.50, places=3)


class TestAssembleVideo(unittest.TestCase):
    def test_srt_time_formatting(self):
        self.assertEqual(assemble_video.srt_time(0.0), "00:00:00,000")
        self.assertEqual(assemble_video.srt_time(65.432), "00:01:05,432")

    def test_render_sub_strip_dimensions(self):
        from PIL import ImageFont

        font_path = "/System/Library/Fonts/SFNS.ttf"
        font = ImageFont.truetype(font_path, 34) if Path(font_path).exists() else ImageFont.load_default()
        buf = assemble_video.render_sub_strip("O(N²) · Δ = 2048\nLine two", font)
        self.assertEqual(len(buf), assemble_video.SUB_W * assemble_video.SUB_H * 4)


if __name__ == "__main__":
    unittest.main()
