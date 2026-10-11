---
name: tidewick-chapter-player
description: "Tidewick chapter player: use when an Tidewick player says \"play\", \"next chapter\", \"continue\", names a chapter, or answers a case question mid-chapter."
---
# Playing a chapter

Follow `tidewick-core-rules`. Files live in `~/.tidewick/` (`engine/`, `chapters/`, `casebook.json`).

## Before the scene
1. Read the casebook: `python3 ~/.tidewick/engine/casebook.py show`. Use `current_chapter` unless the player names one.
2. If `chapters/chNN.md` isn't there, fetch it from the pinned tag in `MANIFEST.md`, check it against `SHA256SUMS`, then read it. Run `case_maths.py check chapters/chNN.md`; if any line fails, don't play it: say the chapter needs fixing and stop.
3. `casebook.py start chNN`. If review items are due (`casebook.py due`), offer the recap first, once: "Quick recap before we go on, or straight into the chapter?"

## The loop (one step per message)
1. **Scene.** Tell the `## Scene` text word for word, then the `## Case` table (never the JSON).
2. **Reason first.** List `## Choices`, then ask the `## Reason prompt`. Don't take a choice before a reason. If they give both at once, that's fine.
3. Save it: `casebook.py reason chNN "<their words>"`. Then, if needed: "Thanks. Which one: A, B or C?"
4. **Receipt.** Run `case_maths.py receipt chapters/chNN.md --choice X` and show its lines as they are. Then run `case_maths.py chart chapters/chNN.md --choice X --out ~/.tidewick/chNN-X.png` and send the image. For a "decline" choice, chart the chapter's `chart.choice` instead and say it shows the offer they turned down.
5. **Reason back.** One line linking their saved reason to the result, judged on what they knew at the time, never on the outcome alone.
6. **Companion line.** The `## Companion line` text, word for word. Then: "Say \"what did I learn?\" for the market words, or \"go on\" for the clue."
7. **Learn panel** (only if asked): the `## Learn panel` text.
8. **Clue.** The `## Clue` text. It is always unlocked, whatever they chose and whatever the result.
9. **Save.** `casebook.py finish chNN --choice X --result <receipt result> --clue <clue_id> --concept <each concept_id>`.
10. **Close.** After chapter 1 only, ask the routines question in `tidewick-getting-started` first. Then: "That's chapter N. Recap now, or next chapter whenever you're ready?"

## When things go sideways
* "Can I change my answer?" Yes, before the receipt. After it, they can replay the chapter; the first result stays in the casebook, the clue doesn't change.
* Off-topic or real-money questions: core rules §4, then back to the step you were on.
* No Python: tell the chapter from the file and show `## Expected maths` for their choice instead of the receipt. No chart; say so in one line.
* End of chapter 10 and 16: the readiness note (core rules §5).
