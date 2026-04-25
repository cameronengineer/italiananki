# Requirements: openai>=1.0.0

"""
Audit flash card rows using external LLM via OpenRouter.

Reads:   spreadsheets/*.csv              (columns: front_text, front_labels, back_highlight, back_text, audio)
Writes:  spreadsheets_audited/*.csv      (same columns + ai_issues, ai_fixes)
"""

import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

# --- Path setup ---
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

SPREADSHEETS_DIR = PROJECT_ROOT / "spreadsheets"
AUDITED_DIR = PROJECT_ROOT / "spreadsheets_audited"
API_KEY_FILE = PROJECT_ROOT / ".openrouter"

# --- Model configuration ---
MODEL = "google/gemini-flash-1.5"  # Fast and reliable model
MAX_WORKERS = 50  # Massive parallelism
MAX_RETRIES = 3
RETRY_DELAY = 2


# ---------------------------------------------------------------------------
# Load API key
# ---------------------------------------------------------------------------
def load_api_key() -> str:
    if not API_KEY_FILE.exists():
        raise FileNotFoundError(
            f"API key file not found: {API_KEY_FILE}\n"
            f"Create it with: echo 'your-key-here' > {API_KEY_FILE}"
        )
    key = API_KEY_FILE.read_text().strip()
    if not key:
        raise ValueError(f"API key file {API_KEY_FILE} is empty.")
    return key


def audit_flash_card(row: dict[str, str], api_key: str) -> dict[str, str]:
    """
    Send a flash card row to the AI for auditing via OpenRouter.
    
    Returns: dict with 'issues' and 'fixes' keys
    """
    front_text = row.get("front_text", "").strip()
    front_labels = row.get("front_labels", "").strip()
    back_highlight = row.get("back_highlight", "").strip()
    back_text = row.get("back_text", "").strip()
    audio = row.get("audio", "").strip()
    
    # Construct the prompt for the AI
    prompt = f"""You are auditing an Italian language flash card for Anki. Please review the card and identify any issues or suggest improvements.

Flash card details:
- Front text (English): {front_text}
- Front labels (metadata): {front_labels}
- Back highlight (Italian): {back_highlight}
- Back text (full context): {back_text}
- Audio text: {audio}

Important rules:
- Italian adjectives do NOT have articles (e.g., "primo/a/i/e" is correct for "first" as an adjective)
- Nouns typically include articles (e.g., "il primo" for "the first one" as a noun)

Please analyze:
1. Is the translation accurate?
2. Are the Italian words/phrases correct?
3. Is the metadata (front_labels) appropriate?
4. Are there any grammatical errors?
5. Is the audio text appropriate for pronunciation?
6. Is there any missing or confusing information?

Respond with TWO lines only:
Line 1: Brief description of issues found (or "none" if no issues)
Line 2: Specific fix suggestions (or "none" if no fixes needed)

Example responses:
none
none

OR

Translation uses wrong tense
Change "parlavo" to "parlo" for present tense

Keep each line concise (under 100 characters). Do not use line breaks within each line.
"""
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                }),
                timeout=30,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            
            # Parse two-line response
            lines = content.split("\n", 1)
            issues_line = lines[0].strip() if len(lines) > 0 else ""
            fixes_line = lines[1].strip() if len(lines) > 1 else ""
            
            # Normalize "none" to empty string
            if issues_line.lower() in ["none", "no issues", "no problems", ""]:
                issues_line = ""
            if fixes_line.lower() in ["none", "no fixes", ""]:
                fixes_line = ""
            
            # Remove any remaining line breaks to ensure single-line CSV output
            issues_line = issues_line.replace("\n", " ").replace("\r", " ")
            fixes_line = fixes_line.replace("\n", " ").replace("\r", " ")
            
            return {
                "issues": issues_line,
                "fixes": fixes_line
            }
        
        except (requests.HTTPError, requests.Timeout) as exc:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                return {
                    "issues": f"Error: {str(exc)}",
                    "fixes": ""
                }
        except Exception as exc:
            return {
                "issues": f"Error: {str(exc)}",
                "fixes": ""
            }
    
    return {
        "issues": "Error: Max retries exceeded",
        "fixes": ""
    }


