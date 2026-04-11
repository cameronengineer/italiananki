# Requirements: requests

"""
Generate images for flashcards using OpenRouter.

Two-phase process per image:
  1. Text AI (google/gemini-3.1-flash-lite-preview) reads the full flashcard row
     and writes a precise image generation prompt that reflects the Italian meaning,
     avoiding ambiguous English interpretations.
  2. Image AI (black-forest-labs/flux.2-klein-4b) generates the image from that prompt.

Reads:   spreadsheets/*.csv     (must have a `back_highlight` column)
Writes:  media/images/<md5>.png

The `back_highlight` value is MD5-hashed to produce the output filename.
Each unique `back_highlight` value produces exactly one PNG file.

Skips entries where the output file already exists and is non-empty (resume).

Usage (from project root, with .venv activated):
    python builder/2_generate_images.py                  # all CSVs
    python builder/2_generate_images.py cafe             # single CSV
    python builder/2_generate_images.py cafe nouns       # multiple CSVs
"""

import argparse
import base64
import csv
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

API_KEY_FILE = PROJECT_ROOT / ".openrouter"
SPREADSHEETS_DIR = PROJECT_ROOT / "spreadsheets"
OUTPUT_DIR = PROJECT_ROOT / "media" / "images"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TEXT_MODEL  = "google/gemini-3.1-flash-lite-preview"   # cheap text AI for prompt generation
IMAGE_MODEL = "black-forest-labs/flux.2-klein-4b"      # $0.014/image — 3× cheaper than Gemini

LIMIT = None        # Set to an integer to cap the run (useful for testing)
MAX_RETRIES = 2
RETRY_SLEEP = 5.0
WORKERS = 10        # Number of parallel workers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_api_key(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"API key file not found: {path}\n"
            f"Create it with: echo 'your-key-here' > {path}"
        )
    return path.read_text(encoding="utf-8").strip()


def image_filename(key: str) -> str:
    """Return the MD5 hash of the image key as a PNG filename."""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return f"{digest}.png"


def collect_entries(spreadsheets_dir: Path, only: list[str] | None = None) -> list[dict]:
    """
    Walk CSVs in spreadsheets_dir and collect unique flashcard rows keyed by
    `back_highlight`. Returns a list of dicts with keys:
        source, front_text, front_labels, back_highlight, back_text, audio

    Deduplicates by image key: `back_text` when non-empty (verb infinitive),
    otherwise `back_highlight`. This collapses all conjugated forms of the same
    verb down to a single image keyed on the infinitive.
    Skips CSVs that have no `back_highlight` column.
    """
    seen: dict[str, dict] = {}  # image_key -> entry dict

    for csv_path in sorted(spreadsheets_dir.glob("*.csv")):
        if only and csv_path.stem not in only:
            continue
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            if "back_highlight" not in fieldnames:
                print(f"  [skip] {csv_path.name} — no 'back_highlight' column")
                continue
            for row in reader:
                back_highlight = row.get("back_highlight", "").strip()
                back_text      = row.get("back_text", "").strip()
                key = back_text if back_text else back_highlight
                if key and key not in seen:
                    seen[key] = {
                        "source":         csv_path.name,
                        "image_key":      key,
                        "front_text":     row.get("front_text", "").strip(),
                        "front_labels":   row.get("front_labels", "").strip(),
                        "back_highlight": back_highlight,
                        "back_text":      back_text,
                        "audio":          row.get("audio", "").strip(),
                    }

    return list(seen.values())


def describe_image(api_key: str, entry: dict) -> str | None:
    """
    Call the text AI with the full flashcard row to produce a specific,
    unambiguous image generation prompt tailored to the Italian meaning.
    Returns the prompt string, or None on failure.
    """
    front_text   = entry["front_text"]
    front_labels = entry["front_labels"]
    back_highlight = entry["back_highlight"]
    back_text    = entry["back_text"]

    infinitive_line = f"\n- Italian infinitive: {back_text}" if back_text else ""

    user_content = (
        f"- English: {front_text}\n"
        f"- Type / context: {front_labels}\n"
        f"- Italian: {back_highlight}"
        f"{infinitive_line}\n\n"
        f"Write the image generation prompt."
    )

    system_content = (
        "You generate image prompts for Italian language flashcard illustrations. "
        "Given a flashcard's data, write a single specific image generation prompt "
        "(2–3 sentences) for a flat design, minimalist icon-style illustration. "
        "The Italian word/phrase takes precedence over the English when the English "
        "is ambiguous — the image must accurately represent the Italian meaning. "
        "The image must be simple, clear, and suitable for a language learner. "
        "STRICTLY NO TEXT, letters, numbers, or labels in the image. "
        "Respond with only the image prompt, nothing else."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": TEXT_MODEL,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user",   "content": user_content},
        ],
    }

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            description = result["choices"][0]["message"]["content"].strip()
            if description:
                return description
            print(f"    [warn] Empty description from text AI for: {back_highlight}")
            return None

        except requests.HTTPError as exc:
            print(f"    [error] Text AI attempt {attempt}: HTTP {exc.response.status_code} — {exc}")
        except Exception as exc:
            print(f"    [error] Text AI attempt {attempt}: {exc}")

        if attempt <= MAX_RETRIES:
            time.sleep(RETRY_SLEEP)

    return None


