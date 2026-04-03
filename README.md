# Italian Anki

A pipeline for generating Italian language Anki flashcard decks from curated source data.

---

## How it works

```
sources/
  verbs/          nouns/        (any future deck)
  generate.py  →  generate.py  →  ...
       │               │
       └───────┬───────┘
               ▼
        spreadsheets/
        verbs.csv   nouns.csv   (standardised schema)
               │
               ▼
           builder/
           build.py
               │
       ┌───────┴───────┐
       ▼               ▼
  media/audio/    media/images/
  *.mp3           *.png
               │
               ▼
           output/
           Italian_Verbs.apkg
           Italian_Nouns.apkg
```

1. **Source generators** (`sources/*/generate.py`) — each deck group maintains its own source CSV and a script that transforms it into the standardised spreadsheet schema.
2. **Spreadsheets** (`spreadsheets/*.csv`) — generated artifacts; never edit by hand. Schema documented in [`spreadsheets/schema.md`](spreadsheets/schema.md).
3. **Builder** (`builder/build.py`) — reads all spreadsheets, generates audio via gTTS and optional images via Pillow, then packages each deck as an `.apkg` using genanki.
4. **Output** (`output/*.apkg`) — import these files directly into Anki.

---

## Project structure

```
italiananki/
├── sources/                  # One folder per deck group
│   ├── verbs/
│   │   ├── generate.py       # Transforms source/ → spreadsheets/verbs.csv
│   │   ├── config.yaml       # Deck name, ID, tags
│   │   ├── README.md
│   │   └── source/
│   │       └── verbs.csv     # Raw Italian/English source data
│   └── nouns/
│       ├── generate.py
│       ├── config.yaml
│       ├── README.md
│       └── source/
│           └── nouns.csv
│
├── spreadsheets/             # Standardised CSV output (generated — do not edit)
│   └── schema.md             # Column definitions for all spreadsheets
│
├── builder/                  # Builds media and .apkg decks from spreadsheets
│   ├── build.py              # Entry point
│   ├── media_generator.py    # gTTS audio + Pillow images
│   ├── anki_builder.py       # genanki deck assembly
│   └── requirements.txt
│
├── media/
│   ├── audio/                # Generated .mp3 pronunciation files
│   └── images/               # Generated card images (optional)
│
├── output/                   # Final .apkg files — import into Anki
│
├── requirements.txt          # Top-level dependencies
└── .gitignore
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate a spreadsheet

```bash
python sources/verbs/generate.py
python sources/nouns/generate.py
```

Each script writes a CSV to `spreadsheets/`.

### 3. Build the Anki decks

```bash
# Build all decks
python builder/build.py

# Build one deck only
python builder/build.py --deck verbs

# Build without regenerating media
python builder/build.py --skip-media
```

Decks are written to `output/*.apkg`.

### 4. Import into Anki

Open Anki → File → Import → select a `.apkg` from `output/`.

---

## Adding a new deck group

1. Create a new folder under `sources/` (e.g. `sources/adjectives/`)
2. Add `config.yaml`, `README.md`, `source/adjectives.csv`, and `generate.py`
   (copy an existing deck's files as a template)
3. Run `python sources/adjectives/generate.py`
4. Run `python builder/build.py --deck adjectives`

The `generate.py` must output a CSV conforming to [`spreadsheets/schema.md`](spreadsheets/schema.md).

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `genanki` | Create `.apkg` Anki deck files |
| `gTTS` | Google Text-to-Speech for Italian audio |
| `Pillow` | Generate card images |
| `pyyaml` | Read `config.yaml` files |
| `pandas` | Optional — useful for data cleaning in generators |