"""
sources/verbs/generate.py
─────────────────────────
Reads source/verbs.csv and config.yaml, transforms the data into the
project-wide standardised schema, and writes the result to
../../spreadsheets/verbs.csv.

Run from the project root:
    python sources/verbs/generate.py
"""

import csv
import os
import yaml

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_CSV = os.path.join(SCRIPT_DIR, "source", "verbs.csv")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.yaml")

PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
SPREADSHEETS_DIR = os.path.join(PROJECT_ROOT, "spreadsheets")


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_id(index: int) -> str:
    """Generate a stable, unique card ID."""
    return f"verb_{index:03d}"


def build_audio_filename(card_id: str) -> str:
    """Placeholder filename — the builder will create the actual file."""
    return f"{card_id}.mp3"


def transform_row(raw: dict, index: int, config: dict) -> dict:
    """
    Map a row from source/verbs.csv to the standardised spreadsheet schema.
    See spreadsheets/schema.md for full column definitions.
    """
    card_id = build_id(index)
    tags = " ".join(config.get("tags", []))

    return {
        "id": card_id,
        "deck": config["deck_name"],
        "tags": tags,
        "card_type": config.get("card_type", "word"),
        "italian": raw["infinitive"],
        "english": raw["english"],
        "part_of_speech": "verb",
        "gender": "",                        # Not applicable for verbs
        "example_it": raw.get("example_it", ""),
        "example_en": raw.get("example_en", ""),
        "notes": raw.get("notes", ""),
        "audio_file": build_audio_filename(card_id),
        "image_file": "",                    # Not used for this deck
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    config = load_config()
    output_path = os.path.join(SPREADSHEETS_DIR, config["output_file"])

    os.makedirs(SPREADSHEETS_DIR, exist_ok=True)

    rows = []
    with open(SOURCE_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for index, raw_row in enumerate(reader, start=1):
            rows.append(transform_row(raw_row, index, config))

    schema_columns = [
        "id", "deck", "tags", "card_type", "italian", "english",
        "part_of_speech", "gender", "example_it", "example_en",
        "notes", "audio_file", "image_file",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema_columns)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
