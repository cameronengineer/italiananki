"""
builder/media_generator.py
──────────────────────────
Generates audio and image media files for Anki cards.

Audio:  Uses gTTS (Google Text-to-Speech) to produce an Italian .mp3 for
        each card's Italian word or phrase.

Images: Uses Pillow to render a simple text-on-background .png for cards
        that request an image (image_file column is non-empty in the CSV).

Both functions are no-ops if the output file already exists, so re-running
the builder is safe and only generates missing files.
"""

import os


# ── Audio ─────────────────────────────────────────────────────────────────────

def generate_audio(text: str, output_path: str, lang: str = "it") -> None:
    """
    Generate an Italian pronunciation audio file using gTTS.

    Args:
        text:        The Italian text to synthesise (word or short phrase).
        output_path: Full path where the .mp3 should be written.
        lang:        BCP-47 language code (default 'it' for Italian).
    """
    if os.path.exists(output_path):
        return  # Skip if already generated

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        from gtts import gTTS  # type: ignore
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(output_path)
        print(f"  [audio] {os.path.basename(output_path)}")
    except ImportError:
        print("  [audio] gTTS not installed — skipping. Run: pip install gTTS")
    except Exception as exc:
        print(f"  [audio] Failed for '{text}': {exc}")


# ── Images ────────────────────────────────────────────────────────────────────

# Default image dimensions and colours
IMAGE_WIDTH = 400
IMAGE_HEIGHT = 200
BACKGROUND_COLOUR = (255, 248, 220)   # Cornsilk — soft warm background
TEXT_COLOUR = (40, 40, 40)            # Near-black
FONT_SIZE = 48


def generate_image(text: str, output_path: str) -> None:
    """
    Render a simple card image: Italian word centred on a plain background.

    Args:
        text:        The Italian word or phrase to render.
        output_path: Full path where the .png should be written.
    """
    if os.path.exists(output_path):
        return  # Skip if already generated

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore

        img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), color=BACKGROUND_COLOUR)
        draw = ImageDraw.Draw(img)

        # Try to use a system font; fall back to the Pillow default
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", FONT_SIZE)
        except (IOError, OSError):
            font = ImageFont.load_default()

        # Centre the text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (IMAGE_WIDTH - text_w) // 2
        y = (IMAGE_HEIGHT - text_h) // 2

        draw.text((x, y), text, fill=TEXT_COLOUR, font=font)

        img.save(output_path, "PNG")
        print(f"  [image] {os.path.basename(output_path)}")

    except ImportError:
        print("  [image] Pillow not installed — skipping. Run: pip install Pillow")
    except Exception as exc:
        print(f"  [image] Failed for '{text}': {exc}")
