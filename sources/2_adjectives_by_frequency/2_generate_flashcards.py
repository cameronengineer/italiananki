"""
Generate flashcard CSV for Italian adjectives.

Input:  sources/2_adjectives_by_frequency/adjectives_translated.csv  (italian, english)
Output: spreadsheets/adjectives.csv

The `italian` column stores full inflected forms, e.g. "primo/a/i/e", "grande/i", "blu".
The base form for audio is everything before the first '/'.

Card format (production — English front, Italian back):
  front_text    = English meaning
  front_labels  = "adjective"
  back_highlight = full inflected forms string (e.g. "primo/a/i/e")
  back_text     = ""
  audio         = base form (e.g. "primo")
"""

import csv
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

INPUT_CSV = pathlib.Path(__file__).resolve().parent / "adjectives_translated.csv"
OUTPUT_CSV = PROJECT_ROOT / "spreadsheets" / "adjectives.csv"

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

            # Base form = everything before the first '/'
            base_form = italian.split("/")[0]

            writer.writerow(
                {
                    "front_text": english,
                    "front_labels": "adjective",
                    "back_highlight": italian,
                    "back_text": "",
                    "audio": base_form,
                }
            )
            rows_written += 1

    print(f"Wrote {rows_written} rows → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
