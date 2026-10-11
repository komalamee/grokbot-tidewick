"""Every worked chapter's numbers must verify, and the receipt/chart commands must run."""
import tempfile
import unittest
from pathlib import Path

import _path
import case_maths as m

WORKED = ["ch01.md", "ch02.md"]


class Chapters(unittest.TestCase):
    def test_every_claim_verifies(self):
        for name in WORKED:
            res = m.check_chapter(_path.CHAPTERS / name)
            fails = [line for ok, line in res if not ok]
            self.assertEqual(fails, [], f"{name}: {fails}")
            self.assertGreater(len(res), 30)

    def test_check_catches_a_wrong_number(self):
        text = (_path.CHAPTERS / "ch01.md").read_text(encoding="utf-8").replace('"breakevens": [9.2], "max_gain": 8', '"breakevens": [9.4], "max_gain": 8', 1)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.md"
            p.write_text(text, encoding="utf-8")
            fails = [line for ok, line in m.check_chapter(p) if not ok]
        self.assertEqual(len(fails), 1)
        self.assertIn("breakeven", fails[0])

    def test_missing_slot_fails(self):
        text = (_path.CHAPTERS / "ch01.md").read_text(encoding="utf-8").replace("## Clue", "## Something else")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.md"
            p.write_text(text, encoding="utf-8")
            fails = [line for ok, line in m.check_chapter(p) if not ok]
        self.assertTrue(any("Clue" in f for f in fails))

    def test_receipts(self):
        r = m.receipt(_path.CHAPTERS / "ch01.md", "A")
        self.assertIn("YOUR RESULT: +£8", r)
        self.assertIn("Breakeven: £9.20", r)
        self.assertIn("at £7 \u2192 \u2212£22", r)
        r = m.receipt(_path.CHAPTERS / "ch01.md", "B")
        self.assertIn("Had you chosen A", r)
        r = m.receipt(_path.CHAPTERS / "ch02.md", "A")
        self.assertIn("Cash £480 \u2192 £489", r)
        with self.assertRaises(ValueError):
            m.receipt(_path.CHAPTERS / "ch01.md", "holder")  # not a player choice

    def test_charts(self):
        with tempfile.TemporaryDirectory() as d:
            for name, choice in (("ch01.md", "A"), ("ch02.md", "A"), ("ch01.md", "B")):
                out = m.chart(_path.CHAPTERS / name, choice, str(Path(d) / f"{name}-{choice}.png"))
                self.assertGreater(Path(out).stat().st_size, 5000)

    def test_chart_falls_back_to_svg_without_pillow(self):
        real = m._PilCanvas
        def no_pillow(*a, **k):
            raise ImportError("no Pillow")
        m._PilCanvas = no_pillow
        try:
            with tempfile.TemporaryDirectory() as d:
                out = m.chart(_path.CHAPTERS / "ch01.md", "A", str(Path(d) / "c.png"))
                self.assertTrue(out.endswith(".svg"))
                svg = Path(out).read_text(encoding="utf-8")
                self.assertIn("breakeven £9.20", svg)
                self.assertIn("what happened: £12", svg)
        finally:
            m._PilCanvas = real

    def test_story_is_placeholder_and_slotted(self):
        for name in WORKED:
            ch = m.parse_chapter(_path.CHAPTERS / name)
            self.assertEqual(ch["meta"]["story_status"], "PLACEHOLDER")
            self.assertIn("[PLACEHOLDER STORY", ch["sections"]["Scene"])
            self.assertIn("whatever the result", ch["sections"]["Clue"])


if __name__ == "__main__":
    unittest.main()