def generate_image(api_key: str, description: str, output_path: Path) -> bool:
    """
    Call OpenRouter with FLUX.2 Klein to generate an image from `description`
    and write the PNG to output_path. Returns True on success.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "Italian Flashcards",
    }
    payload = {
        "model": IMAGE_MODEL,
        "messages": [{"role": "user", "content": description}],
        "modalities": ["image"],
    }

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()

            if not result.get("choices"):
                print(f"    [error] No choices in response: {result}")
                return False

            message = result["choices"][0]["message"]
            images = message.get("images")

            if not images:
                print(f"    [error] No images in response message: {message}")
                return False

            image_url = images[0]["image_url"]["url"]
            if not image_url.startswith("data:image/"):
                print(f"    [error] Unexpected image URL format: {image_url[:60]}...")
                return False

            _, encoded = image_url.split(",", 1)
            output_path.write_bytes(base64.b64decode(encoded))
            return True

        except requests.HTTPError as exc:
            print(f"    [error] Image gen attempt {attempt}: HTTP {exc.response.status_code} — {exc}")
        except Exception as exc:
            print(f"    [error] Image gen attempt {attempt}: {exc}")

        if attempt <= MAX_RETRIES:
            print(f"    Retrying in {RETRY_SLEEP}s...")
            time.sleep(RETRY_SLEEP)

    return False


def run_task(
    api_key: str,
    idx: int,
    total: int,
    entry: dict,
    output_path: Path,
    print_lock: threading.Lock,
) -> bool:
    """Worker task: generate image description then the image itself."""
    key = entry["back_highlight"]

    with print_lock:
        print(f"[{idx}/{total}] ({entry['source']}) \"{key}\"")

    # Phase 1: text AI generates a precise image description
    description = describe_image(api_key, entry)
    if not description:
        with print_lock:
            print(f"  [fail] [{idx}/{total}] could not generate description for: {key}")
        return False

    # Phase 2: image AI generates the image
    success = generate_image(api_key, description, output_path)

    with print_lock:
        if success:
            print(f"  [ok]   [{idx}/{total}] {output_path.name}")
        else:
            print(f"  [fail] [{idx}/{total}] {key}")

    return success


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate flashcard images.")
    parser.add_argument(
        "csvs",
        nargs="*",
        metavar="CSV",
        help="Spreadsheet stem(s) to process (e.g. cafe nouns). Omit to process all.",
    )
    args = parser.parse_args()
    only = args.csvs or None

    api_key = load_api_key(API_KEY_FILE)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if only:
        print(f"Scanning spreadsheets in {SPREADSHEETS_DIR} (filtered: {', '.join(only)}) ...")
    else:
        print(f"Scanning spreadsheets in {SPREADSHEETS_DIR} ...")
    entries = collect_entries(SPREADSHEETS_DIR, only=only)

    if not entries:
        print("No entries found. Nothing to do.")
        return

    # Filter to only entries that need generating
    to_generate = [
        entry
        for entry in entries
        if not (OUTPUT_DIR / image_filename(entry["image_key"])).exists()
        or (OUTPUT_DIR / image_filename(entry["image_key"])).stat().st_size == 0
    ]

    if LIMIT is not None:
        to_generate = to_generate[:LIMIT]

    total_entries = len(entries)
    total_to_generate = len(to_generate)
    skipped = total_entries - total_to_generate

    print(f"Found {total_entries} unique image key(s). {skipped} already exist, {total_to_generate} to generate.\n")
    print("=" * 80)

    if total_to_generate == 0:
        print("All images already exist. Nothing to do.")
        return

    print(f"Running with {WORKERS} parallel workers.\n")

    generated = 0
    failed = 0
    print_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(
                run_task,
                api_key,
                idx,
                total_to_generate,
                entry,
                OUTPUT_DIR / image_filename(entry["image_key"]),
                print_lock,
            ): entry["image_key"]
            for idx, entry in enumerate(to_generate, start=1)
        }

        for future in as_completed(futures):
            try:
                success = future.result()
            except Exception as exc:
                key = futures[future]
                print(f"  [exception] {key}: {exc}")
                success = False

            if success:
                generated += 1
            else:
                failed += 1

    print("\n" + "=" * 80)
    print(
        f"\nFinished."
        f"\n  Generated                 : {generated}"
        f"\n  Skipped (already existed) : {skipped}"
        f"\n  Failed                    : {failed}"
        f"\n  Output dir                : {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
