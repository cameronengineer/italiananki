"""
Generate flashcard CSV for Italian verbs — imperfetto tense.

Input:  sources/6_verbs_imperfetto_by_frequency/verbs_conjugated.csv
Output: spreadsheets/verbs_imperfetto.csv

Produces 6 rows per verb (one per pronoun), skipping any row where the
conjugated form is empty (partial conjugation run).

Card format (production — English front, Italian back):
  front_text    = English meaning (e.g. "I was")
  front_labels  = "infinitive: {italian} | tense: imperfect | subject: {pronoun}"
  back_highlight = conjugated form (e.g. "ero")
  back_text     = ""
  audio         = conjugated form
  image         = prompt derived from the infinitive — shared across all 6 pronoun rows
"""

import csv
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

INPUT_CSV = pathlib.Path(__file__).resolve().parent / "verbs_conjugated.csv"
OUTPUT_CSV = PROJECT_ROOT / "spreadsheets" / "verbs_imperfetto.csv"

FIELDNAMES = ["front_text", "front_labels", "back_highlight", "back_text", "audio", "image"]

# Pronouns in frequency-natural order; use exact column header strings from the CSV.
PRONOUNS = ["io", "tu", "lui/lei", "noi", "voi", "loro"]
TENSE = "imperfect"


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
            english_infinitive = row["english"].strip()
            action = english_infinitive[3:] if english_infinitive.lower().startswith("to ") else english_infinitive
            image_prompt = f"A simple illustration of the action of {action}"

            for pronoun in PRONOUNS:
                conjugated = row[pronoun].strip()
                if not conjugated:
                    continue  # skip incomplete conjugation entries
                english = row[f"{pronoun}_english"].strip()

                writer.writerow(
                    {
                        "front_text": english,
                        "front_labels": (
                            f"infinitive: {italian} | tense: {TENSE} | subject: {pronoun}"
                        ),
                        "back_highlight": conjugated,
                        "back_text": "",
                        "audio": conjugated,
                        "image": image_prompt,
                    }
                )
                rows_written += 1

    print(f"Wrote {rows_written} rows → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
