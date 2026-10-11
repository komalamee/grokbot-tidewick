# Fixed files manifest: Tidewick

Every file is fetched from a **pinned tag** of this bot's public repo, never from `main`, and checked against `SHA256SUMS` (same tag) before use. Base URL: `https://raw.githubusercontent.com/<OWNER>/grokbot-tidewick/<TAG>/fixed-files/` (this repo's raw files; `fixed-files/` sits at the repo root). *Placeholder: no release tag has been cut yet.*

| File | What it is | Installed where (player's box) | By which skill, when |
|---|---|---|---|
| `engine/case_maths.py` | Case maths: Black-Scholes, payoffs, breakevens, ledger, receipts, charts, chapter checks | `~/.tidewick/engine/` | `tidewick-getting-started`, after the player says they're ready for chapter 1 |
| `engine/casebook.py` | Reads and writes the player's casebook | `~/.tidewick/engine/` | same |
| `chapters/chNN.md` | One chapter: story, case, checked numbers, panel, clue, recap | `~/.tidewick/chapters/` | `tidewick-chapter-player`, when that chapter starts (one at a time) |
| `chapters/CURRICULUM.md` | The 16-chapter map (for pointing a question to the right chapter) | `~/.tidewick/chapters/` | `tidewick-getting-started`, with the engine |
| `SHA256SUMS` | Checksums for every file above | `~/.tidewick/` | fetched first, every time |

Not installed (repo only): `chapters/FORMAT.md`, `casebook/CASEBOOK.md`, `casebook/casebook.example.json`.

Updating: when a new tag ships, tell the player in one line and fetch only on their yes. The casebook is never overwritten.
Charts need Pillow for PNG; without it `case_maths.py` writes an SVG instead.
