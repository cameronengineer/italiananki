#!/usr/bin/env python3
"""
Translate Italian vocabulary from CILS word lists to English using OpenRouter.

For each word in the vocabulary lists (A1, A2, B1, B2), the AI provides:
  - The Italian word (unchanged from input)
  - The grammatical function (already provided in source CSV)
  - The single best English translation

Reads:  sources/11_cils/a1_vocabulary.csv
        sources/11_cils/a2_vocabulary.csv
        sources/11_cils/b1_vocabulary.csv
        sources/11_cils/b2_vocabulary.csv

Writes: sources/11_cils/a1_vocabulary_translated.csv
        sources/11_cils/a2_vocabulary_translated.csv
        sources/11_cils/b1_vocabulary_translated.csv
        sources/11_cils/b2_vocabulary_translated.csv

Output columns: italian, function, english

Usage (from project root, with .venv activated):
    python sources/11_cils/2_translate.py
"""

import asyncio
import csv
import json
import pathlib
import time
from typing import Dict, List, Tuple

import aiohttp

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "sources" / "11_cils"
API_KEY_FILE = PROJECT_ROOT / ".openrouter"

# Levels to process
LEVELS = ['a1', 'a2', 'b1', 'b2']

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "google/gemini-3.1-flash-lite-preview"
RETRY_DELAY = 5          # seconds between retries
MAX_RETRIES = 3
MAX_CONCURRENT = 10      # maximum concurrent API requests

# ---------------------------------------------------------------------------
# Load API key
# ---------------------------------------------------------------------------
def load_api_key() -> str:
    """Load OpenRouter API key from file."""
    key = API_KEY_FILE.read_text().strip()
    if not key:
        raise ValueError(f"API key file {API_KEY_FILE} is empty.")
    return key


