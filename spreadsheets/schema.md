# Spreadsheet Schema

All `sources/*/2_generate_flashcards.py` scripts must write a CSV conforming to this schema. The `builder/` reads these CSVs to generate audio and build Anki flashcard decks.

The CSV files in this directory are generated artifacts. Do not edit them manually — re-run the relevant `2_generate_flashcards.py` script to regenerate.

---

## Columns

| Column | Required | Description |
|---|---|---|
| `front_text` | yes | Text shown as the main body on the card front |
| `front_labels` | yes | Contextual metadata shown above the front text as chips. One or more `label: value` pairs separated by ` \| `. Can be a bare word when no value is needed (e.g. `noun`). |
| `back_highlight` | yes | Primary Italian text shown highlighted on the card back. Can be empty. |
| `back_text` | yes | Secondary text on the card back. Can be empty. |
| `audio` | yes | Italian text used to generate the audio file. Must match the text passed to the audio generator exactly. Can be empty. |
| `image` | yes | Text prompt used to generate the card image via AI. For conjugated verb cards, all pronoun rows for the same verb share the same prompt. Can be empty if no image is needed. |

Column order must be: `front_text`, `front_labels`, `back_highlight`, `back_text`, `audio`, `image`.

---

## Card orientation

Cards are production-style: the English word or phrase appears on the front and the Italian on the back. The learner produces the Italian before flipping.

- `front_text` — English
- `front_labels` — context about what kind of answer is expected
- `back_highlight` — the Italian answer
- `back_text` — additional context if needed, otherwise empty
- `audio` — the Italian string to pronounce
- `image` — the prompt used to generate the card image

---

## `front_labels` format

```
noun
adjective
infinitive: essere | tense: present | subject: io
```

Separator between pairs is ` | ` (space, pipe, space). Each pair uses `label: value` format with a space after the colon. A field with no associated value can omit the colon and value entirely.

---

## Rules

1. UTF-8 encoding.
2. Fields containing commas or ` | ` must be quoted.
3. Empty fields must still be present — no columns may be omitted.
