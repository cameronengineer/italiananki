"""
Filter the grouped word list to words with a plausible Italian-English
similarity score: keeps rows where 0.7 <= Initial_Jaro < 1.0.

  < 0.7  — too dissimilar; likely not a true cognate / transferable word
  == 1.0 — identical strings; trivial / not useful as a learning card

Reads:  sources/8_transferable/3_group_words.csv
Writes: sources/8_transferable/4_clean.csv

Usage (from project root, with .venv activated):
    python sources/8_transferable/scripts/4_clean.py
"""

import csv
import pathlib

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent  # sources/8_transferable/

INPUT_CSV = SOURCE_DIR / "3_group_words.csv"
OUTPUT_CSV = SOURCE_DIR / "4_clean.csv"


def main() -> None:
    if not INPUT_CSV.exists():
        print(f"Error: {INPUT_CSV} not found.")
        return

    with open(INPUT_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])

        if "Initial_Jaro" not in fieldnames:
            print(f"Error: 'Initial_Jaro' column not found in {INPUT_CSV}")
            return

        rows = list(reader)

    kept = []
    removed = 0

    for row in rows:
        try:
            score = float(row.get("Initial_Jaro", 0))
            if 0.7 <= score < 1.0:
                kept.append(row)
            else:
                removed += 1
        except ValueError:
            print(f"Warning: invalid Initial_Jaro for word '{row.get('Word', '?')}' — skipping")
            removed += 1

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    total = len(rows)
    print(f"Total rows   : {total}")
    print(f"Kept         : {len(kept)}  (0.7 <= Initial_Jaro < 1.0)")
    print(f"Removed      : {removed}")
    print(f"Kept %       : {len(kept) / total * 100:.1f}%" if total else "")
    print(f"Written to   : {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
