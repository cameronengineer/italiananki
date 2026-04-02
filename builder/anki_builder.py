"""
builder/anki_builder.py
───────────────────────
Converts a list of standardised card rows (from a spreadsheets/*.csv) into
a genanki Deck and writes it as an .apkg file.

Card template:
  Front: Italian word / phrase (+ audio player if audio_file is present)
  Back:  English translation, example sentences, gender, notes

The note type (model) is shared across all decks and uses a stable model ID
so that Anki recognises existing notes on re-import.
"""

import os
from typing import Any

# ── Note model ────────────────────────────────────────────────────────────────

# Stable model ID — do not change; Anki uses this to recognise the note type
ITALIAN_MODEL_ID = 9876543210

CARD_FRONT_TEMPLATE = """\
<div class="italian">{{Italian}}</div>
{{#AudioFile}}
  <div class="audio">{{AudioFile}}</div>
{{/AudioFile}}
"""

CARD_BACK_TEMPLATE = """\
{{FrontSide}}
<hr>
<div class="english">{{English}}</div>
{{#Gender}}
  <div class="gender">Gender: <strong>{{Gender}}</strong></div>
{{/Gender}}
{{#ExampleIT}}
  <div class="example">
    <span class="it">{{ExampleIT}}</span>
    <span class="en">{{ExampleEN}}</span>
  </div>
{{/ExampleIT}}
{{#Notes}}
  <div class="notes">{{Notes}}</div>
{{/Notes}}
"""

CARD_CSS = """\
.card { font-family: 'Helvetica Neue', Arial, sans-serif; text-align: center;
        background: #fffdf4; color: #222; padding: 20px; }
.italian { font-size: 2em; font-weight: bold; margin-bottom: 10px; }
.english { font-size: 1.4em; color: #444; margin: 10px 0; }
.gender  { font-size: 0.9em; color: #888; }
.example { font-size: 0.95em; margin-top: 12px; }
.example .it { display: block; font-style: italic; }
.example .en { display: block; color: #666; }
.notes   { font-size: 0.85em; color: #999; margin-top: 10px; }
"""


def make_model():
    """Create and return the genanki note model used by all Italian cards."""
    try:
        import genanki  # type: ignore
    except ImportError:
        raise ImportError("genanki not installed. Run: pip install genanki")

    return genanki.Model(
        ITALIAN_MODEL_ID,
        "Italian Learning Card",
        fields=[
            {"name": "ID"},
            {"name": "Italian"},
            {"name": "English"},
            {"name": "PartOfSpeech"},
            {"name": "Gender"},
            {"name": "ExampleIT"},
            {"name": "ExampleEN"},
            {"name": "Notes"},
            {"name": "AudioFile"},
            {"name": "ImageFile"},
        ],
        templates=[
            {
                "name": "Italian → English",
                "qfmt": CARD_FRONT_TEMPLATE,
                "afmt": CARD_BACK_TEMPLATE,
            }
        ],
        css=CARD_CSS,
    )


# ── Note factory ──────────────────────────────────────────────────────────────

def row_to_note(row: dict, model: Any) -> Any:
    """Convert a single CSV row dict to a genanki Note."""
    try:
        import genanki  # type: ignore
    except ImportError:
        raise ImportError("genanki not installed. Run: pip install genanki")

    audio_field = f"[sound:{row['audio_file']}]" if row.get("audio_file") else ""
    image_field = f"<img src='{row['image_file']}'>" if row.get("image_file") else ""

    # genanki uses a stable GUID per note for de-duplication on import
    note = genanki.Note(
        model=model,
        fields=[
            row.get("id", ""),
            row.get("italian", ""),
            row.get("english", ""),
            row.get("part_of_speech", ""),
            row.get("gender", ""),
            row.get("example_it", ""),
            row.get("example_en", ""),
            row.get("notes", ""),
            audio_field,
            image_field,
        ],
        tags=row.get("tags", "").split(),
        guid=genanki.guid_for(row.get("id", "")),
    )
    return note


# ── Deck builder ──────────────────────────────────────────────────────────────

def build_deck(rows: list[dict], output_path: str) -> None:
    """
    Build a genanki Package (.apkg) from a list of standardised card rows.

    Args:
        rows:        List of row dicts conforming to spreadsheets/schema.md.
        output_path: Full path for the output .apkg file.
    """
    try:
        import genanki  # type: ignore
    except ImportError:
        raise ImportError("genanki not installed. Run: pip install genanki")

    if not rows:
        print("  [build] No rows — skipping deck creation")
        return

    # Derive deck name and ID from the first row
    deck_name = rows[0].get("deck", "Italian")
    # Hash the deck name to a stable int for genanki (keep it positive and < 2^31)
    deck_id = abs(hash(deck_name)) % (10 ** 9)

    model = make_model()
    deck = genanki.Deck(deck_id, deck_name)

    for row in rows:
        note = row_to_note(row, model)
        deck.add_note(note)

    # Collect media files referenced by cards
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    media_files = []
    for row in rows:
        if row.get("audio_file"):
            path = os.path.join(project_root, "media", "audio", row["audio_file"])
            if os.path.exists(path):
                media_files.append(path)
        if row.get("image_file"):
            path = os.path.join(project_root, "media", "images", row["image_file"])
            if os.path.exists(path):
                media_files.append(path)

    package = genanki.Package(deck)
    package.media_files = media_files

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    package.write_to_file(output_path)