def get_audited_rows(output_path: Path) -> set[str]:
    """
    Get the set of front_text values that have already been audited.
    Used for resume functionality.
    
    Returns: set of front_text strings that have been processed
    """
    if not output_path.exists():
        return set()
    
    audited = set()
    try:
        with open(output_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                front_text = row.get("front_text", "").strip()
                if front_text:
                    audited.add(front_text)
    except Exception as e:
        print(f"  Warning: Could not read existing output file: {e}")
        return set()
    
    return audited


def audit_spreadsheet(csv_path: Path, output_path: Path, api_key: str) -> tuple[int, int, int]:
    """
    Audit a single spreadsheet using massive parallelism and write results to output path.
    Supports resuming from previous runs.
    
    Returns: (total_rows, rows_with_issues, rows_skipped)
    """
    rows_with_issues = 0
    total_rows = 0
    rows_skipped = 0
    
    # Check if we're resuming
    audited_rows = get_audited_rows(output_path)
    is_resuming = len(audited_rows) > 0
    
    if is_resuming:
        print(f"  Resuming: {len(audited_rows)} rows already audited")
    
    # Read all rows from input CSV
    rows_to_process: list[tuple[int, dict[str, str]]] = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        output_fieldnames = list(fieldnames) + ["ai_issues", "ai_fixes"]
        
        for idx, row in enumerate(reader, start=1):
            total_rows += 1
            front_text = row.get("front_text", "").strip()
            
            # Skip if already audited
            if front_text in audited_rows:
                rows_skipped += 1
                continue
            
            rows_to_process.append((idx, row))
    
    if not rows_to_process:
        print(f"  All rows already audited")
        return total_rows, rows_with_issues, rows_skipped
    
    print(f"  Processing {len(rows_to_process)} rows with {MAX_WORKERS} parallel workers...")
    
    # Open output file in append mode if resuming, otherwise write mode
    file_mode = "a" if is_resuming else "w"
    write_header = not is_resuming
    
    with open(output_path, file_mode, encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=output_fieldnames)
        
        # Write header only if starting fresh
        if write_header:
            writer.writeheader()
            f_out.flush()
        
        # Process rows in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_row = {}
            for idx, row in rows_to_process:
                front_text = row.get("front_text", "").strip()
                
                # Handle empty rows immediately
                if not front_text:
                    output_row = {**row, "ai_issues": "", "ai_fixes": ""}
                    writer.writerow(output_row)
                    f_out.flush()
                    continue
                
                # Submit audit task
                future = executor.submit(audit_flash_card, row, api_key)
                future_to_row[future] = (idx, row)
            
            # Process results as they complete
            completed = 0
            for future in as_completed(future_to_row):
                idx, row = future_to_row[future]
                front_text = row.get("front_text", "").strip()
                completed += 1
                
                try:
                    audit_result = future.result()
                    
                    # Track rows with issues
                    if audit_result["issues"]:
                        rows_with_issues += 1
                    
                    # Write row immediately
                    output_row = {
                        **row,
                        "ai_issues": audit_result["issues"],
                        "ai_fixes": audit_result["fixes"]
                    }
                    writer.writerow(output_row)
                    f_out.flush()
                    
                    # Progress update
                    status = "✗" if audit_result["issues"] else "✓"
                    print(f"    [{completed}/{len(future_to_row)}] {status} {front_text[:50]}")
                    
                except Exception as e:
                    print(f"    [ERROR] Row {idx}: {str(e)}")
                    output_row = {
                        **row,
                        "ai_issues": f"Exception: {str(e)}",
                        "ai_fixes": ""
                    }
                    writer.writerow(output_row)
                    f_out.flush()
    
    return total_rows, rows_with_issues, rows_skipped


def main() -> None:
    # Load API key
    api_key = load_api_key()
    
    # Create output directory
    AUDITED_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Starting flash card audit with {MAX_WORKERS} parallel workers...")
    print(f"Model: {MODEL}\n")
    
    total_cards = 0
    total_issues = 0
    total_skipped = 0
    processed_files = 0
    
    start_time = time.time()
    
    # Process each CSV in spreadsheets directory
    for csv_path in sorted(SPREADSHEETS_DIR.glob("*.csv")):
        stem = csv_path.stem
        output_path = AUDITED_DIR / f"{stem}.csv"
        
        print(f"Processing: {csv_path.name}")
        
        file_start = time.time()
        rows, issues, skipped = audit_spreadsheet(csv_path, output_path, api_key)
        file_elapsed = time.time() - file_start
        
        total_cards += rows
        total_issues += issues
        total_skipped += skipped
        processed_files += 1
        
        audited_count = rows - skipped
        print(f"  ✓ Completed in {file_elapsed:.1f}s: {audited_count} cards audited, {issues} with issues, {skipped} skipped")
        print(f"  → {output_path}\n")
    
    elapsed = time.time() - start_time
    
    print(
        f"Audit complete in {elapsed:.1f}s."
        f"\n  Files processed          : {processed_files}"
        f"\n  Total cards audited      : {total_cards - total_skipped}"
        f"\n  Total cards skipped      : {total_skipped}"
        f"\n  Cards with issues        : {total_issues}"
        f"\n  Output directory         : {AUDITED_DIR}"
    )


if __name__ == "__main__":
    main()
