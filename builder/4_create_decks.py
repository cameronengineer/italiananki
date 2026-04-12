# Requirements: genanki>=0.13.0

"""
Generate one Anki .apkg per spreadsheet CSV.

Reads:   spreadsheets/*.csv              (columns: front_text, front_labels, back_highlight, back_text, audio)
Reads:   media/audio_compressed/*.mp3    (produced by builder/3_compress_media.py; falls back to media/audio/)
Reads:   media/images_compressed/*.jpg   (produced by builder/3_compress_media.py; falls back to media/images/)
Writes:  output/<stem>.apkg              (one package per source CSV)
"""

import csv
import hashlib
import re
from pathlib import Path

import genanki

# --- Path setup ---
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

SPREADSHEETS_DIR = PROJECT_ROOT / "spreadsheets"
AUDIO_DIR  = PROJECT_ROOT / "media" / "audio_compressed"
AUDIO_DIR_FALLBACK = PROJECT_ROOT / "media" / "audio"
IMAGE_DIR  = PROJECT_ROOT / "media" / "images_compressed"
IMAGE_DIR_FALLBACK = PROJECT_ROOT / "media" / "images"
OUTPUT_DIR = PROJECT_ROOT / "output"

# ---------------------------------------------------------------------------
# Stable IDs — must never change or Anki will duplicate cards on re-import.
# ---------------------------------------------------------------------------
MODEL_ID = 1944521879  # shared across all decks (same card layout)


def deck_id_for(stem: str) -> int:
    """Derive a stable deck ID from the CSV stem via MD5, in Anki's safe range."""
    digest = hashlib.md5(stem.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % (1 << 30)) + (1 << 30)


DECK_NAMES: dict[str, str] = {
    "adjectives":                "Cam's Decks - Italiano Aggettivi",
    "cafe":                      "Cam's Decks - Italiano Caffè",
    "fluentforever":             "Cam's Decks - Italiano Fluent Forever 625 Words",
    "nouns":                     "Cam's Decks - Italiano Sostantivi",
    "verbs_infinito":            "Cam's Decks - Italiano Verbi Infinito",
    "verbs_presente":            "Cam's Decks - Italiano Verbi Presente",
    "verbs_passatoprossimo":     "Cam's Decks - Italiano Verbi Passato Prossimo",
    "verbs_imperfetto":          "Cam's Decks - Italiano Verbi Imperfetto",
    "verbs_presenteprogressivo": "Cam's Decks - Italiano Verbi Presente Progressivo",
}


