"""
Generate flashcard CSVs for CILS vocabulary (one per CEFR level).

Input:  sources/11_cils/*_vocabulary_translated.csv  (italian_original, italian, function, english)
Output: spreadsheets/cils_a1.csv
        spreadsheets/cils_a2.csv
        spreadsheets/cils_b1.csv
        spreadsheets/cils_b2.csv

Card format (production — English front, Italian back):
  front_text     = English meaning (e.g. "dog")
  front_labels   = "CILS A1 | function" (e.g. "CILS A1 | sostantivo maschile")
  back_highlight = Italian word with article/forms (e.g. "il cane" or "bello/a/i/e")
  back_text      = ""
  audio          = base form before any "/" so TTS reads cleanly
"""

import csv
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_DIR = pathlib.Path(__file__).resolve().parent
SPREADSHEETS_DIR = PROJECT_ROOT / "spreadsheets"

FIELDNAMES = ["front_text", "front_labels", "back_highlight", "back_text", "audio"]

LEVELS = ["a1", "a2", "b1", "b2"]


def generate_flashcards_for_level(level: str) -> int:
    """Generate flashcards for a single CEFR level."""
    input_csv = SOURCE_DIR / f"{level}_vocabulary_translated.csv"
    output_csv = SPREADSHEETS_DIR / f"cils_{level}.csv"
    
    if not input_csv.exists():
        print(f"⚠️  Skipping {level.upper()}: {input_csv} not found")
        return 0
    
    SPREADSHEETS_DIR.mkdir(parents=True, exist_ok=True)
    
    rows_written = 0
    with (
        open(input_csv, newline="", encoding="utf-8") as in_f,
        open(output_csv, "w", newline="", encoding="utf-8") as out_f,
    ):
        reader = csv.DictReader(in_f)
        writer = csv.DictWriter(out_f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        
        for row in reader:
            english = row["english"].strip()
            italian = row["italian"].strip()
            function = row["function"].strip()
            
            if not english or not italian:
                continue
            
            # Create front label with CEFR level and grammatical function
            front_labels = f"CILS {level.upper()} | {function}"
            
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
    
    return rows_written


def main() -> None:
    total_rows = 0
    
    for level in LEVELS:
        rows = generate_flashcards_for_level(level)
        if rows > 0:
            output_path = SPREADSHEETS_DIR / f"cils_{level}.csv"
            print(f"✓ {level.upper()}: Wrote {rows} rows → {output_path}")
            total_rows += rows
    
    print(f"\n📊 Total: {total_rows} flashcards generated across {len([l for l in LEVELS if (SOURCE_DIR / f'{l}_vocabulary_translated.csv').exists()])} levels")


if __name__ == "__main__":
    main()
