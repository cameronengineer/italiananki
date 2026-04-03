"""
Generate flashcard CSV for Italian verbs — passato prossimo tense.

Input:  sources/5_verbs_passatoprossimo_by_frequency/verbs_conjugated.csv
Output: spreadsheets/verbs_passatoprossimo.csv

Produces 6 rows per verb (one per pronoun), skipping any row where the
conjugated form is empty (partial conjugation run).

Card format (production — English front, Italian back):
  front_text    = English meaning (e.g. "I have been")
  front_labels  = "infinitive: {italian} | tense: past | subject: {pronoun}"
  back_highlight = conjugated form (e.g. "sono stato/a")
  back_text     = ""
  audio         = conjugated form
"""

import csv
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

INPUT_CSV = pathlib.Path(__file__).resolve().parent / "verbs_conjugated.csv"
OUTPUT_CSV = PROJECT_ROOT / "spreadsheets" / "verbs_passatoprossimo.csv"

FIELDNAMES = ["front_text", "front_labels", "back_highlight", "back_text", "audio"]

# Pronouns in frequency-natural order; use exact column header strings from the CSV.
PRONOUNS = ["io", "tu", "lui/lei", "noi", "voi", "loro"]
TENSE = "past"


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
                    }
                )
                rows_written += 1

    print(f"Wrote {rows_written} rows → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
