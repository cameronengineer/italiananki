"""
Translate the top 2000 Italian verb infinitives (by frequency) to English using OpenRouter.

The AI flags each entry as valid or invalid. Entries that are not proper
Italian verb infinitives (conjugated forms, non-words, pipe-joined combos,
data artefacts, etc.) are removed from the output entirely.

Reads:  sources/3_verbs_infinitive_by_frequency/itwac_verbs_lemmas_notail_2_1_0.csv
Writes: sources/3_verbs_infinitive_by_frequency/verbs_translated.csv

Output columns: italian, english (invalid entries are excluded), valid

Usage (from project root, with .venv activated):
    python sources/3_verbs_infinitive_by_frequency/translate.py
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
SOURCE_CSV = PROJECT_ROOT / "sources" / "3_verbs_infinitive_by_frequency" / "itwac_verbs_lemmas_notail_2_1_0.csv"
OUTPUT_DIR = PROJECT_ROOT / "sources" / "3_verbs_infinitive_by_frequency"
OUTPUT_CSV = OUTPUT_DIR / "verbs_translated.csv"
API_KEY_FILE = PROJECT_ROOT / ".openrouter"

FIELDNAMES = ["italian", "english"]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "google/gemini-3.1-flash-lite-preview"
BATCH_SIZE = 50          # verbs per API call
MAX_WORDS = 2000         # collect this many unique lemmas
RETRY_DELAY = 5          # seconds between retries on rate-limit / server errors
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
    """Return the first `limit` unique verb infinitive lemmas from the dataset."""
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
                    "italian": {
                        "type": "string",
                        "description": "The Italian verb lemma exactly as provided",
                    },
                    "english": {
                        "type": "string",
                        "description": "English infinitive translation (e.g. 'to be', 'to go')",
                    },
                    "valid": {
                        "type": "boolean",
                        "description": (
                            "True if this is a real Italian verb infinitive. "
                            "False if it is a conjugated form, pipe-joined combo, "
                            "misspelling, non-word, or other data artefact."
                        ),
                    },
                },
                "required": ["italian", "english", "valid"],
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
    Ask the model to translate a list of Italian verb infinitives to English
    and flag whether each entry is a valid verb infinitive.

    Returns a dict mapping each lemma to:
        {"english": "<translation>", "valid": "true" | "false"}
    """
    word_list = "\n".join(f"- {w}" for w in words)
    prompt = (
        "You are processing a frequency list of Italian verb lemmas. "
        "Some entries may be data artefacts rather than real verb infinitives — "
        "for example: conjugated forms (e.g. 'sta', 'sono'), pipe-joined combos "
        "(e.g. 'essere|stare'), invented/misspelled words, or non-verbs.\n\n"
        "For each entry, provide the English infinitive translation and set valid=true "
        "if it is a real Italian verb infinitive, or valid=false if it is not.\n\n"
        "Entries to process:\n"
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
                            "name": "verb_translations",
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
                item["italian"]: {
                    "english": item["english"],
                    "valid": "true" if item["valid"] else "false",
                }
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

    # Fallback: return empty translations, marked valid to avoid silent data loss
    return {w: {"english": "", "valid": "true"} for w in words}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    api_key = load_api_key()

    print(f"Loading lemmas from {SOURCE_CSV} …")
    lemmas = load_lemmas()
    print(f"  {len(lemmas)} unique lemmas collected.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Resume support: reload previously processed entries.
    # If the file has a 'valid' column, preserve its value so invalid entries
    # remain filtered out on the next write. If not, default to 'true'.
    done: dict[str, dict[str, str]] = {}
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                done[row["italian"]] = {
                    "english": row["english"],
                    "valid": row.get("valid", "true"),
                }
        print(f"  Resuming — {len(done)} verbs already processed.")

    remaining = [w for w in lemmas if w not in done]
    print(f"  {len(remaining)} verbs to process.")

    results: dict[str, dict[str, str]] = dict(done)
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num, start in enumerate(range(0, len(remaining), BATCH_SIZE), 1):
        batch = remaining[start : start + BATCH_SIZE]
        print(f"  Batch {batch_num}/{total_batches}: processing {len(batch)} verbs …", end=" ", flush=True)
        translations = translate_batch(batch, api_key)
        results.update(translations)
        print("done.")

        # Write incrementally — only include valid entries
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for lemma in lemmas:
                entry = results.get(lemma)
                if entry and entry["valid"] == "true":
                    writer.writerow({"italian": lemma, "english": entry["english"]})

        if batch_num < total_batches:
            time.sleep(1)

    invalid = [l for l in lemmas if results.get(l, {}).get("valid") == "false"]
    print(f"\nDone. Output written to {OUTPUT_CSV}")
    print(f"Total rows: {len([l for l in lemmas if l in results])}")
    print(f"Flagged invalid: {len(invalid)}")


if __name__ == "__main__":
    main()
