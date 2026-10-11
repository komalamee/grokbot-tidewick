# Chapter format

One chapter = one Markdown file, `chNN.md`, in this folder. The bot fetches the file for the chapter the player is on, from a pinned tag of this public repo (see `../MANIFEST.md`). Nothing here is fetched from `main`.

Why Markdown and not YAML: story writers can edit it in any editor, and the bot can read it as plain text. The numbers sit in one fenced JSON block, so the maths script can check them with the Python standard library alone.

## Layout (fixed slots, in this order)

```
---
id: ch01                      # file name without .md
season: 1                     # 1 = Beginner, 2 = Intermediate
chapter: 1                    # number shown to the player
title: A right and a promise
concept: one line, the single options idea this chapter teaches
status: skeleton | draft | checked | approved
concept_ids: put-option, right-vs-promise   # saved to the casebook's concepts and review list
clue_id: clue-01               # saved to the casebook's clues, whatever the result
story_status: PLACEHOLDER | DRAFT | FINAL
---

## Learning objectives        numbered list, at most 2
## Scene                      story text the bot tells, word for word. Ends on the case.
## Case                       plain-words table of the inputs in fictional £, then the ```case-json block
## Choices                    lettered list (A, B, C), one line each, as the player sees them
## Reason prompt              the one question asking the player's reason BEFORE they choose
## Expected maths             human-readable working; the case-json block is what gets checked
## Outcome                    the authored end-date price, and the one story line that reveals it
## Companion line             [COMPANION]'s one line naming the idea, plus the teaching truth it must carry
## Learn panel                optional "What did I just learn?": market term, plain meaning, link to this case, one real-world note
## Clue                       what is unlocked. ALWAYS unlocked, whatever the choice or result
## Recap questions            2–3 questions: Q, answer, a short worked example if wrong, and Concept: <id>
```

Every `##` slot must be present and non-empty; `case_maths.py check` fails the chapter otherwise.

## Story slots

Story text uses slots, never names, until the cast is decided: `[KEEPER]` (the player), `[COMPANION]`, `[CHARACTER_A]`, `[CHARACTER_B]`, and so on, plus `[PLACE_1]`, `[DATE]`. Placeholder story is fenced like this so it can't be mistaken for real text:

```
> **[PLACEHOLDER STORY: to be written]** what the scene needs to do, in one or two lines.
```

## The case-json block

```case-json
{
  "unit": "crates",                 // plural noun used in receipts and chart labels
  "today_price": 10.5,              // context only; not used in any result
  "start_cash": 480,                // optional: turns on the ledger checks
  "outcome_price": 12,              // the authored end-date price
  "what_if_prices": [7, 0],         // shown in the receipt and on the chart
  "choices": ["A", "B"],            // ids the player can pick
  "positions": {
    "A": {"label": "Make the promise",
          "legs": [{"kind": "short_put", "units": 10, "strike": 10, "premium": 0.8}],
          "ledger_events": [{"type": "open", "units": 10, "strike": 10, "premium_total": 8},
                            {"type": "expiry", "price": 12}]},
    "B": {"label": "Decline", "legs": []}
  },
  "expected": {
    "A": {"fee_net": 8, "reserve": 100, "breakevens": [9.2], "max_gain": 8, "max_loss": 92,
          "result_at": {"12": 8, "7": -22},
          "ledger": {"after_open": {"cash": 488, "reserved": 100, "available": 388},
                     "at_end": {"cash": 488, "reserved": 0, "realised": 8}}}
  },
  "chart": {"choice": "A", "min": 0, "max": 16, "compare": []}
}
```
(Comments above are for this document only; the real block is strict JSON.)

- **Legs**: `long_call`, `short_call`, `long_put`, `short_put` (units, strike, premium **per unit**) and `goods` (units, basis per unit). A short call needs enough goods to cover it.
- **Positions** can include extra non-choice entries (e.g. the other side of the trade, or a what-if) for the learn panel; they are checked the same way.
- **expected** keys (all optional): `fee_net` (+ in, − out), `reserve` (cash set aside for short puts), `breakevens`, `max_gain`, `max_loss` (positive number, or `"unlimited"`), `result_at` (price → result), `ledger` (`after_open` and/or `at_end` → any of `cash`, `reserved`, `available`, `fee_received`, `realised`, `goods_value`, `unrealised`, `wealth`).
- All money is fictional pounds, at most whole pence. Results exclude costs unless a chapter says otherwise.

## Checks

```
python3 ../engine/case_maths.py check ch01.md ch02.md
python3 ../engine/case_maths.py receipt ch01.md --choice A
python3 ../engine/case_maths.py chart ch01.md --choice A --out ch01-A.png
```
A chapter can't move from `skeleton`/`draft` to `checked` until `check` passes with no FAIL lines.
