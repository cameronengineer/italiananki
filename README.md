# italiananki

A pipeline that generates Italian-language Anki decks from frequency-ranked word lists. Source data is processed through a series of scripts that translate, conjugate, and format the data into a standard CSV schema, from which Anki packages are built.

All scripts are Python and run inside a local virtual environment. API calls use OpenRouter (LLM) and ElevenLabs (text-to-speech).

---

## How it works

1. Each `sources/` subfolder contains a raw word list and numbered scripts that process it into a translated or conjugated CSV.
2. Each source folder has a `2_generate_flashcards.py` script that converts the processed CSV into the standard spreadsheet schema.
3. `builder/1_generate_audio.py` reads all spreadsheet CSVs and generates MP3 audio files for every unique Italian string.
4. `builder/2_create_decks.py` reads all spreadsheet CSVs and audio files and writes one `.apkg` Anki package per CSV into `output/`.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r builder/requirements.txt
```

API keys are read from plain-text files in the project root:

| File | Used by |
|---|---|
| `.openrouter` | Translation and conjugation scripts |
| `.elevenlabs` | `builder/1_generate_audio.py` |

---

## Directory structure

### `sources/`

Each subfolder is an independent word set. Scripts are numbered and run in order.

#### `1_nouns_by_frequency/`
Top 1000 Italian nouns ranked by corpus frequency. `1_translate.py` calls the LLM to produce an English translation and the correct definite article form (e.g. `la parte`). Output: `nouns_translated.csv` with columns `italian` (article + noun) and `english`.

#### `2_adjectives_by_frequency/`
Top ~500 Italian adjectives. `1_translate.py` translates each adjective. The `italian` column stores all inflected forms as a slash-separated string (e.g. `primo/a/i/e`). Output: `adjectives_translated.csv`.

#### `3_verbs_infinito_by_frequency/`
Top ~1600 Italian verbs in infinitive form. `1_translate.py` translates each verb (e.g. `essere` → `to be`). Output: `verbs_translated.csv`.

#### `4_verbs_presente_by_frequency/`
Conjugations of the top 400 verbs in the present tense. `1_conjugate.py` calls the LLM and returns all six pronoun forms per verb. Output: `verbs_conjugated.csv` with columns `italian`, `english`, and one column per pronoun (`io`, `tu`, `lui/lei`, `noi`, `voi`, `loro`) plus English equivalents.

#### `5_verbs_passatoprossimo_by_frequency/`
Same structure as `4_verbs_presente_by_frequency/` for the passato prossimo tense.

#### `6_verbs_imperfetto_by_frequency/`
Same structure for the imperfetto tense.

#### `7_cafe/`
A manually curated set of common phrases for everyday situations (greetings, ordering, directions, etc.).

#### `8_transferable/`
Italian words whose spelling is similar enough to English that a learner can leverage existing knowledge (cognates). The pipeline lives in `scripts/` and runs in order:

1. `1_process.py` — calls the LLM to translate and classify each word from `input/it_50k.txt`, computing a Jaro similarity score between the Italian word and its English translation.
2. `2_remove_duplicates.py` — deduplicates by base form (infinitive or singular).
3. `3_group_words.py` — applies suffix, prefix, and replacement rules to find transformation chains that maximise the Jaro score, identifying structural spelling patterns between Italian and English.
4. `4_clean.py` — filters to rows where `0.7 <= Initial_Jaro < 1.0` (similar but not identical strings).
5. `5_generate_flashcards.py` — converts `4_clean.csv` to the spreadsheet schema.

---

### `spreadsheets/`

Generated CSV files in the standard schema. One file per source, consumed by `builder/`. Not committed to the repository.

Schema columns: `front_text`, `back_highlight`, `front_labels`, `back_text`, `audio`. Full specification in `spreadsheets/schema.md`.

Card orientation: English on the front, Italian on the back. `front_labels` carries contextual metadata (word type, tense, subject pronoun). `audio` holds the Italian text used to generate the audio file.

---

### `builder/`

- `1_generate_audio.py` — collects unique values from the `audio` column across all spreadsheet CSVs and calls ElevenLabs to produce MP3 files named by MD5 hash of the text. Skips files that already exist. Output: `media/audio/`.
- `2_create_decks.py` — reads all spreadsheet CSVs and builds one Anki `.apkg` per file. Audio files are bundled into each package where present. Output: `output/`.

---

### `media/`

Audio files produced by `builder/1_generate_audio.py`. Filenames are MD5 hashes of the Italian text string. Not committed to the repository.

### `output/`

Anki `.apkg` packages produced by `builder/2_create_decks.py`. Import directly into Anki via File → Import. Not committed to the repository.

---

## Dependencies

`requirements.txt` — dependencies for `sources/` scripts.  
`builder/requirements.txt` — additional dependencies for `builder/` scripts.
