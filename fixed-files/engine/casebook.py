#!/usr/bin/env python3
"""The player's casebook: a small JSON file on the player's own box. Standard library only.

Default path: ~/.tidewick/casebook.json (override with TIDEWICK_HOME or --file).
Nothing here is sent anywhere. Format and field meanings: ../casebook/CASEBOOK.md.

  casebook.py init --name NAME --traded never|a-little|yes
  casebook.py show                         print the casebook as JSON
  casebook.py start ch01                   mark a chapter in progress
  casebook.py reason ch01 "TEXT"           save the player's stated reason (before they choose)
  casebook.py finish ch01 --choice A --result 8 --clue clue-01 --concept put-option [--concept ...]
  casebook.py due                          review items due at the current chapter (for the recap quiz)
  casebook.py review CONCEPT right|wrong   record a recap answer
  casebook.py reminder on|off              the next-chapter reminder setting (off by default)
  casebook.py note-sent                    record that a reminder went out for the current chapter
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

VERSION = 1
REVIEW_GAP = 2        # a concept comes back for review two chapters later (suggestion, see SPEC open questions)
RETIRE_AFTER = 2      # retired from review after this many right answers
TRADED = ("never", "a-little", "yes")


def default_path() -> Path:
    home = os.environ.get("TIDEWICK_HOME")
    return Path(home) / "casebook.json" if home else Path.home() / ".tidewick" / "casebook.json"


def chapter_num(cid: str) -> int:
    m = re.fullmatch(r"ch(\d{2})", cid or "")
    if not m:
        raise ValueError(f"chapter id must look like ch01, got {cid!r}")
    return int(m.group(1))


def chapter_id(n: int) -> str:
    return f"ch{n:02d}"


def today() -> str:
    return dt.date.today().isoformat()


def new_casebook(name: str, traded: str) -> dict:
    if traded not in TRADED:
        raise ValueError(f"traded must be one of {TRADED}")
    return {"version": VERSION,
            "player": {"name": name.strip()[:60], "traded_before": traded, "started_on": today()},
            "current_chapter": "ch01",
            "chapters": {},
            "clues": [],
            "concepts": [],
            "review": [],
            "settings": {"next_chapter_reminder": "off", "last_note_for": None}}


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate(data)
    return data


def save(path: Path, data: dict) -> None:
    validate(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".casebook-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def validate(d: dict) -> None:
    if not isinstance(d, dict) or d.get("version") != VERSION:
        raise ValueError("not a version 1 casebook")
    for k in ("player", "current_chapter", "chapters", "clues", "concepts", "review", "settings"):
        if k not in d:
            raise ValueError(f"casebook missing {k}")
    chapter_num(d["current_chapter"])
    for cid in d["chapters"]:
        chapter_num(cid)


def start(d: dict, cid: str) -> dict:
    chapter_num(cid)
    ch = d["chapters"].setdefault(cid, {})
    if ch.get("status") != "done":
        ch["status"] = "in-progress"
        ch.setdefault("started_on", today())
    d["current_chapter"] = cid
    return d


def save_reason(d: dict, cid: str, text: str) -> dict:
    start(d, cid)
    d["chapters"][cid]["reason"] = text.strip()[:500]
    return d


def finish(d: dict, cid: str, choice: str, result_gbp: float, clues: list[str], concepts: list[str]) -> dict:
    """Record a finished chapter. Clues are added whatever the result: they never depend on winning."""
    n = chapter_num(cid)
    ch = d["chapters"].setdefault(cid, {})
    ch.update({"status": "done", "choice": choice, "result_gbp": round(float(result_gbp), 2), "finished_on": today()})
    ch.setdefault("reason", "")
    have = {c["id"] for c in d["clues"]}
    for c in clues:
        if c not in have:
            d["clues"].append({"id": c, "chapter": cid})
    known = {c["id"] for c in d["concepts"]}
    queued = {r["concept"] for r in d["review"]}
    for c in concepts:
        if c not in known:
            d["concepts"].append({"id": c, "chapter": cid})
        if c not in queued:
            d["review"].append({"concept": c, "from": cid, "due_at": chapter_id(n + REVIEW_GAP), "right": 0})
    if chapter_num(d["current_chapter"]) <= n:
        d["current_chapter"] = chapter_id(n + 1)
    return d


def due(d: dict) -> list[dict]:
    cur = chapter_num(d["current_chapter"])
    return [r for r in d["review"] if chapter_num(r["due_at"]) <= cur]


def review(d: dict, concept: str, right: bool) -> dict:
    cur = chapter_num(d["current_chapter"])
    for r in list(d["review"]):
        if r["concept"] == concept:
            if right:
                r["right"] += 1
                if r["right"] >= RETIRE_AFTER:
                    d["review"].remove(r)
                else:
                    r["due_at"] = chapter_id(cur + REVIEW_GAP)
            else:
                r["due_at"] = chapter_id(cur + 1)
            return d
    raise ValueError(f"{concept!r} is not on the review list")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Player casebook (local JSON, never shared).")
    ap.add_argument("--file", type=Path, default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("--name", required=True); i.add_argument("--traded", choices=TRADED, required=True)
    i.add_argument("--force", action="store_true")
    sub.add_parser("show")
    s = sub.add_parser("start"); s.add_argument("chapter")
    r = sub.add_parser("reason"); r.add_argument("chapter"); r.add_argument("text")
    f = sub.add_parser("finish"); f.add_argument("chapter"); f.add_argument("--choice", required=True)
    f.add_argument("--result", type=float, required=True); f.add_argument("--clue", action="append", default=[])
    f.add_argument("--concept", action="append", default=[])
    sub.add_parser("due")
    v = sub.add_parser("review"); v.add_argument("concept"); v.add_argument("answer", choices=["right", "wrong"])
    m = sub.add_parser("reminder"); m.add_argument("state", choices=["on", "off"])
    sub.add_parser("note-sent")
    a = ap.parse_args(argv)
    path = a.file or default_path()

    if a.cmd == "init":
        if path.exists() and not a.force:
            print(f"casebook already exists at {path}; use --force to start again", file=sys.stderr)
            return 1
        save(path, new_casebook(a.name, a.traded))
        print(path)
        return 0
    d = load(path)
    if a.cmd == "show":
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "due":
        print(json.dumps(due(d), indent=1))
        return 0
    if a.cmd == "start":
        start(d, a.chapter)
    elif a.cmd == "reason":
        save_reason(d, a.chapter, a.text)
    elif a.cmd == "finish":
        finish(d, a.chapter, a.choice, a.result, a.clue, a.concept)
    elif a.cmd == "review":
        review(d, a.concept, a.answer == "right")
    elif a.cmd == "reminder":
        d["settings"]["next_chapter_reminder"] = a.state
    elif a.cmd == "note-sent":
        d["settings"]["last_note_for"] = d["current_chapter"]
    save(path, d)
    print(json.dumps({"saved": str(path), "current_chapter": d["current_chapter"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
