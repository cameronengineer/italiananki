"""
Translate the top 2000 Italian nouns (by frequency) to English using OpenRouter.
The AI also determines the correct definite article for each noun.

Reads:  sources/1_nouns_by_frequency/itwac_nouns_lemmas_notail_2_0_0.csv
Writes: sources/1_nouns_by_frequency/nouns_translated.csv

Output columns:
  italian  — noun with definite article (e.g. "la metro", "il cane", "l'uomo")
  english  — single best English translation

Usage (from project root, with .venv activated):
    python sources/1_nouns_by_frequency/1_translate.py
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
SOURCE_CSV = PROJECT_ROOT / "sources" / "1_nouns_by_frequency" / "itwac_nouns_lemmas_notail_2_0_0.csv"
OUTPUT_DIR = PROJECT_ROOT / "sources" / "1_nouns_by_frequency"
OUTPUT_CSV = OUTPUT_DIR / "nouns_translated.csv"
API_KEY_FILE = PROJECT_ROOT / ".openrouter"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "google/gemini-3.1-flash-lite-preview"
BATCH_SIZE = 50
MAX_WORDS = 1000
RETRY_DELAY = 5
MAX_RETRIES = 3

# Definite articles to strip when recovering bare lemmas from the output CSV
# (used only for resume — order matters: longer prefixes first)
_ARTICLES = ("gli ", "l'", "lo ", "le ", "la ", "il ", "i ")


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
    """Return the first `limit` unique lemmas from the source dataset."""
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


def strip_article(italian: str) -> str:
    """Strip leading definite article to recover the bare lemma (for resume)."""
    lower = italian.lower()
    for art in _ARTICLES:
        if lower.startswith(art):
            return italian[len(art):]
    return italian


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
                        "description": "The bare Italian noun exactly as provided in the input list",
                    },
                    "italian": {
                        "type": "string",
                        "description": (
                            "The noun with its correct Italian definite article "
                            "(e.g. 'la metro', 'il cane', 'l\\'uomo', 'gli zaini')"
                        ),
                    },
                    "english": {
                        "type": "string",
                        "description": "Single best English translation of the noun",
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
def translate_batch(words: list[str], api_key: str) -> dict[str, tuple[str, str]]:
    """
    Translate a batch of bare Italian nouns.
    Returns a dict mapping bare lemma → (article_form, english).
    """
    word_list = "\n".join(f"- {w}" for w in words)
    prompt = (
        "For each Italian noun below, provide:\n"
        "  1. The noun with its correct definite article (il/lo/la/l'/i/gli/le)\n"
        "  2. The single best English translation\n\n"
        "Return each bare noun unchanged in the 'lemma' field for matching.\n\n"
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
                            "name": "noun_translations",
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
                item["lemma"]: (item["italian"], item["english"])
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

    return {w: ("", "") for w in words}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    api_key = load_api_key()

    print(f"Loading lemmas from {SOURCE_CSV} …")
    lemmas = load_lemmas()
    print(f"  {len(lemmas)} unique lemmas loaded.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Resume: read existing output and strip articles to recover bare lemmas
    done: dict[str, tuple[str, str]] = {}  # bare_lemma → (italian_with_article, english)
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                italian = row.get("italian", "").strip()
                english = row.get("english", "").strip()
                if italian:
                    bare = strip_article(italian)
                    done[bare] = (italian, english)
        print(f"  Resuming — {len(done)} words already translated.")

    remaining = [w for w in lemmas if w not in done]
    print(f"  {len(remaining)} words to translate.")

    results: dict[str, tuple[str, str]] = dict(done)
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num, start in enumerate(range(0, len(remaining), BATCH_SIZE), 1):
        batch = remaining[start : start + BATCH_SIZE]
        print(f"  Batch {batch_num}/{total_batches}: translating {len(batch)} words …", end=" ", flush=True)
        translations = translate_batch(batch, api_key)
        for word in batch:
            results[word] = translations.get(word, ("", ""))
        print("done.")

        # Write incrementally so progress is not lost on interruption
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["italian", "english"])
            writer.writeheader()
            for lemma in lemmas:
                if lemma in results:
                    italian_form, english = results[lemma]
                    writer.writerow({"italian": italian_form, "english": english})

        if batch_num < total_batches:
            time.sleep(1)

    total = len([l for l in lemmas if l in results])
    print(f"\nDone. {total} rows written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
