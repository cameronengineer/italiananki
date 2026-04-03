"""
Translate the top 2000 Italian adjectives (by frequency) to English using OpenRouter.

The Italian column uses the following format:
  - bello/a/i/e   — adjectives with 4 forms (masc sg / fem sg / masc pl / fem pl)
  - intelligente/i — adjectives with 2 forms (singular / plural)
  - blu            — invariable adjectives (no change)

Reads:  sources/2_adjectives_by_frequency/itwac_adj_lemmas_notail_2_1_0.csv
Writes: sources/2_adjectives_by_frequency/adjectives_translated.csv

Usage (from project root, with .venv activated):
    python sources/2_adjectives_by_frequency/translate.py
"""

import csv
import json
import pathlib
import time

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_CSV = PROJECT_ROOT / "sources" / "2_adjectives_by_frequency" / "itwac_adj_lemmas_notail_2_1_0.csv"
OUTPUT_DIR = PROJECT_ROOT / "sources" / "2_adjectives_by_frequency"
OUTPUT_CSV = OUTPUT_DIR / "adjectives_translated.csv"
API_KEY_FILE = PROJECT_ROOT / ".openrouter"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "google/gemini-3.1-flash-lite-preview"
BATCH_SIZE = 50          # adjectives per API call
MAX_WORDS = 500         # collect this many unique lemmas
RETRY_DELAY = 5          # seconds between retries
MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Load API key
# ---------------------------------------------------------------------------
def load_api_key() -> str:
    key = API_KEY_FILE.read_text().strip()
    if not key:
        raise ValueError(f"API key file {API_KEY_FILE} is empty.")
    return key


# ---------------------------------------------------------------------------
# Read source data
# ---------------------------------------------------------------------------
def load_lemmas(limit: int = MAX_WORDS) -> list[str]:
    """Return the first `limit` unique lemmas from the dataset."""
    seen: set[str] = set()
    ordered: list[str] = []
    with open(SOURCE_CSV, newline="", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(ordered) >= limit:
                break
            lemma = row["lemma"].strip().strip('"')
            if lemma and lemma not in seen:
                seen.add(lemma)
                ordered.append(lemma)
    return ordered


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "lemma": {
                        "type": "string",
                        "description": "The base lemma exactly as provided",
                    },
                    "italian": {
                        "type": "string",
                        "description": (
                            "Inflected forms string: "
                            "'bello/a/i/e' for 4-form adjectives, "
                            "'intelligente/i' for 2-form adjectives, "
                            "'blu' for invariable adjectives"
                        ),
                    },
                    "english": {
                        "type": "string",
                        "description": "Single best English translation",
                    },
                },
                "required": ["lemma", "italian", "english"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Translation via OpenRouter
# ---------------------------------------------------------------------------
def translate_batch(words: list[str], api_key: str) -> dict[str, dict[str, str]]:
    """
    Ask the model to translate a list of Italian adjectives to English and
    determine their inflection pattern.

    Returns a dict mapping each base lemma to:
        {"italian": "<formatted forms>", "english": "<translation>"}
    """
    word_list = "\n".join(f"- {w}" for w in words)
    prompt = (
        "For each Italian adjective below, provide the English translation and the Italian forms string.\n\n"
        "Rules for the Italian forms string:\n"
        "- Changes for gender AND number (4 forms): write masc_sg/fem_sg/masc_pl/fem_pl (e.g. bello/a/i/e)\n"
        "- Changes only for number (2 forms): write singular/plural (e.g. intelligente/i)\n"
        "- Invariable (no change): write just the single form (e.g. blu)\n\n"
        "Adjectives to process:\n"
        f"{word_list}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "adjective_translations",
                            "strict": True,
                            "schema": RESPONSE_SCHEMA,
                        },
                    },
                }),
                timeout=60,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return {
                item["lemma"]: {"italian": item["italian"], "english": item["english"]}
                for item in parsed["items"]
            }

        except (requests.HTTPError, requests.Timeout) as exc:
            print(f"  [attempt {attempt}/{MAX_RETRIES}] Request error: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"  [attempt {attempt}/{MAX_RETRIES}] Parse error: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    # Fallback: return bare lemmas with empty translations
    return {w: {"italian": w, "english": ""} for w in words}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    api_key = load_api_key()

    print(f"Loading lemmas from {SOURCE_CSV} …")
    lemmas = load_lemmas()
    print(f"  {len(lemmas)} unique lemmas collected.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Resume support: rebuild done set from existing output using the base lemma
    # (the part of the Italian forms string before the first '/')
    done: dict[str, dict[str, str]] = {}
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                base = row["italian"].split("/")[0]
                done[base] = {"italian": row["italian"], "english": row["english"]}
        print(f"  Resuming — {len(done)} adjectives already translated.")

    remaining = [w for w in lemmas if w not in done]
    print(f"  {len(remaining)} adjectives to translate.")

    results: dict[str, dict[str, str]] = dict(done)
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num, start in enumerate(range(0, len(remaining), BATCH_SIZE), 1):
        batch = remaining[start : start + BATCH_SIZE]
        print(f"  Batch {batch_num}/{total_batches}: translating {len(batch)} adjectives …", end=" ", flush=True)
        translations = translate_batch(batch, api_key)
        results.update(translations)
        print("done.")

        # Write incrementally
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["italian", "english"])
            writer.writeheader()
            for lemma in lemmas:
                if lemma in results:
                    writer.writerow(results[lemma])

        if batch_num < total_batches:
            time.sleep(1)

    print(f"\nDone. Output written to {OUTPUT_CSV}")
    print(f"Total rows: {len([l for l in lemmas if l in results])}")


if __name__ == "__main__":
    main()
