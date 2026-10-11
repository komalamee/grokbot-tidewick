#!/usr/bin/env python3
"""Banned-phrase and private-data scan for any Grok Bot template (skills, listing, args).

Generalised from the Nomad Pro engine's tools/banned_scan.py (28 Sep 2026).

  python3 banned_scan.py DIR_OR_FILE [...] [--banned banned.txt] [--allow allow.txt] [--private-terms FILE]

1. Banned phrases = GENERIC list below + the bot's own banned.txt (one regex per line).
   Text between <!-- banned-list:start --> and <!-- banned-list:end --> is the bot's do-not-say list and is skipped.
   allow.txt: exact phrases removed from a line before matching (official titles quoted verbatim, etc.). Keep it short.
2. Private data: generic leak markers + --private-terms FILE (other people's names and handles, addresses,
   account numbers, agent IDs; the file lives in the repo root and is gitignored).
   The owner's published name is NOT a private term: the listing has to say "Made by Komal Amin"
   (checklist J5), so listing it makes the scan fail on a file that must carry it (Docs Librarian setup,
   29 Sep 2026). Skills are the other way round: no owner name, pronoun, city or timezone (guardrail 12).
Exit 1 on any hit. This file is skipped (it contains the patterns).
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

# Generic: hype and promises, plus a few advice-as-fact phrases that no bot should say anyway.
# These don't mean a bot needs a disclaimer: add one only if intake says its subject needs it.
# Add product words in banned.txt, not here.
GENERIC_BANNED = [
    r"\bguaranteed?\b", r"\bcertified\b", r"\brisk[- ]free\b", r"\b100% (accurate|safe|compliant)\b",
    r"\bapproved by\b", r"\bendorsed by\b", r"\bofficial partner\b", r"\bnever worry\b", r"\bno surprises\b",
    r"\byou (should|must) (file|claim|invest|buy|sell)\b", r"\bthis is (legal|tax|financial|medical) advice\b",
    r"\bwe recommend (investing|buying|selling)\b", r"\bdiagnos(e|is)\b", r"\bgamified\b",
    r"\binstall(s|ed)? by (thousands|millions)\b", r"\b#1\b", r"\bbest[- ]in[- ]class\b",
]
PRIVATE_DEFAULT = ["/users/", "/home/box", "~/library", "icloud drive", "macbook", "obsidian", "c:\\users\\",
                   "docs.google.com/", "drive.google.com/"]
PRIVATE_REGEX = [r"[\w.+-]+@[\w-]+\.[\w.]+", r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"]
EXTS = {".md", ".py", ".json", ".html", ".txt", ".csv", ".yaml", ".yml", ".ts", ".js"}

def lines_of(path: Path):
    return path.read_text(encoding="utf-8", errors="replace").splitlines()

def load(path, lower=False):
    if not path: return []
    out = [l.rstrip("\n") for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    return [l.lower().strip() for l in out] if lower else [l.strip() for l in out]

def files(targets):
    me = Path(__file__).resolve()
    for t in targets:
        p = Path(t)
        for f in ([p] if p.is_file() else sorted(p.rglob("*"))):
            if f.is_file() and f.suffix in EXTS and f.resolve() != me and "__pycache__" not in f.parts \
               and f.name not in ("banned.txt", "private-terms.txt", "private-terms.example.txt", "allow.txt"):
                yield f

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--banned"); ap.add_argument("--allow"); ap.add_argument("--private-terms")
    a = ap.parse_args(argv)
    banned = GENERIC_BANNED + load(a.banned)
    allow = [re.compile(re.escape(x), re.I) for x in load(a.allow)]
    terms = PRIVATE_DEFAULT + load(a.private_terms, lower=True)
    bh, ph = [], []
    for f in files(a.targets):
        skip = False
        for n, line in enumerate(lines_of(f), 1):
            if "banned-list:start" in line: skip = True
            if "banned-list:end" in line: skip = False; continue
            low = line.lower()
            for t in terms:
                pat = (r"(?<![a-z0-9])" if t[:1].isalnum() else "") + re.escape(t) + (r"(?![a-z0-9])" if t[-1:].isalnum() else "")
                if re.search(pat, low): ph.append((f, n, t, line.strip()[:140]))
            for rx in PRIVATE_REGEX:
                for m in re.finditer(rx, line, re.I): ph.append((f, n, m.group(0), line.strip()[:140]))
            if skip: continue
            clean = line
            for al in allow: clean = al.sub("[allowed]", clean)
            if f.suffix == ".py": clean = re.sub(r"(^\s*|:\s*)pass\s*(#.*)?$", r"\1", clean)
            for pat in banned:
                for m in re.finditer(pat, clean, re.I): bh.append((f, n, m.group(0), line.strip()[:140]))
    print(f"Banned-phrase hits: {len(bh)}")
    for h in bh: print("  {}:{}  [{}]  {}".format(*h))
    print(f"Private-data hits: {len(ph)}")
    for h in ph: print("  {}:{}  [{}]  {}".format(*h))
    return 1 if (bh or ph) else 0

if __name__ == "__main__":
    sys.exit(main())