def deck_name_for(stem: str) -> str:
    """Return the human-readable deck name for a CSV stem."""
    return DECK_NAMES.get(stem, f"Cam's Decks - Italian {stem.replace('_', ' ').title()}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def audio_filename(text: str) -> str:
    """MD5-hash filename matching builder/1_generate_audio.py."""
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return f"{digest}.mp3"


def image_filename(key: str, ext: str = "jpg") -> str:
    """MD5-hash filename. Compressed images are .jpg; originals are .png."""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return f"{digest}.{ext}"


def resolve_image(key: str) -> tuple[Path, str] | None:
    """
    Return (path, filename) for the image, preferring the compressed .jpg.
    Falls back to the original .png if compressed version doesn't exist.
    """
    jpg_name = image_filename(key, "jpg")
    jpg_path = IMAGE_DIR / jpg_name
    if jpg_path.exists() and jpg_path.stat().st_size > 0:
        return jpg_path, jpg_name

    png_name = image_filename(key, "png")
    png_path = IMAGE_DIR_FALLBACK / png_name
    if png_path.exists() and png_path.stat().st_size > 0:
        return png_path, png_name

    return None


def resolve_audio(text: str) -> tuple[Path, str] | None:
    """
    Return (path, filename) for the audio, preferring media/audio_compressed/.
    Falls back to media/audio/ if compressed version doesn't exist.
    """
    fname = audio_filename(text)
    compressed = AUDIO_DIR / fname
    if compressed.exists() and compressed.stat().st_size > 0:
        return compressed, fname

    original = AUDIO_DIR_FALLBACK / fname
    if original.exists() and original.stat().st_size > 0:
        return original, fname

    return None


def labels_html(front_labels: str) -> str:
    """
    Convert a front_labels string into a row of pill chips.

    Input:  "infinitive: vivere | tense: present | subject: io"
    Output: '<div class="meta-row"><span class="pill infinitive">vivere</span>...'
    """
    if not front_labels.strip():
        return ""
    chips = []
    for part in front_labels.split(" | "):
        part = part.strip()
        if ": " in part:
            label, value = part.split(": ", 1)
        else:
            label, value = part, part
        # Normalise label to a safe CSS class name
        css_class = re.sub(r"[^a-z0-9-]", "-", label.strip().lower())
        chips.append(f'<span class="pill {css_class}">{value.strip()}</span>')
    return '<div class="meta-row">' + "".join(chips) + "</div>"


# ---------------------------------------------------------------------------
# Anki model (shared card template + CSS)
# ---------------------------------------------------------------------------

def build_model() -> genanki.Model:
    css = """
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 18px;
  text-align: center;
  color: #333;
  background-color: #f4f4f9;
  padding: 10px;
}

.card-container {
  background-color: white;
  border-radius: 15px;
  padding: 20px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  max-width: 90%;
  margin: 0 auto;
}

.meta-row {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.pill {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.75em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Label-specific pill colours */
.pill.noun       { background-color: #d1fae5; color: #065f46; }
.pill.adjective  { background-color: #fef3c7; color: #92400e; }
.pill.infinitive { background-color: #dbeafe; color: #1e40af; }
.pill.tense      { background-color: #ede9fe; color: #5b21b6; }
.pill.subject    { background-color: #fce7f3; color: #9d174d; }

.front-text {
  font-size: 2em;
  font-weight: 700;
  color: #2c3e50;
  line-height: 1.3;
}

.back-highlight {
  font-size: 2em;
  font-weight: 700;
  color: #e74c3c;
  margin-bottom: 12px;
}

.back-text {
  font-size: 1.2em;
  color: #2c3e50;
  font-style: italic;
  line-height: 1.5;
}

hr#answer {
  border: 0;
  border-top: 1px solid #ddd;
  margin: 20px 0;
}

.card-image {
  margin-top: 14px;
}

.card-image img {
  max-height: 540px;
  max-width: 100%;
  width: auto;
  height: auto;
  border-radius: 10px;
}
"""

    qfmt = """
<div class="card-container">
  {{#Image}}<div class="card-image">{{Image}}</div>{{/Image}}
  {{FrontLabels}}
  <div class="front-text">{{FrontText}}</div>
</div>
"""

    afmt = """
{{FrontSide}}
<hr id="answer">
<div class="card-container">
  {{#BackHighlight}}<div class="back-highlight">{{BackHighlight}}</div>{{/BackHighlight}}
  <div class="back-text">{{BackText}}</div>
  {{Audio}}
</div>
"""

    return genanki.Model(
        MODEL_ID,
        "Italian Anki Model v2",
        fields=[
            {"name": "FrontText"},
            {"name": "FrontLabels"},
            {"name": "BackHighlight"},
            {"name": "BackText"},
            {"name": "Audio"},
            {"name": "Image"},
        ],
        templates=[
            {
                "name": "Italian Card",
                "qfmt": qfmt,
                "afmt": afmt,
            }
        ],
        css=css,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_deck(csv_path: Path, deck_name: str, deck_id: int, model: genanki.Model) -> tuple[genanki.Deck, list[str], int, int, int]:
    """
    Read a spreadsheet CSV and return a populated Deck plus stats.
    Returns: (deck, media_files, notes_added, notes_missing_audio, notes_missing_image)
    """
    stem = csv_path.stem
    deck = genanki.Deck(deck_id, deck_name)
    media_files: list[str] = []
    notes_added = 0
    missing_audio = 0
    missing_image = 0

    with open(csv_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            front_text = row.get("front_text", "").strip()
            front_labels_raw = row.get("front_labels", "").strip()
            back_highlight = row.get("back_highlight", "").strip()
            back_text = row.get("back_text", "").strip()
            audio_text = row.get("audio", "").strip()
            image_key = back_text if back_text else back_highlight

            if not front_text:
                continue

            # Resolve audio
            if audio_text:
                result = resolve_audio(audio_text)
                if result:
                    audio_path, fname = result
                    audio_field = f"[sound:{fname}]"
                    media_files.append(str(audio_path))
                else:
                    audio_field = ""
                    missing_audio += 1
            else:
                audio_field = ""

            # Resolve image
            if image_key:
                result = resolve_image(image_key)
                if result:
                    img_path, fname = result
                    image_field = f'<img src="{fname}">'
                    media_files.append(str(img_path))
                else:
                    image_field = ""
                    missing_image += 1
            else:
                image_field = ""

            # Stable GUID: based only on content fields, never on media fields.
            # This ensures Anki updates existing notes rather than creating new
            # ones when audio or images are added/changed between runs.
            guid = genanki.guid_for(stem, front_text, back_text)

            note = genanki.Note(
                model=model,
                guid=guid,
                fields=[
                    front_text,
                    labels_html(front_labels_raw),
                    back_highlight,
                    back_text,
                    audio_field,
                    image_field,
                ],
            )
            deck.add_note(note)
            notes_added += 1

    return deck, media_files, notes_added, missing_audio, missing_image


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model = build_model()

    total_notes = 0
    total_missing_audio = 0
    total_missing_image = 0

    for csv_path in sorted(SPREADSHEETS_DIR.glob("*.csv")):
        stem = csv_path.stem
        deck_name = deck_name_for(stem)
        deck_id = deck_id_for(stem)
        output_apkg = OUTPUT_DIR / f"{stem}.apkg"

        deck, media_files, notes_added, missing_audio, missing_image = build_deck(
            csv_path, deck_name, deck_id, model
        )

        package = genanki.Package(deck)
        package.media_files = media_files
        package.write_to_file(str(output_apkg))

        total_notes += notes_added
        total_missing_audio += missing_audio
        total_missing_image += missing_image

        print(
            f"  {deck_name:<40}  {notes_added:>5} notes"
            f"  ({missing_audio} without audio)"
            f"  ({missing_image} without image)"
            f"  → {output_apkg.name}"
        )

    print(
        f"\nFinished."
        f"\n  Total notes written       : {total_notes}"
        f"\n  Total missing audio       : {total_missing_audio}"
        f"\n  Total missing image       : {total_missing_image}"
        f"\n  Output dir                : {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
