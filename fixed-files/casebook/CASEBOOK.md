# Casebook: the player's progress

The casebook is one small JSON file on the player's own box, at `~/.tidewick/casebook.json`. The bot reads it before every chapter and writes it after. It is never sent or shared. `engine/casebook.py` is the only thing that writes it, so the format stays valid.

The bot also keeps one general memory: that the casebook exists and where. Progress itself lives in the file, not in memory, so it survives a long gap and can be read back exactly.

## Fields

| Field | What it holds |
|---|---|
| `version` | Format version (1) |
| `player.name` | What the player asked to be called |
| `player.traded_before` | `never`, `a-little` or `yes`, from getting-started. Sets pace only, never skips safety |
| `player.started_on` | Date of the first chapter (YYYY-MM-DD, the box's date) |
| `current_chapter` | The next chapter to play, e.g. `ch02` |
| `chapters.chNN.status` | `in-progress` or `done` |
| `chapters.chNN.reason` | The player's own reason, saved **before** they chose. Used later to compare reason with outcome |
| `chapters.chNN.choice` | The letter they picked |
| `chapters.chNN.result_gbp` | Their result in fictional £, from the receipt |
| `clues[]` | Clue ids found, with the chapter. Added on finishing a chapter, whatever the result |
| `concepts[]` | Concept ids learned (e.g. `put-option`, `cash-secured-put`) |
| `review[]` | Concepts queued for the recap quiz: `due_at` chapter and how many times answered right |
| `settings.next_chapter_reminder` | `off` (default) or `on` |
| `settings.last_note_for` | The chapter a reminder was last sent for, so it's never sent twice for the same chapter |

Review rule (a suggestion, still to be confirmed): a concept comes back two chapters after it's learned; a right answer pushes it two chapters on, two right answers retire it, a wrong answer brings it back next chapter.

See `casebook.example.json` for a casebook after chapter 1.
