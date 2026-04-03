"""
Generate flashcard CSV for Italian verb infinitives.

Input:  sources/3_verbs_infinito_by_frequency/verbs_translated.csv  (italian, english)
Output: spreadsheets/verbs_infinito.csv

Card format (production — English front, Italian back):
  front_text    = English meaning (e.g. "to be")
  front_labels  = "infinitive"
  back_highlight = Italian infinitive (e.g. "essere")
  back_text     = ""
  audio         = Italian infinitive
"""

import csv
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

INPUT_CSV = pathlib.Path(__file__).resolve().parent / "verbs_translated.csv"
OUTPUT_CSV = PROJECT_ROOT / "spreadsheets" / "verbs_infinito.csv"

FIELDNAMES = ["front_text", "front_labels", "back_highlight", "back_text", "audio"]


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    with (
        open(INPUT_CSV, newline="", encoding="utf-8") as in_f,
        open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f,
    ):
        reader = csv.DictReader(in_f)
        writer = csv.DictWriter(out_f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        for row in reader:
            italian = row["italian"].strip()
            english = row["english"].strip()
            if not italian or not english:
                continue

            writer.writerow(
                {
                    "front_text": english,
                    "front_labels": "infinitive",
                    "back_highlight": italian,
                    "back_text": "",
                    "audio": italian,
                }
            )
            rows_written += 1

    print(f"Wrote {rows_written} rows → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
