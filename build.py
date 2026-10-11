#!/usr/bin/env python3
"""Build create_bot_share_json args for one Grok Bot template, with hard checks.

Generalised from the Nomad Pro v2 build.py (28 Sep 2026). grokbot-template v0.1 (29 Sep 2026): routines
must start off. v0.2 (29 Sep 2026): declared slugs are exempt from the token-like rule.

  python3 build.py [--root .] [--private-terms ../private-terms.txt] [--allow allow.txt] [--check-live DIR]

Reads:   bot.json, routines.json, skills/<slug>/SKILL.md   (paths relative to --root)
Writes:  args/create_bot_share_json.args.json  (only when every check passes; else ...args.FAILED.json)
Fails (exit 1) on: args > 92,000 bytes · any private-data hit · plugin key not "pluginId" or id not a
digit string · gettingStarted not packed · routine slug problems · cron/time mismatch · a routine not
"enabled": false (owner's rule, 29 Sep 2026: routines start off; the owner switches each on) · a plugin the
skills or routines mention but the args don't pack · a --private-terms file that isn't there ·
(--check-live) live SKILL.md != repo SKILL.md.
The slugs bot.json and routines.json declare are exempt from the token-like rule: they are public
kebab-case names, and a slug of 32 characters or more (e.g. a four-word routine slug) used to fail the
documented build until an --allow file was added (Docs Librarian setup, 29 Sep 2026). --allow is still
there for other public strings, such as an engine URL.
Never edits skill text at build time: fix the source file instead (Nomad Pro lesson: live != args).
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

MAX_BYTES = 92_000          # host limit sits between ~98 KB (staged) and ~103 KB (rejected)
KNOWN_PLUGINS = ["Gmail", "Google Calendar", "Google Drive", "Google Sheets", "GitHub", "Slack",
                 "Notion", "Linear", "Vercel", "Stripe"]  # names to look for in skill text
PRIVATE_PATTERNS = [
    (r"[\w.+-]+@[\w-]+\.[\w.]+", "email"),
    (r"/[U]sers/|/home/\w+|C:\\[U]sers\\", "local path"),
    (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "agent/uuid id"),
    (r"\b[A-Za-z0-9_-]{32,}\b", "token-like string"),
    (r"\b\d{1,2}:\d{2} (?!your\b|local\b|their\b)[A-Z][a-z]+ time\b", "owner timezone baked in"),
    (r"docs\.google\.com|drive\.google\.com", "private doc link"),
]
fails: list[str] = []

def fail(msg): fails.append(msg); print("FAIL", msg)

def frontmatter(text, path):
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m: fail(f"{path}: no frontmatter"); return {}, text
    try:
        import yaml; fm = yaml.safe_load(m.group(1)) or {}
    except ImportError:
        fm = {}
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":"); fm[k.strip()] = v.strip().strip('"')
    return fm, text[m.end():]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--private-terms")
    ap.add_argument("--allow", help="file of exact substrings allowed through the private scan (e.g. a public engine URL)")
    ap.add_argument("--check-live", help="live skills folder to compare byte-for-byte")
    a = ap.parse_args()
    root = Path(a.root)
    cfg = json.loads((root / "bot.json").read_text(encoding="utf-8"))
    routines_src = json.loads((root / "routines.json").read_text(encoding="utf-8"))
    gs = cfg["gettingStarted"]
    prefix = gs.removesuffix("-getting-started")

    # Skills
    skills = []
    for slug in cfg["skills"]:
        p = root / "skills" / slug / "SKILL.md"
        if not p.exists(): fail(f"missing skill {p}"); continue
        fm, body = frontmatter(p.read_text(encoding="utf-8"), p)
        if fm.get("name") != slug: fail(f"{slug}: frontmatter name is {fm.get('name')!r}")
        if not str(fm.get("description", "")).strip(): fail(f"{slug}: empty description")
        if not slug.startswith(prefix + "-"): fail(f"{slug}: slug not prefixed with '{prefix}-'")
        skills.append({"name": slug, "description": str(fm["description"]).strip(), "content": body})
        if a.check_live:
            live = Path(a.check_live) / slug / "SKILL.md"
            if not live.exists() or live.read_bytes() != p.read_bytes():
                fail(f"{slug}: live copy differs from repo ({live})")
    if gs not in cfg["skills"]: fail(f"gettingStarted '{gs}' is not among packed skills")

    # Plugins
    plugins = cfg.get("plugins", [])
    for pl in plugins:
        if "plugin_id" in pl: fail(f"plugin {pl.get('name')}: key 'plugin_id' (must be 'pluginId')")
        pid = pl.get("pluginId")
        if not (isinstance(pid, str) and pid.isdigit()): fail(f"plugin {pl.get('name')}: pluginId must be a digit string, got {pid!r}")
        if not pl.get("description"): fail(f"plugin {pl.get('name')}: no description (say access level + use)")
    packed = {pl.get("name") for pl in plugins}

    # Routines
    routines, seen = [], set()
    need = ["slug", "name", "description", "schedule", "cron", "trigger", "enabled", "needs", "quiet_when", "job"]
    for r in routines_src:
        miss = [k for k in need if k not in r]
        if miss: fail(f"routine {r.get('slug')}: missing {miss}"); continue
        s = r["slug"]
        if r["enabled"] is not False:
            fail(f"routine {s}: must be \"enabled\": false (routines start off; the owner switches each on)")
        if s in seen: fail(f"routine slug duplicated: {s}")
        seen.add(s)
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s): fail(f"routine slug not kebab-case: {s}")
        if not s.startswith(prefix + "-") and s not in cfg.get("legacy_routine_slugs", []):
            fail(f"routine slug not prefixed with '{prefix}-': {s} (published slugs never change: list them in bot.json legacy_routine_slugs)")
        t = re.search(r"\b(\d{1,2}):(\d{2})\b", r["schedule"]); c = r["cron"].split()
        if t and len(c) == 5 and c[0].isdigit() and c[1].isdigit() and (int(c[0]), int(c[1])) != (int(t[2]), int(t[1])):
            fail(f"routine {s}: schedule says {t[0]} but cron is '{r['cron']}'")
        if "owner's timezone" not in r["schedule"]: fail(f"routine {s}: schedule must say \"in the owner's timezone\"")
        for n in r["needs"]:
            if n not in packed: fail(f"routine {s} needs {n}, which is not packed")
        content = f"Starts off: runs only after the owner says yes to it. {r['schedule']} (cron {r['cron']}). Trigger: {r['trigger']}. Needs: {', '.join(r['needs']) or 'none'}. " \
                  f"{r['job']} Send nothing when: {r['quiet_when']}"
        routines.append({"slug": s, "name": r["name"], "description": r["description"], "content": content})

    # Slugs this bot declares for itself. Public kebab-case names, so the token-like rule below skips them.
    declared = {gs, *cfg["skills"], *cfg.get("legacy_routine_slugs", []),
                *(r["slug"] for r in routines_src if isinstance(r.get("slug"), str))}

    # Connections parity: every plugin named in skills/routines must be packed
    alltext = " ".join(x["content"] + " " + x["description"] for x in skills + routines)
    for name in KNOWN_PLUGINS:
        if re.search(rf"\b{re.escape(name)}\b", alltext) and name not in packed:
            fail(f"connections parity: skills/routines mention '{name}' but it is not packed ('optional' still means pack it)")

    memory = [{"kind": "profile", "content": m} for m in cfg.get("memory", [])]
    args = {"profile": cfg["profile"], "visibility": cfg.get("visibility", "public"), "memory": memory,
            "plugins": plugins, "gettingStarted": {"skill": gs}, "skills": skills, "routines": routines}

    # Private-data scan (fails; allow-list is explicit)
    allow = [l.strip() for l in Path(a.allow).read_text().splitlines() if l.strip() and not l.startswith("#")] if a.allow else []
    terms = []
    if a.private_terms:
        pt = Path(a.private_terms)
        if pt.exists():
            terms = [l.strip().lower() for l in pt.read_text().splitlines() if l.strip() and not l.startswith("#")]
        else:
            fail(f"--private-terms {pt} not found: copy private-terms.example.txt to it so the scan can run "
                 f"(it is gitignored, and the repo is public)")
    blob = json.dumps(args, ensure_ascii=False, indent=1)
    for al in allow: blob = blob.replace(al, "[allowed]")
    slugged = blob
    for d in sorted(declared, key=len, reverse=True):
        if d: slugged = slugged.replace(d, "[slug]")
    for pat, label in PRIVATE_PATTERNS:
        text = slugged if label == "token-like string" else blob
        for m in re.finditer(pat, text):
            fail(f"private data ({label}): ...{text[max(0, m.start()-40):m.end()+20]!r}")
    low = blob.lower()
    for t in terms:
        if re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", low): fail(f"private term found: {t!r}")

    # Size (same measure as the Nomad Pro build: json.dumps default separators, UTF-8)
    size = len(json.dumps(args, ensure_ascii=False).encode())
    compact = len(json.dumps(args, ensure_ascii=False, separators=(",", ":")).encode())
    print(f"size {size:,} bytes (compact {compact:,}); limit {MAX_BYTES:,}")
    if size > MAX_BYTES: fail(f"args {size:,} bytes > {MAX_BYTES:,}: trim wording, not behaviour")

    print(f"skills {len(skills)} · routines {len(routines)} · plugins {len(plugins)} · memories {len(memory)}")
    out = root / "args"; out.mkdir(exist_ok=True)
    name = "create_bot_share_json.args.json" if not fails else "create_bot_share_json.args.FAILED.json"
    (out / name).write_text(json.dumps(args, ensure_ascii=False, indent=1), encoding="utf-8")
    print(("OK -> " if not fails else f"{len(fails)} FAIL(s) -> ") + str(out / name))
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
