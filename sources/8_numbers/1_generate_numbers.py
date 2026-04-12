"""
Generate numbers.csv — 400 Italian number flashcard entries.

Output: sources/8_numbers/numbers.csv
Columns:
  english  — "42 / forty-two"
  italian  — "quarantadue"

Number distribution (400 total):
  Band 1:   0–100        → all 101 integers (foundational, daily-use)
  Band 2:   101–999      → ~100 numbers (round hundreds, half-hundreds, random fill)
  Band 3:  1,000–9,999   → ~100 numbers (round thousands, half-thousands, random fill)
  Band 4: 10,000–999,999 → ~98 numbers  (tens/hundreds of thousands, random fill)
  Extra:  1,000,000      → 1 landmark number
  Total:   400

A fixed random seed ensures the output is deterministic.
"""

import csv
import random
from pathlib import Path

from num2words import num2words

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RANDOM_SEED = 42
TARGET_TOTAL = 400
OUTPUT_FILE = Path(__file__).parent / "numbers.csv"

# ---------------------------------------------------------------------------
# Band definitions
# ---------------------------------------------------------------------------

# Band 1: 0–100 — all mandatory
BAND1 = list(range(0, 101))  # 101 numbers

# Band 2: 101–999 — mandatory anchors + random fill
BAND2_MANDATORY = sorted({
    # Round hundreds
    200, 300, 400, 500, 600, 700, 800, 900,
    # Half-hundreds (x50)
    150, 250, 350, 450, 550, 650, 750, 850, 950,
    # Common real-world numbers
    101, 110, 111, 120, 125, 200, 365, 500, 999,
})
BAND2_POOL = list(range(101, 1000))
BAND2_TARGET = 100  # total numbers in this band

# Band 3: 1,000–9,999 — mandatory anchors + random fill
BAND3_MANDATORY = sorted({
    # Round thousands
    1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000,
    # Half-thousands
    1500, 2500, 3500, 4500, 5500, 6500, 7500, 8500, 9500,
    # Common real-world numbers
    1001, 1100, 1200, 1492, 1776, 1900, 1945, 1999, 2001, 9999,
})
BAND3_POOL = list(range(1000, 10000))
BAND3_TARGET = 100  # total numbers in this band

# Band 4: 10,000–999,999 — mandatory anchors + random fill
BAND4_MANDATORY = sorted({
    # Tens of thousands
    10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000,
    # Hundreds of thousands
    100000, 200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000,
    # Common real-world figures
    10500, 25000, 50000, 75000, 100000, 150000, 250000, 500000, 999999,
})
BAND4_POOL = list(range(10000, 1000000))
# Band 4 target is calculated below to hit exactly TARGET_TOTAL

# Landmark extra
EXTRAS = [1_000_000]

# ---------------------------------------------------------------------------
# Build the full number list
# ---------------------------------------------------------------------------

def fill_band(mandatory: list[int], pool: list[int], target: int, rng: random.Random) -> list[int]:
    """Return `target` numbers: all mandatory ones + random fill from pool."""
    result = set(mandatory)
    remaining = [x for x in pool if x not in result]
    rng.shuffle(remaining)
    needed = max(0, target - len(result))
    result.update(remaining[:needed])
    return sorted(result)


def build_number_list() -> list[int]:
    rng = random.Random(RANDOM_SEED)

    band1 = BAND1  # 101 numbers, fixed

    band2 = fill_band(BAND2_MANDATORY, BAND2_POOL, BAND2_TARGET, rng)

    band3 = fill_band(BAND3_MANDATORY, BAND3_POOL, BAND3_TARGET, rng)

    # Calculate band4 target so the grand total hits TARGET_TOTAL exactly
    used = len(band1) + len(band2) + len(band3) + len(EXTRAS)
    band4_target = TARGET_TOTAL - used
    band4 = fill_band(BAND4_MANDATORY, BAND4_POOL, band4_target, rng)

    all_numbers = sorted(set(band1 + band2 + band3 + band4 + EXTRAS))

    # Trim to exactly TARGET_TOTAL if deduplication pushed us over
    # (shouldn't happen with the logic above, but defensive)
    if len(all_numbers) > TARGET_TOTAL:
        all_numbers = all_numbers[:TARGET_TOTAL]

    return all_numbers


# ---------------------------------------------------------------------------
# Italian / English word conversion
# ---------------------------------------------------------------------------

def to_italian(n: int) -> str:
    return num2words(n, lang="it")


def to_english_word(n: int) -> str:
    return num2words(n, lang="en")


def english_field(n: int) -> str:
    """Return e.g. '42 / forty-two'."""
    return f"{n} / {to_english_word(n)}"


# ---------------------------------------------------------------------------
# Write CSV
# ---------------------------------------------------------------------------

def write_csv(numbers: list[int], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["english", "italian"])
        for n in numbers:
            writer.writerow([english_field(n), to_italian(n)])
    print(f"Wrote {len(numbers)} rows to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    numbers = build_number_list()

    # Report distribution
    bands = [
        ("0–100",        0,      100),
        ("101–999",      101,    999),
        ("1,000–9,999",  1000,   9999),
        ("10,000–999,999", 10000, 999999),
        ("1,000,000+",  1000000, 10**9),
    ]
    print(f"Total numbers: {len(numbers)}")
    for label, lo, hi in bands:
        count = sum(1 for n in numbers if lo <= n <= hi)
        print(f"  {label:20s}: {count}")

    write_csv(numbers, OUTPUT_FILE)


if __name__ == "__main__":
    main()
