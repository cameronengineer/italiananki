"""
Generate flashcard CSV for Italian numbers.

Input:  sources/8_numbers/numbers.csv  (english, italian)
Output: spreadsheets/numbers.csv

Card format (production — English/numeral front, Italian back):
  front_text      = "42 / forty-two"
  front_labels    = "number"
  back_highlight  = Italian word form (e.g. "quarantadue")
  back_text       = ""
  audio           = Italian word form (same as back_highlight)
  generate_image  = "false"  — numbers don't need AI images

The `generate_image` column is read by builder/2_generate_images.py:
if the value is "false" (case-insensitive), that row is skipped during
image generation.
"""

import csv
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

INPUT_CSV  = pathlib.Path(__file__).resolve().parent / "numbers.csv"
OUTPUT_CSV = PROJECT_ROOT / "spreadsheets" / "numbers.csv"

FIELDNAMES = ["front_text", "front_labels", "back_highlight", "back_text", "audio", "generate_image"]


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
            english = row["english"].strip()   # e.g. "42 / forty-two"
            italian = row["italian"].strip()   # e.g. "quarantadue"
            if not english or not italian:
                continue

            writer.writerow(
                {
                    "front_text":     english,
                    "front_labels":   "number",
                    "back_highlight": italian,
                    "back_text":      "",
                    "audio":          italian,
                    "generate_image": "false",
                }
            )
            rows_written += 1

    print(f"Wrote {rows_written} rows → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
