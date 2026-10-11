"""Casebook: init, reason before choice, clues never depend on the result, review queue."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _path
import casebook as c


class Casebook(unittest.TestCase):
    def test_flow(self):
        d = c.new_casebook("Sam", "never")
        self.assertEqual(d["settings"]["next_chapter_reminder"], "off")
        c.save_reason(d, "ch01", "Happy to own crates at £10.")
        self.assertEqual(d["chapters"]["ch01"]["status"], "in-progress")
        c.finish(d, "ch01", "A", -22, ["clue-01"], ["put-option"])
        self.assertEqual(d["current_chapter"], "ch02")
        self.assertEqual(d["clues"], [{"id": "clue-01", "chapter": "ch01"}])  # clue found despite a loss
        self.assertEqual(d["chapters"]["ch01"]["reason"], "Happy to own crates at £10.")
        self.assertEqual(c.due(d), [])
        c.finish(d, "ch02", "C", 0, ["clue-02"], ["cash-secured-put"])
        self.assertEqual([r["concept"] for r in c.due(d)], ["put-option"])  # due at ch03
        c.review(d, "put-option", False)
        self.assertEqual(d["review"][0]["due_at"], "ch04")
        d["current_chapter"] = "ch04"
        c.review(d, "put-option", True)
        c.review(d, "put-option", True)
        self.assertNotIn("put-option", [r["concept"] for r in d["review"]])

    def test_replay_does_not_duplicate(self):
        d = c.new_casebook("Sam", "yes")
        c.finish(d, "ch01", "A", 8, ["clue-01"], ["put-option"])
        c.finish(d, "ch01", "B", 0, ["clue-01"], ["put-option"])
        self.assertEqual(len(d["clues"]), 1)
        self.assertEqual(len(d["review"]), 1)
        self.assertEqual(d["current_chapter"], "ch02")

    def test_bad_ids(self):
        d = c.new_casebook("Sam", "never")
        with self.assertRaises(ValueError):
            c.start(d, "chapter-1")
        with self.assertRaises(ValueError):
            c.new_casebook("Sam", "sometimes")

    def test_example_file_is_valid(self):
        c.validate(json.loads((_path.ROOT / "fixed-files" / "casebook" / "casebook.example.json").read_text(encoding="utf-8")))

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, TIDEWICK_HOME=home)
            run = lambda *a: subprocess.run([sys.executable, str(_path.ENGINE / "casebook.py"), *a], env=env,
                                            capture_output=True, text=True, check=True)
            run("init", "--name", "Sam", "--traded", "never")
            run("reason", "ch01", "The fee is mine either way.")
            run("finish", "ch01", "--choice", "A", "--result", "8", "--clue", "clue-01", "--concept", "put-option")
            d = json.loads(run("show").stdout)
            self.assertEqual(d["current_chapter"], "ch02")
            self.assertTrue((Path(home) / "casebook.json").exists())


if __name__ == "__main__":
    unittest.main()
