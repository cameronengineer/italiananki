# Requirements: elevenlabs>=1.0.0

import csv
import hashlib
import time
from pathlib import Path

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# --- Path setup ---
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

API_KEY_FILE = PROJECT_ROOT / ".elevenlabs"
SPREADSHEETS_DIR = PROJECT_ROOT / "spreadsheets"
OUTPUT_DIR = PROJECT_ROOT / "media" / "audio"

VOICE_ID = "HuK8QKF35exsCh2e7fLT"
MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"
LANGUAGE_CODE = "it"

VOICE_SETTINGS = VoiceSettings(
    stability=0.5,
    similarity_boost=1.0,
    style=1.0,
    speed=0.7,
)

MAX_RETRIES = 2
RETRY_SLEEP = 5.0
CALL_DELAY = 0.5


def load_api_key(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"API key file not found: {path}\n"
            f"Create it with: echo 'your-key-here' > {path}"
        )
    return path.read_text(encoding="utf-8").strip()


def audio_filename(text: str) -> str:
    """Return the MD5 hash of the text as an MP3 filename."""
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return f"{digest}.mp3"


def collect_audio_strings(spreadsheets_dir: Path) -> list[tuple[str, str]]:
    """
    Walk all CSVs in spreadsheets_dir and collect (source_label, audio_text) pairs.
    Deduplicates by audio text — each unique string is only generated once.
    Returns a list of (label, audio_text) sorted by label for predictable output.
    """
    seen: dict[str, str] = {}  # audio_text -> first source label

    for csv_path in sorted(spreadsheets_dir.glob("*.csv")):
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if "audio" not in (reader.fieldnames or []):
                print(f"  [skip] {csv_path.name} — no 'audio' column")
                continue
            for row in reader:
                text = row.get("audio", "").strip()
                if text and text not in seen:
                    seen[text] = csv_path.name

    return [(label, text) for text, label in seen.items()]


def generate_audio(client: ElevenLabs, text: str, output_path: Path) -> bool:
    """Call ElevenLabs TTS and write MP3 to output_path. Returns True on success."""
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            audio_bytes = client.text_to_speech.convert(
                voice_id=VOICE_ID,
                text=text,
                model_id=MODEL_ID,
                output_format=OUTPUT_FORMAT,
                language_code=LANGUAGE_CODE,
                voice_settings=VOICE_SETTINGS,
            )
            if not isinstance(audio_bytes, (bytes, bytearray)):
                audio_bytes = b"".join(audio_bytes)
            output_path.write_bytes(audio_bytes)
            return True
        except Exception as e:
            print(f"    [error] Attempt {attempt}: {e}")
            if attempt <= MAX_RETRIES:
                print(f"    Retrying in {RETRY_SLEEP}s...")
                time.sleep(RETRY_SLEEP)

    return False


def main() -> None:
    api_key = load_api_key(API_KEY_FILE)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = ElevenLabs(api_key=api_key)

    print(f"Scanning spreadsheets in {SPREADSHEETS_DIR} ...")
    entries = collect_audio_strings(SPREADSHEETS_DIR)

    if not entries:
        print("No audio strings found. Nothing to do.")
        return

    total = len(entries)
    print(f"Found {total} unique audio string(s).\n")

    generated = 0
    skipped = 0
    failed = 0

    for i, (source, text) in enumerate(entries, start=1):
        filename = audio_filename(text)
        output_path = OUTPUT_DIR / filename
        label = f"[{i}/{total}] ({source}) \"{text}\""

        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"{label} — already exists, skipping")
            skipped += 1
            continue

        print(f"{label} — generating...")
        success = generate_audio(client, text, output_path)
        if success:
            print(f"    Saved: {filename}")
            generated += 1
        else:
            print(f"    [fail] Could not generate audio for: {text}")
            failed += 1

        time.sleep(CALL_DELAY)

    print(
        f"\nFinished."
        f"\n  Generated                 : {generated}"
        f"\n  Skipped (already existed) : {skipped}"
        f"\n  Failed                    : {failed}"
        f"\n  Output dir                : {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
