"""
Generate flashcard CSV for Fluent Forever Italian word list.

Input:  sources/9_fluentforever/translated.csv  (english, italian, type, theme)
Output: spreadsheets/fluentforever.csv

Card format (production — English front, Italian back):
  front_text     = English meaning (e.g. "dog")
  front_labels   = "type | theme" (e.g. "noun | Animal")
  back_highlight = Italian word with article (e.g. "il cane")
  back_text      = ""
  audio          = base form before any "/" so TTS reads cleanly
"""

import csv
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

INPUT_CSV = pathlib.Path(__file__).resolve().parent / "translated.csv"
OUTPUT_CSV = PROJECT_ROOT / "spreadsheets" / "fluentforever.csv"

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
            english = row["english"].strip()
            italian = row["italian"].strip()
            word_type = row["type"].strip()
            theme = row["theme"].strip()
            if not english or not italian:
                continue

            front_labels = f"{word_type} | {theme}" if theme else word_type

            writer.writerow(
                {
                    "front_text": english,
                    "front_labels": front_labels,
                    "back_highlight": italian,
                    "back_text": "",
                    "audio": italian.split("/")[0].strip(),
                }
            )
            rows_written += 1

    print(f"Wrote {rows_written} rows → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
