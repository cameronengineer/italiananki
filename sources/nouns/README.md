# Deck: Italian Nouns

**Anki deck path:** `Italian::Nouns`

## What this deck covers

Common Italian nouns with gender, example sentences, and grammar notes covering:
- Grammatical gender (masculine/feminine)
- Irregular plurals
- Polysemous words (multiple meanings)
- Invariable nouns (no plural change)

## Source data

`source/nouns.csv` — each row is one noun:

| Column | Description |
|--------|-------------|
| `italian` | The Italian noun |
| `english` | English translation |
| `gender` | `m` (masculine) or `f` (feminine) |
| `example_it` | Example sentence in Italian |
| `example_en` | English translation of the example |
| `notes` | Grammar notes, irregular plurals, special usage |

## How to generate

From the project root:

```bash
python sources/nouns/generate.py
```

This reads `source/nouns.csv` and writes the standardised output to `spreadsheets/nouns.csv`.
Nouns also get an additional `gender_m` or `gender_f` tag appended automatically.

## Adding new nouns

Add rows directly to `source/nouns.csv` and re-run `generate.py`.
Always include the `gender` column — it is required for article and adjective agreement notes.
If the plural is irregular, document it in `notes`.
