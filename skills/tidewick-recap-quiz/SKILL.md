---
name: tidewick-recap-quiz
description: "Tidewick recap quiz: use when an Tidewick player says \"quiz me\", \"recap\" or \"test me\", or accepts a recap offered at the start or end of a chapter."
---
# Recap quiz

Follow `tidewick-core-rules`. A recap is a short look back, never a test to pass. It never blocks the story.

## Picking questions (at most 3)
1. Concepts due for review: `casebook.py due`. Take questions from the `## Recap questions` of the chapter each concept came from.
2. Otherwise, the chapter they just finished.
3. If they ask about a chapter they haven't played, say it's coming up and offer that chapter instead.

## Asking
* One question per message. Accept answers in their own words; the meaning matters, not the wording.
* Each question names its concept (`Concept: <id>`). **Right:** one line saying why it's right. `casebook.py review <concept> right`.
* **Not quite:** no "wrong". Show the question's "If wrong" worked example, one short line at a time if it has numbers. `casebook.py review <concept> wrong`.
* Numbers come from the chapter text. Never invent a new question with new numbers.

## Ending
One line, no score: what they've got, and what comes back later ("Breakeven comes back in a couple of chapters"). Then: "Next chapter whenever you're ready."
