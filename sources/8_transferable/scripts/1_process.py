"""
Process Italian words from the frequency list using OpenRouter.

For each word, the AI provides:
  - English translation
  - Word type(s)
  - Infinitive / base form
  - Jaro similarity score between the Italian word and English translation

Reads:  sources/8_transferable/input/it_50k.txt
Writes: sources/8_transferable/1_process.csv

Supports resume: already-processed words are skipped on re-run.

Usage (from project root, with .venv activated):
    python sources/8_transferable/scripts/1_process.py
"""

import csv
import pathlib
from enum import Enum
from typing import Optional

from Levenshtein import jaro
from openai import OpenAI
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent          # sources/8_transferable/
PROJECT_ROOT = SCRIPT_DIR.parents[2]   # project root

API_KEY_FILE = PROJECT_ROOT / ".openrouter"
INPUT_FILE = SOURCE_DIR / "input" / "it_50k.txt"
OUTPUT_CSV = SOURCE_DIR / "1_process.csv"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "google/gemini-3.1-flash-lite-preview"
LIMIT = 2000


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------
class WordType(str, Enum):
    art = "art"
    adj = "adj"
    adv = "adv"
    conj = "conj"
    f = "f"
    fam = "+fam"
    nfam = "-fam"
    interj = "interj"
    m = "m"
    n = "n"
    nc = "nc"
    nf = "nf"
    nf_el = "nf (el)"
    nm = "nm"
    nmf = "nmf"
    nm_f = "nm/f"
    num = "num"
    obj = "obj"
    dir_obj = "dir obj"
    indir_obj = "indir obj"
    pl = "pl"
    prep = "prep"
    pron = "pron"
    sg = "sg"
    subj = "subj"
    verb = "verb"
    sentence = "sentence"
    other = "other"


class WordAnalysis(BaseModel):
    english_translation: str
    word_types: list[WordType]
    infinitive: Optional[str] = None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not API_KEY_FILE.exists():
        print(f"Error: API key file not found: {API_KEY_FILE}")
        return
    if not INPUT_FILE.exists():
        print(f"Error: Input file not found: {INPUT_FILE}")
        return

    api_key = API_KEY_FILE.read_text(encoding="utf-8").strip()
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    # Resume: load already-processed words
    processed_words: set[str] = set()
    file_exists = OUTPUT_CSV.exists() and OUTPUT_CSV.stat().st_size > 0
    if file_exists:
        with open(OUTPUT_CSV, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("Word"):
                    processed_words.add(row["Word"])
        print(f"Loaded {len(processed_words)} previously processed words.")

    fieldnames = ["Word", "Infinitive", "English_Translation", "Word_Type", "Jaro_Score"]
    mode = "a" if file_exists else "w"

    with (
        open(INPUT_FILE, encoding="utf-8") as infile,
        open(OUTPUT_CSV, mode, newline="", encoding="utf-8") as outfile,
    ):
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()

        count = 0
        for line in infile:
            if count >= LIMIT:
                print(f"Reached limit of {LIMIT} words.")
                break

            parts = line.strip().split()
            if not parts:
                continue
            italian_word = parts[0]

            if italian_word in processed_words:
                print(f"Skipping '{italian_word}' (already processed)")
                continue

            print(f"Processing: {italian_word} …", end=" ", flush=True)

            try:
                completion = client.beta.chat.completions.parse(
                    model=MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Analyze the Italian word.\n"
                                "1. Provide a single, most common English translation. "
                                "Do not provide synonyms or multiple options. "
                                "If it's a verb, provide the infinitive (e.g., 'to eat').\n"
                                "2. Determine its word type(s) from the allowed list.\n"
                                "3. For the infinitive field, apply these transformations in order:\n"
                                "   - If it is a verb: convert to infinitive form\n"
                                "   - If it is a plural noun: convert to singular form\n"
                                "   - If it is a feminine word and a masculine form exists: "
                                "convert to masculine form\n"
                                "   Return the base masculine singular infinitive form. "
                                "If none of these transformations apply, provide the word itself."
                            ),
                        },
                        {"role": "user", "content": f"Word: {italian_word}"},
                    ],
                    response_format=WordAnalysis,
                )

                analysis = completion.choices[0].message.parsed
                translation = analysis.english_translation
                word_types = ", ".join(t.value for t in analysis.word_types)
                infinitive = analysis.infinitive if analysis.infinitive else italian_word
                score = jaro(italian_word, translation)

                writer.writerow({
                    "Word": italian_word,
                    "Infinitive": infinitive,
                    "English_Translation": translation,
                    "Word_Type": word_types,
                    "Jaro_Score": score,
                })
                outfile.flush()
                print(f"→ {translation}  [{word_types}]  score={score:.3f}")
                count += 1

            except Exception as e:
                print(f"\nError processing '{italian_word}': {e}")

    print(f"\nDone. {count} new words written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
