"""
Generate flashcard CSV for Italian-English transferable words (cognates).

These are Italian words whose spelling is similar enough to English that a
learner can transfer existing knowledge (e.g. "favore" → "favor").

Reads:  sources/8_transferable/4_clean.csv
Writes: spreadsheets/transferable.csv  (only when WRITE_OUTPUT = True)

Card format (production — English front, Italian back):
  front_text    = English translation
  front_labels  = primary word type (e.g. "noun", "verb", "adjective")
  back_highlight = Italian word (surface form from the frequency list)
  back_text     = ""
  audio         = Italian word

Usage (from project root, with .venv activated):
    python sources/8_transferable/scripts/5_generate_flashcards.py
"""

import csv
import pathlib

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent          # sources/8_transferable/
PROJECT_ROOT = SCRIPT_DIR.parents[2]   # project root

INPUT_CSV = SOURCE_DIR / "4_clean.csv"
OUTPUT_CSV = PROJECT_ROOT / "spreadsheets" / "transferable.csv"

FIELDNAMES = ["front_text", "front_labels", "back_highlight", "back_text", "audio"]

# Set to True to write spreadsheets/transferable.csv; False to dry-run only.
WRITE_OUTPUT = False

# Map raw Word_Type values → human-readable front_labels
TYPE_LABEL: dict[str, str] = {
    "adj":      "adjective",
    "adv":      "adverb",
    "art":      "article",
    "conj":     "conjunction",
    "f":        "noun",
    "interj":   "interjection",
    "m":        "noun",
    "n":        "noun",
    "nc":       "noun",
    "nf":       "noun",
    "nf (el)":  "noun",
    "nm":       "noun",
    "nmf":      "noun",
    "nm/f":     "noun",
    "num":      "numeral",
    "prep":     "preposition",
    "pron":     "pronoun",
    "verb":     "verb",
    "+fam":     "word",
    "-fam":     "word",
    "other":    "word",
}


def primary_label(word_type: str) -> str:
    """Return a human-readable label from the first entry in a Word_Type string."""
    first = word_type.split(",")[0].strip()
    return TYPE_LABEL.get(first, first)


def main() -> None:
    if not INPUT_CSV.exists():
        print(f"Error: {INPUT_CSV} not found. Run 4_clean.py first.")
        return

    rows_written = 0
    with open(INPUT_CSV, newline="", encoding="utf-8") as in_f:
        reader = csv.DictReader(in_f)

        if WRITE_OUTPUT:
            OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
            out_f = open(OUTPUT_CSV, "w", newline="", encoding="utf-8")
            writer = csv.DictWriter(out_f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
        else:
            out_f = None
            writer = None

        for row in reader:
            word = row["Word"].strip()
            english = row["English_Translation"].strip()
            word_type = row["Word_Type"].strip()

            if not word or not english:
                continue

            if writer:
                writer.writerow({
                    "front_text": english,
                    "front_labels": primary_label(word_type),
                    "back_highlight": word,
                    "back_text": "",
                    "audio": word.split("/")[0].strip(),
                })
            rows_written += 1

        if out_f:
            out_f.close()

    if WRITE_OUTPUT:
        print(f"Wrote {rows_written} rows → {OUTPUT_CSV}")
    else:
        print(f"Dry run: {rows_written} rows (WRITE_OUTPUT=False, nothing written)")


if __name__ == "__main__":
    main()
