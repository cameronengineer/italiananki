#!/usr/bin/env python3
"""
Randomize the order of flashcards in the translated CSV files.

This prevents the vocabulary from being learned in alphabetical order,
which creates unwanted patterns and makes the deck less effective.

Reads:  sources/11_cils/a1_vocabulary_translated.csv
        sources/11_cils/a2_vocabulary_translated.csv
        sources/11_cils/b1_vocabulary_translated.csv
        sources/11_cils/b2_vocabulary_translated.csv

Writes: Overwrites the same files with rows in random order

Usage (from project root, with .venv activated):
    python sources/11_cils/2.5_randomize.py
"""

import csv
import random
import pathlib
from typing import List, Dict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "sources" / "11_cils"

# Levels to process
LEVELS = ['a1', 'a2', 'b1', 'b2']

# Set random seed for reproducibility (remove this line for true randomness each run)
random.seed(42)


def randomize_csv(csv_path: pathlib.Path) -> None:
    """
    Read a CSV file, randomize the row order, and write it back.
    
    Args:
        csv_path: Path to the CSV file to randomize
    """
    if not csv_path.exists():
        print(f"  ⚠️  File not found: {csv_path}")
        return
    
    # Read all rows
    rows: List[Dict[str, str]] = []
    fieldnames: List[str] = []
    
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    
    if not rows:
        print(f"  ⚠️  No data rows found in {csv_path}")
        return
    
    original_count = len(rows)
    
    # Randomize the order
    random.shuffle(rows)
    
    # Write back to the same file
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"  ✓ Randomized {original_count} rows → {csv_path.name}")


def main() -> None:
    """Main function."""
    print("Randomizing flashcard order for all CEFR levels...\n")
    
    total_processed = 0
    
    for level in LEVELS:
        print(f"{'='*60}")
        print(f"Processing level {level.upper()}")
        print(f"{'='*60}")
        
        csv_path = SOURCE_DIR / f"{level}_vocabulary_translated.csv"
        randomize_csv(csv_path)
        
        if csv_path.exists():
            total_processed += 1
        
        print()
    
    print(f"{'='*60}")
    print(f"Randomization complete! Processed {total_processed} level(s).")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
