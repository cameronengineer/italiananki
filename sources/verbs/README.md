# Deck: Italian Verbs

**Anki deck path:** `Italian::Verbs`

## What this deck covers

Common Italian verbs presented as infinitive → English translation flashcards, with:
- An example sentence in Italian
- The English translation of the example
- Grammar notes (irregularities, conjugation patterns, auxiliary usage)

## Source data

`source/verbs.csv` — each row is one verb:

| Column | Description |
|--------|-------------|
| `infinitive` | The Italian infinitive form |
| `english` | English translation |
| `example_it` | Example sentence in Italian |
| `example_en` | English translation of the example |
| `notes` | Grammar notes and irregular forms |

## How to generate

From the project root:

```bash
python sources/verbs/generate.py
```

This reads `source/verbs.csv` and writes the standardised output to `spreadsheets/verbs.csv`.

## Adding new verbs

Add rows directly to `source/verbs.csv` and re-run `generate.py`.
Keep the format consistent:
- `infinitive` should be the bare infinitive (e.g. `parlare`, not `parlare (to speak)`)
- `notes` should include any irregular conjugation patterns