# ---------------------------------------------------------------------------
# Read source data
# ---------------------------------------------------------------------------
def load_vocabulary(csv_path: pathlib.Path) -> List[Tuple[str, str]]:
    """
    Load vocabulary from CSV file.
    Returns list of tuples: (italian, function)
    """
    entries = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            italian = row.get("italian", "").strip()
            function = row.get("function", "").strip()
            if italian and function:
                entries.append((italian, function))
    return entries


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
                        "description": "The Italian word exactly as provided",
                    },
                    "english": {
                        "type": "string",
                        "description": "Single best English translation",
                    },
                },
                "required": ["italian", "english"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def is_noun(function: str) -> bool:
    """Check if the grammatical function indicates a noun."""
    function_lower = function.lower()
    return "sostantivo" in function_lower


def is_adjective(function: str) -> bool:
    """Check if the grammatical function indicates an adjective."""
    function_lower = function.lower()
    return "aggettivo" in function_lower


# ---------------------------------------------------------------------------
# Translation via OpenRouter
# ---------------------------------------------------------------------------
async def translate_word(
    session: aiohttp.ClientSession,
    italian: str,
    function: str,
    api_key: str,
    word_num: int,
    total_words: int
) -> Tuple[str, str, str]:
    """
    Translate a single Italian word to English using async HTTP.
    
    Args:
        session: aiohttp session
        italian: The Italian word
        function: The grammatical function
        api_key: OpenRouter API key
        word_num: Current word number (for progress display)
        total_words: Total number of words
    
    Returns:
        Tuple of (italian_input, italian_formatted, english_translation)
        - For nouns: italian_formatted includes definite article (e.g., "il cane")
        - For adjectives: italian_formatted includes all forms (e.g., "bello/a/i/e" or "intelligente/i" or "blu")
        - For other words: italian_formatted is the same as italian_input
    """
    if is_noun(function):
        prompt = (
            f"Translate this Italian noun to English: {italian}\n"
            f"Grammatical function: {function}\n\n"
            "Provide:\n"
            "1. The noun WITH its correct definite article (il/lo/la/l'/i/gli/le)\n"
            "   Example: 'cane' should become 'il cane'\n"
            "2. The single best English translation (no article needed)\n"
            "   Example: 'dog'\n"
        )
    elif is_adjective(function):
        prompt = (
            f"Translate this Italian adjective to English: {italian}\n"
            f"Grammatical function: {function}\n\n"
            "Provide:\n"
            "1. The adjective with ALL its forms using this format:\n"
            "   - If it changes for gender AND number (4 forms): masc_sg/fem_sg/masc_pl/fem_pl\n"
            "     Example: 'bello/a/i/e'\n"
            "   - If it changes only for number (2 forms): singular/plural\n"
            "     Example: 'intelligente/i'\n"
            "   - If it's invariable (no change): just the single form\n"
            "     Example: 'blu'\n"
            "2. The single best English translation\n"
            "   Example: 'beautiful' or 'intelligent' or 'blue'\n"
        )
    else:
        prompt = (
            f"Translate this Italian word to English: {italian}\n"
            f"Grammatical function: {function}\n\n"
            "Provide the single best English translation."
        )

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "word_translations",
                "strict": True,
                "schema": RESPONSE_SCHEMA,
            },
        },
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                
                # Extract the translation from the first item
                if parsed.get("items") and len(parsed["items"]) > 0:
                    item = parsed["items"][0]
                    italian_result = item.get("italian", italian)
                    english_result = item.get("english", "")
                    print(f"  [{word_num}/{total_words}] '{italian}' → '{italian_result}' / '{english_result}'")
                    return (italian, italian_result, english_result)
                
                print(f"  [{word_num}/{total_words}] '{italian}' → (no result)")
                return (italian, italian, "")

        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            print(f"  [{word_num}/{total_words}] '{italian}' - attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * attempt)
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"  [{word_num}/{total_words}] '{italian}' - parse error attempt {attempt}/{MAX_RETRIES}: {exc}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

    # Fallback: return empty translation
    print(f"  [{word_num}/{total_words}] '{italian}' → (failed after {MAX_RETRIES} attempts)")
    return (italian, italian, "")


# ---------------------------------------------------------------------------
# Process a single level
# ---------------------------------------------------------------------------
async def process_level(level: str, api_key: str) -> None:
    """Process translations for a single CEFR level using concurrent requests."""
    print(f"\n{'='*60}")
    print(f"Processing level {level.upper()}")
    print(f"{'='*60}")
    
    source_csv = SOURCE_DIR / f"{level}_vocabulary.csv"
    output_csv = SOURCE_DIR / f"{level}_vocabulary_translated.csv"
    
    if not source_csv.exists():
        print(f"  WARNING: Source file {source_csv} not found. Skipping.")
        return
    
    print(f"Loading vocabulary from {source_csv} …")
    entries = load_vocabulary(source_csv)
    print(f"  {len(entries)} words loaded.")
    
    # Resume support: check existing output
    # Use italian_original column for clean resume tracking
    done: Dict[str, Tuple[str, str]] = {}
    if output_csv.exists():
        with open(output_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                original = row.get("italian_original", "").strip()
                italian = row.get("italian", "").strip()
                english = row.get("english", "").strip()
                if original and italian:
                    done[original] = (italian, english)
        print(f"  Resuming — {len(done)} words already translated.")
    
    # Determine what still needs translation
    remaining = [(it, fn) for it, fn in entries if it not in done]
    print(f"  {len(remaining)} words to translate.")
    
    if not remaining:
        print(f"  All words already translated!")
        return
    
    # Create results dict from existing translations
    results: Dict[str, Tuple[str, str]] = dict(done)
    total_words = len(remaining)
    
    # Process words concurrently with a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def translate_with_semaphore(
        session: aiohttp.ClientSession,
        italian: str,
        function: str,
        word_num: int
    ) -> Tuple[str, str, str]:
        async with semaphore:
            return await translate_word(session, italian, function, api_key, word_num, total_words)
    
    async with aiohttp.ClientSession() as session:
        # Create all translation tasks
        tasks = [
            translate_with_semaphore(session, italian, function, idx + 1)
            for idx, (italian, function) in enumerate(remaining)
        ]
        
        # Execute all tasks concurrently and gather results
        translations = await asyncio.gather(*tasks)
        
        # Update results with new translations
        for original_italian, italian_result, english_result in translations:
            results[original_italian] = (italian_result, english_result)
    
    # Write final results
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, 
            fieldnames=["italian_original", "italian", "function", "english"]
        )
        writer.writeheader()
        for it, fn in entries:
            if it in results:
                italian_formatted, english = results[it]
                writer.writerow({
                    "italian_original": it,
                    "italian": italian_formatted,
                    "function": fn,
                    "english": english
                })
    
    total = len([it for it, _ in entries if it in results])
    print(f"\nDone. {total} rows written to {output_csv}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    """Main function."""
    api_key = load_api_key()
    print("Starting translation process for all CEFR levels...")
    
    for level in LEVELS:
        await process_level(level, api_key)
    
    print(f"\n{'='*60}")
    print("All levels processed successfully!")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
