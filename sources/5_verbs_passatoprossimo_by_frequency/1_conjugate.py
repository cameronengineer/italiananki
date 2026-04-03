"""
Conjugate Italian verb infinitives in the passato prossimo tense.

The passato prossimo is formed with the correct auxiliary (avere or essere)
plus the past participle, agreeing in gender/number where required.
Each conjugated form includes the full construction, e.g. 'ho mangiato',
'sono andato/a'.

For each verb the AI returns all six pronoun forms plus English translations.

Reads:  sources/3_verbs_infinitive_by_frequency/verbs_translated.csv
Writes: sources/5_verbs_passatoprossimo_by_frequency/verbs_conjugated.csv

Output columns: italian, english, io, io_english, tu, tu_english,
                lui/lei, lui/lei_english, noi, noi_english,
                voi, voi_english, loro, loro_english

Usage (from project root, with .venv activated):
    python sources/5_verbs_passatoprossimo_by_frequency/1_conjugate.py
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
INPUT_CSV    = PROJECT_ROOT / "sources" / "3_verbs_infinito_by_frequency" / "verbs_translated.csv"
OUTPUT_DIR   = PROJECT_ROOT / "sources" / "5_verbs_passatoprossimo_by_frequency"
OUTPUT_CSV   = OUTPUT_DIR / "verbs_conjugated.csv"
API_KEY_FILE = PROJECT_ROOT / ".openrouter"

FIELDNAMES = [
    "italian", "english",
    "io", "io_english",
    "tu", "tu_english",
    "lui/lei", "lui/lei_english",
    "noi", "noi_english",
    "voi", "voi_english",
    "loro", "loro_english",
]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL            = "google/gemini-3.1-flash-lite-preview"
BATCH_SIZE       = 20    # verbs per API call
RETRY_DELAY      = 5
MAX_RETRIES      = 3
MAX_CONJUGATIONS = 400   # stop after this many total conjugations (including already-done)

# ---------------------------------------------------------------------------
# Load API key
# ---------------------------------------------------------------------------
def load_api_key() -> str:
    key = API_KEY_FILE.read_text().strip()
    if not key:
        raise ValueError(f"API key file {API_KEY_FILE} is empty.")
    return key


# ---------------------------------------------------------------------------
# Read input
# ---------------------------------------------------------------------------
def load_verbs() -> list[dict[str, str]]:
    """Return list of {italian, english} dicts from the translated verbs CSV."""
    verbs: list[dict[str, str]] = []
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["italian"].strip():
                verbs.append({"italian": row["italian"].strip(), "english": row["english"].strip()})
    return verbs


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
                        "description": "The Italian verb infinitive exactly as provided",
                    },
                    "io": {
                        "type": "string",
                        "description": "Passato prossimo for 'io' (e.g. 'ho mangiato', 'sono andato/a')",
                    },
                    "io_english": {
                        "type": "string",
                        "description": "English translation of the 'io' form (e.g. 'I have eaten', 'I went')",
                    },
                    "tu": {
                        "type": "string",
                        "description": "Passato prossimo for 'tu' (e.g. 'hai mangiato', 'sei andato/a')",
                    },
                    "tu_english": {
                        "type": "string",
                        "description": "English translation of the 'tu' form (e.g. 'you have eaten', 'you went')",
                    },
                    "lui_lei": {
                        "type": "string",
                        "description": "Passato prossimo for 'lui/lei' (e.g. 'ha mangiato', 'è andato/a')",
                    },
                    "lui_lei_english": {
                        "type": "string",
                        "description": "English translation of the 'lui/lei' form (e.g. 'he/she has eaten')",
                    },
                    "noi": {
                        "type": "string",
                        "description": "Passato prossimo for 'noi' (e.g. 'abbiamo mangiato', 'siamo andati/e')",
                    },
                    "noi_english": {
                        "type": "string",
                        "description": "English translation of the 'noi' form (e.g. 'we have eaten', 'we went')",
                    },
                    "voi": {
                        "type": "string",
                        "description": "Passato prossimo for 'voi' (e.g. 'avete mangiato', 'siete andati/e')",
                    },
                    "voi_english": {
                        "type": "string",
                        "description": "English translation of the 'voi' form (e.g. 'you all have eaten')",
                    },
                    "loro": {
                        "type": "string",
                        "description": "Passato prossimo for 'loro' (e.g. 'hanno mangiato', 'sono andati/e')",
                    },
                    "loro_english": {
                        "type": "string",
                        "description": "English translation of the 'loro' form (e.g. 'they have eaten')",
                    },
                },
                "required": ["italian", "io", "io_english", "tu", "tu_english", "lui_lei", "lui_lei_english", "noi", "noi_english", "voi", "voi_english", "loro", "loro_english"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Conjugation via OpenRouter
# ---------------------------------------------------------------------------
def conjugate_batch(verbs: list[dict[str, str]], api_key: str) -> dict[str, dict[str, str]]:
    """
    Ask the model to conjugate a list of Italian verb infinitives in the
    passato prossimo tense for all six pronouns, with English translations.

    Returns a dict keyed by infinitive with Italian forms and English translations.
    """
    verb_list = "\n".join(f"- {v['italian']}" for v in verbs)
    prompt = (
        "Conjugate each of the following Italian verb infinitives in the "
        "passato prossimo tense for all six pronouns: io, tu, lui/lei, noi, voi, loro.\n\n"
        "Use the correct auxiliary verb (avere or essere) and past participle. "
        "For essere verbs, show gender agreement with a slash (e.g. 'sono andato/a', "
        "'siamo andati/e').\n\n"
        "For each pronoun form also provide the English translation "
        "(e.g. io → 'I ate' / 'I have eaten', lui/lei → 'he/she ate').\n\n"
        "Return one item per verb with the infinitive, all six conjugated forms, "
        "and their English translations.\n\n"
        "Verbs to conjugate:\n"
        f"{verb_list}"
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
                            "name": "verb_conjugations",
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
                    "io":              item["io"],
                    "io_english":      item["io_english"],
                    "tu":              item["tu"],
                    "tu_english":      item["tu_english"],
                    "lui/lei":         item["lui_lei"],
                    "lui/lei_english": item["lui_lei_english"],
                    "noi":             item["noi"],
                    "noi_english":     item["noi_english"],
                    "voi":             item["voi"],
                    "voi_english":     item["voi_english"],
                    "loro":            item["loro"],
                    "loro_english":    item["loro_english"],
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

    # Fallback: return empty conjugations for this batch
    return {v["italian"]: {"io": "", "io_english": "", "tu": "", "tu_english": "", "lui/lei": "", "lui/lei_english": "", "noi": "", "noi_english": "", "voi": "", "voi_english": "", "loro": "", "loro_english": ""} for v in verbs}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    api_key = load_api_key()

    print(f"Loading verbs from {INPUT_CSV} …")
    verbs = load_verbs()
    print(f"  {len(verbs)} verbs loaded.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Resume support: reload already-conjugated infinitives
    done: set[str] = set()
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done.add(row["italian"])
        print(f"  Resuming — {len(done)} verbs already conjugated.")

    remaining = [v for v in verbs if v["italian"] not in done]
    allowed = max(0, MAX_CONJUGATIONS - len(done))
    if len(remaining) > allowed:
        print(f"  Limiting to {allowed} new conjugations (MAX_CONJUGATIONS={MAX_CONJUGATIONS}).")
        remaining = remaining[:allowed]
    print(f"  {len(remaining)} verbs to conjugate.")

    english: dict[str, str] = {v["italian"]: v["english"] for v in verbs}

    results: dict[str, dict[str, str]] = {}
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num, start in enumerate(range(0, len(remaining), BATCH_SIZE), 1):
        batch = remaining[start : start + BATCH_SIZE]
        print(f"  Batch {batch_num}/{total_batches}: conjugating {len(batch)} verbs …", end=" ", flush=True)
        conjugations = conjugate_batch(batch, api_key)
        results.update(conjugations)
        print("done.")

        mode = "w" if batch_num == 1 else "a"
        with open(OUTPUT_CSV, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if batch_num == 1:
                writer.writeheader()
            for verb in batch:
                inf = verb["italian"]
                conj = results.get(inf, {})
                writer.writerow({
                    "italian":          inf,
                    "english":          english[inf],
                    "io":               conj.get("io", ""),
                    "io_english":       conj.get("io_english", ""),
                    "tu":               conj.get("tu", ""),
                    "tu_english":       conj.get("tu_english", ""),
                    "lui/lei":          conj.get("lui/lei", ""),
                    "lui/lei_english":  conj.get("lui/lei_english", ""),
                    "noi":              conj.get("noi", ""),
                    "noi_english":      conj.get("noi_english", ""),
                    "voi":              conj.get("voi", ""),
                    "voi_english":      conj.get("voi_english", ""),
                    "loro":             conj.get("loro", ""),
                    "loro_english":     conj.get("loro_english", ""),
                })

        if batch_num < total_batches:
            time.sleep(1)

    print(f"\nDone. Output written to {OUTPUT_CSV}")
    print(f"Total rows: {len(remaining)}")


if __name__ == "__main__":
    main()
