"""
builder/build.py
────────────────
Main entry point for the Anki deck builder.

Pipeline:
  1. Scan spreadsheets/ for all .csv files
  2. For each CSV row, generate audio (and optionally images) via media_generator
  3. Build a .apkg Anki deck file for each CSV via anki_builder
  4. Write .apkg files to output/

Run from the project root:
    python builder/build.py

Options:
    python builder/build.py --deck verbs         # Build one deck only
    python builder/build.py --skip-media         # Skip media generation
"""

import argparse
import csv
import os
import sys

# Ensure sibling modules in builder/ are importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from media_generator import generate_audio, generate_image  # noqa: E402
from anki_builder import build_deck  # noqa: E402

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

SPREADSHEETS_DIR = os.path.join(PROJECT_ROOT, "spreadsheets")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
MEDIA_AUDIO_DIR = os.path.join(PROJECT_ROOT, "media", "audio")
MEDIA_IMAGES_DIR = os.path.join(PROJECT_ROOT, "media", "images")


# ── Media generation ──────────────────────────────────────────────────────────

def process_media_for_row(row: dict, skip_media: bool) -> None:
    """Generate audio and/or image for a single card row if not already present."""
    if skip_media:
        return

    audio_file = row.get("audio_file", "").strip()
    if audio_file:
        audio_path = os.path.join(MEDIA_AUDIO_DIR, audio_file)
        if not os.path.exists(audio_path):
            generate_audio(
                text=row["italian"],
                output_path=audio_path,
            )

    image_file = row.get("image_file", "").strip()
    if image_file:
        image_path = os.path.join(MEDIA_IMAGES_DIR, image_file)
        if not os.path.exists(image_path):
            generate_image(
                text=row["italian"],
                output_path=image_path,
            )


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_spreadsheet(csv_path: str, skip_media: bool) -> None:
    """Process a single spreadsheet: generate media, then build the .apkg deck."""
    deck_name = os.path.splitext(os.path.basename(csv_path))[0]
    print(f"\n[{deck_name}] Reading {csv_path}")

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"[{deck_name}] {len(rows)} cards found")

    # Step 1: media
    for row in rows:
        process_media_for_row(row, skip_media)

    # Step 2: Anki deck
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{deck_name}.apkg")
    build_deck(rows=rows, output_path=output_path)
    print(f"[{deck_name}] Deck written to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build Italian Anki decks")
    parser.add_argument(
        "--deck",
        help="Name of a single deck to build (e.g. verbs). Omit to build all.",
    )
    parser.add_argument(
        "--skip-media",
        action="store_true",
        help="Skip audio and image generation.",
    )
    args = parser.parse_args()

    csv_files = sorted(
        os.path.join(SPREADSHEETS_DIR, f)
        for f in os.listdir(SPREADSHEETS_DIR)
        if f.endswith(".csv")
    )

    if not csv_files:
        print("No CSV files found in spreadsheets/. Run a source generator first.")
        print("  e.g.  python sources/verbs/generate.py")
        sys.exit(1)

    if args.deck:
        csv_files = [p for p in csv_files if os.path.basename(p) == f"{args.deck}.csv"]
        if not csv_files:
            print(f"No spreadsheet found for deck '{args.deck}'")
            sys.exit(1)

    for csv_path in csv_files:
        process_spreadsheet(csv_path, skip_media=args.skip_media)

    print("\nAll done.")


if __name__ == "__main__":
    main()
