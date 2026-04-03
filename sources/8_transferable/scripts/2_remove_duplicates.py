"""
Deduplicate the processed word list by Infinitive (base form).

When the same base form appears multiple times (e.g. different inflections of
the same verb), only the first occurrence is kept.

Reads:  sources/8_transferable/1_process.csv
Writes: sources/8_transferable/2_remove_duplicates.csv

Usage (from project root, with .venv activated):
    python sources/8_transferable/scripts/2_remove_duplicates.py
"""

import csv
import pathlib

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent  # sources/8_transferable/

INPUT_CSV = SOURCE_DIR / "1_process.csv"
OUTPUT_CSV = SOURCE_DIR / "2_remove_duplicates.csv"

FIELDNAMES = ["Word", "Infinitive", "English_Translation", "Word_Type", "Jaro_Score"]


def main() -> None:
    if not INPUT_CSV.exists():
        print(f"Error: {INPUT_CSV} not found.")
        return

    seen_infinitives: dict[str, dict] = {}

    with open(INPUT_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(row) != len(FIELDNAMES):
                print(f"Warning: unexpected column count, skipping row: {row}")
                continue
            infinitive = row["Infinitive"]
            if infinitive not in seen_infinitives:
                seen_infinitives[infinitive] = dict(row)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(seen_infinitives.values())

    print(f"Input rows : {sum(1 for _ in open(INPUT_CSV, encoding='utf-8')) - 1}")
    print(f"Output rows: {len(seen_infinitives)}  (deduplicated by Infinitive)")
    print(f"Written to : {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
