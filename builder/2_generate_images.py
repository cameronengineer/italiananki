# Requirements: requests

"""
Generate images for flashcards using OpenRouter (google/gemini-2.5-flash-image).

Reads:   spreadsheets/*.csv     (must have an `image` column)
Writes:  media/images/<md5>.png

The `image` column value is used as both the deduplication key and the basis
for the filename (MD5-hashed). Each unique `image` value produces exactly one
PNG file, so rows that share the same image value all map to the same file.

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
MODEL = "google/gemini-2.5-flash-image"
LIMIT = None        # Set to an integer to cap the run (useful for testing)
MAX_RETRIES = 2
RETRY_SLEEP = 5.0
WORKERS = 10        # Number of parallel requests


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
    """Return the MD5 hash of the key as a PNG filename."""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return f"{digest}.png"


def build_prompt(image_key: str) -> str:
    """
    Build the detailed image generation prompt from the image key.
    The key is a short English concept string (e.g. 'part', 'the action of be').
    """
    return (
        f"A flat design corporate style icon stock illustration representing "
        f"the concept of '{image_key}'. "
        f"The image should be simple, clear, and suitable for a language learner "
        f"to associate with the word or phrase. "
        f"STRICTLY NO TEXT. Do not include any words, letters, numbers, labels, "
        f"or typography of any kind. The image must be 100% purely visual icon only."
    )


def collect_entries(spreadsheets_dir: Path, only: list[str] | None = None) -> list[tuple[str, str]]:
    """
    Walk CSVs in spreadsheets_dir and collect unique (source_label, image_key)
    pairs from the `image` column. Deduplicates by image key.

    If `only` is given, restrict to those stems (e.g. ["cafe", "nouns"]).
    Returns list of (source_label, image_key).
    """
    seen: dict[str, str] = {}  # image_key -> first source label

    for csv_path in sorted(spreadsheets_dir.glob("*.csv")):
        if only and csv_path.stem not in only:
            continue
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if "image" not in (reader.fieldnames or []):
                print(f"  [skip] {csv_path.name} — no 'image' column")
                continue
            for row in reader:
                key = row.get("image", "").strip()
                if key and key not in seen:
                    seen[key] = csv_path.name

    return [(label, key) for key, label in seen.items()]


def generate_image(api_key: str, prompt: str, output_path: Path) -> bool:
    """
    Call OpenRouter with an image-generation model and write PNG to output_path.
    Returns True on success.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "Italian Flashcards",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"],
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
            print(f"    [error] Attempt {attempt}: HTTP {exc.response.status_code} — {exc}")
        except Exception as exc:
            print(f"    [error] Attempt {attempt}: {exc}")

        if attempt <= MAX_RETRIES:
            print(f"    Retrying in {RETRY_SLEEP}s...")
            time.sleep(RETRY_SLEEP)

    return False


def run_task(
    api_key: str,
    idx: int,
    total: int,
    source: str,
    key: str,
    output_path: Path,
    print_lock: threading.Lock,
) -> bool:
    """Worker task: generate one image and print progress thread-safely."""
    prompt = build_prompt(key)
    with print_lock:
        print(f"[{idx}/{total}] ({source}) \"{key}\"")

    success = generate_image(api_key, prompt, output_path)

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
        print("No image keys found. Nothing to do.")
        return

    # Filter to only entries that need generating
    to_generate = [
        (label, key)
        for label, key in entries
        if not (OUTPUT_DIR / image_filename(key)).exists()
        or (OUTPUT_DIR / image_filename(key)).stat().st_size == 0
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
                source,
                key,
                OUTPUT_DIR / image_filename(key),
                print_lock,
            ): key
            for idx, (source, key) in enumerate(to_generate, start=1)
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
