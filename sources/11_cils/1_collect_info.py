#!/usr/bin/env python3
"""
Script to collect Italian vocabulary from Università per Stranieri di Perugia.
Extracts word lists for CEFR levels A1, A2, B1, B2 and saves them to CSV files.
"""

import re
import csv
import os
from pathlib import Path
from typing import Dict, List, Tuple
import requests
from bs4 import BeautifulSoup


# URLs for each level
URLS = {
    'A1': 'https://www.unistrapg.it/profilo_lingua_italiana/site/liste_lessicali_a1.html',
    'A2': 'https://www.unistrapg.it/profilo_lingua_italiana/site/liste_lessicali_a2.html',
    'B1': 'https://www.unistrapg.it/profilo_lingua_italiana/site/liste_lessicali_b1.html',
    'B2': 'https://www.unistrapg.it/profilo_lingua_italiana/site/liste_lessicali_b2.html',
}

# Legend mapping from abbreviation to full form
# Note: Gender information removed from sostantivo to keep flashcard labels simple
LEGEND = {
    'v.t.': 'verbo transitivo',
    'v.int.': 'verbo intransitivo',
    'v. rifl.': 'verbo riflessivo',
    'v.rifl.': 'verbo riflessivo',
    'v.t. pron.': 'verbo transitivo pronominale',
    'v.int. pron.': 'verbo intransitivo pronominale',
    'v. int. pron.': 'verbo intransitivo pronominale',
    's.m.': 'sostantivo',
    's.f.': 'sostantivo',
    'prep.': 'preposizione',
    'agg.': 'aggettivo',
    'avv.': 'avverbio',
    'pron.': 'pronome',
    'part. pron.': 'particella pronominale',
    'art.': 'articolo',
    'cong.': 'congiunzione',
    'inter.': 'interiezione',
    'loc.': 'locuzione',
    'locuz.': 'locuzione',
    's.m. pl.': 'sostantivo plurale',
    's.m - s.f.': 'sostantivo',
    's.m.- s.f.': 'sostantivo',
    's.m. – s.f.': 'sostantivo',
    's.m. - s.f.': 'sostantivo',
    'v. int.': 'verbo intransitivo',
    'v.intr.': 'verbo intransitivo',
    'v.int.pron.': 'verbo intransitivo pronominale',
    'v.t. – v.rifl. – v.t. pron.': 'verbo transitivo - verbo riflessivo - verbo transitivo pronominale',
    'v.t - v.int.': 'verbo transitivo - verbo intransitivo',
    'v.t. - v.int.': 'verbo transitivo - verbo intransitivo',
    'v.t - v. int.': 'verbo transitivo - verbo intransitivo',
    'v.t. - v. int.': 'verbo transitivo - verbo intransitivo',
    'pron. – agg.': 'pronome - aggettivo',
    'pron. - agg.': 'pronome - aggettivo',
    'agg. - avv.': 'aggettivo - avverbio',
    'agg. - inter.': 'aggettivo - interiezione',
    's.m.– s.f.': 'sostantivo',
    's.m - s.f.': 'sostantivo',
    'agg. - s.m.': 'aggettivo - sostantivo',
    'agg. - s.m. - s.f.': 'aggettivo - sostantivo',
    'agg.- s.m. - s.f.': 'aggettivo - sostantivo',
    'v.t.pron.': 'verbo transitivo pronominale',
    'v.t. - v.rifl.': 'verbo transitivo - verbo riflessivo',
    'v.t. - v.int.pron.': 'verbo transitivo - verbo intransitivo pronominale',
    'v.t. – v.int.pron.': 'verbo transitivo - verbo intransitivo pronominale',
    'v.int.': 'verbo intransitivo',
    'v.t - v.int.pron.': 'verbo transitivo - verbo intransitivo pronominale',
    'v. rifl. - v.t. pron.': 'verbo riflessivo - verbo transitivo pronominale',
    'avv. - prep.': 'avverbio - preposizione',
    's.m. - s.f.': 'sostantivo',
    'inter. - s.m.': 'interiezione - sostantivo',
    'pron.- cong.': 'pronome - congiunzione',
    'pron. - cong.': 'pronome - congiunzione',
    'part. pron. – pron.': 'particella pronominale - pronome',
    's.m.- s.f.': 'sostantivo',
    's.f. - avv.': 'sostantivo - avverbio',
    'pron.-  cong.': 'pronome - congiunzione',
    'v.t. - v. int. pron.': 'verbo transitivo - verbo intransitivo pronominale',
    'v.t.– v.rifl. – v.t. pron.': 'verbo transitivo - verbo riflessivo - verbo transitivo pronominale',
    's.m.': 'sostantivo',
    'agg. - s.f.': 'aggettivo - sostantivo',
    'v.t. - v.int.': 'verbo transitivo - verbo intransitivo',
    'v.t - v. int.': 'verbo transitivo - verbo intransitivo',
    'v.t.': 'verbo transitivo',
    'v.t': 'verbo transitivo',
    'v. int. pron.': 'verbo intransitivo pronominale',
    's.m. - s.f': 'sostantivo',
    'v.t. - v.t. pron.': 'verbo transitivo - verbo transitivo pronominale',
    'v.t. – v.t. pron.': 'verbo transitivo - verbo transitivo pronominale',
    'v.int. - v.t.': 'verbo intransitivo - verbo transitivo',
    'v.int - v.t.': 'verbo intransitivo - verbo transitivo',
    's.m. - s.f.': 'sostantivo',
    'v.  int. pron.': 'verbo intransitivo pronominale',
    'v. t.': 'verbo transitivo',
    's.m.': 'sostantivo',
    'agg.- s.m. - s.f.': 'aggettivo - sostantivo',
    'v.int. - v.int.pron.': 'verbo intransitivo - verbo intransitivo pronominale',
    'v.t - v. int. pron.': 'verbo transitivo - verbo intransitivo pronominale',
    's.m. - s.f': 'sostantivo',
    's.m .': 'sostantivo',
    's.m': 'sostantivo',
    'v.int. - v.int. pron.': 'verbo intransitivo - verbo intransitivo pronominale',
    's.m. - agg.': 'sostantivo - aggettivo',
    'v. rifl. - v.int.pron.': 'verbo riflessivo - verbo intransitivo pronominale',
    'v.t. - v.int. pron.': 'verbo transitivo - verbo intransitivo pronominale',
    's.m - s.f.': 'sostantivo',
    'v.t.- v.int.pron.': 'verbo transitivo - verbo intransitivo pronominale',
    's.f. - s.m.': 'sostantivo',
    'v.t. - v.rifl. - v.int. pron.': 'verbo transitivo - verbo riflessivo - verbo intransitivo pronominale',
    'v.int. - v.rifl.': 'verbo intransitivo - verbo riflessivo',
    'v. int - v.int. pron.': 'verbo intransitivo - verbo intransitivo pronominale',
    's.m. - s.f )': 'sostantivo',
    's.m. - s.f.': 'sostantivo',
    'v. t. - v.int.': 'verbo transitivo - verbo intransitivo',
    'v.t. pron. - v.int. pron.': 'verbo transitivo pronominale - verbo intransitivo pronominale',
    's.m. -agg.': 'sostantivo - aggettivo',
    's.m .  s.f.': 'sostantivo',
    'agg. - s.m. -  s.f.': 'aggettivo - sostantivo',
    's.f.-  s.m.': 'sostantivo',
    'agg. -  s.m. - s.f.': 'aggettivo - sostantivo',
    'part. pron. - avv.': 'particella pronominale - avverbio',
    's.m. –  s.f.': 'sostantivo',
    's.m. – agg.': 'sostantivo - aggettivo',
    'v.t.  - v.rifl.': 'verbo transitivo - verbo riflessivo',
    'v.int. - v.t.pron.': 'verbo intransitivo - verbo transitivo pronominale',
    'v.rifl. - v.int.pron.': 'verbo riflessivo - verbo intransitivo pronominale',
    's.m. – s.f': 'sostantivo',
    's.f. –  s.m.': 'sostantivo',
    'v.t. - v.int. - v. rifl.': 'verbo transitivo - verbo intransitivo - verbo riflessivo',
    'v.int. - v. int. pron.': 'verbo intransitivo - verbo intransitivo pronominale',
    'v.t. – v.int.': 'verbo transitivo - verbo intransitivo',
    's.m. - s.f)': 'sostantivo',
    's.m. -  s.f.': 'sostantivo',
    's.m. -s.f.': 'sostantivo',
    's.m. – s.f.': 'sostantivo',
    'agg -  s.m. - s.f.': 'aggettivo - sostantivo',
    's.m .  - s.f.': 'sostantivo',
    'agg. -  s.m.': 'aggettivo - sostantivo',
    's.m.  - s.f.': 'sostantivo',
    'v.int - v.int.pron.': 'verbo intransitivo - verbo intransitivo pronominale',
    's.m. - agg. - avv.': 'sostantivo - aggettivo - avverbio',
    'agg. -  s.m. -  s.f.': 'aggettivo - sostantivo',
    'agg. - s.f.': 'aggettivo - sostantivo',
    'v.t - v.int. - v.rifl.': 'verbo transitivo - verbo intransitivo - verbo riflessivo',
    'v. int pron.': 'verbo intransitivo pronominale',
    'v.t. - v.int.pron.': 'verbo transitivo - verbo intransitivo pronominale',
    's.m. - s.f - agg.': 'sostantivo - aggettivo',
    's.m.- agg.': 'sostantivo - aggettivo',
    'v.t. – v.int.pron.': 'verbo transitivo - verbo intransitivo pronominale',
    'v.int. - v.rifl. - v.int.pron.': 'verbo intransitivo - verbo riflessivo - verbo intransitivo pronominale',
    's.m. – agg.': 'sostantivo - aggettivo',
    'v.int. – v.int.pron.': 'verbo intransitivo - verbo intransitivo pronominale',
    'v.int. – v.int. pron.': 'verbo intransitivo - verbo intransitivo pronominale',
    'v.t. - v.t.pron.': 'verbo transitivo - verbo transitivo pronominale',
    'v.t.- v.int.': 'verbo transitivo - verbo intransitivo',
    'v.int. - v.int. - v.rifl.': 'verbo intransitivo - verbo intransitivo - verbo riflessivo',
    'v.t. -  v.t.pron.': 'verbo transitivo - verbo transitivo pronominale',
    'v. int. - v. rifl.': 'verbo intransitivo - verbo riflessivo',
    's.m. - s.f - agg.': 'sostantivo - aggettivo',
    'agg. - s.m. - s.f': 'aggettivo - sostantivo',
    's.m. - s.f.': 'sostantivo',
    'v.rifl – v.int. pron.': 'verbo riflessivo - verbo intransitivo pronominale',
    'avv. - agg.': 'avverbio - aggettivo',
    'avv.- agg.': 'avverbio - aggettivo',
    'v. int – v.int. pron.': 'verbo intransitivo - verbo intransitivo pronominale',
    'v.t. – v.rifl.': 'verbo transitivo - verbo riflessivo',
    's.m. - s.f.': 'sostantivo',
    'pron. - agg.': 'pronome - aggettivo',
    'v.int. - v.t. - v.rifl.': 'verbo intransitivo - verbo transitivo - verbo riflessivo',
    'agg. – s.m.': 'aggettivo - sostantivo',
    'v.t. – v. rifl.': 'verbo transitivo - verbo riflessivo',
    's.m. – s.f.': 'sostantivo',
    'v.t. – v.int. pron.': 'verbo transitivo - verbo intransitivo pronominale',
    'v.int. pron. – v.rifl.': 'verbo intransitivo pronominale - verbo riflessivo',
    's.m .': 'sostantivo',
    'v.t. - v. rifl. - v.int.pron.': 'verbo transitivo - verbo riflessivo - verbo intransitivo pronominale',
    'v.int. – v.int.pron.': 'verbo intransitivo - verbo intransitivo pronominale',
    's.m.- s.f.': 'sostantivo',
    's.f - s.m.': 'sostantivo',
    's.f. - s.m': 'sostantivo',
    's.m.  -s.f.': 'sostantivo',
    's.m. s.f.': 'sostantivo',
}


def fetch_page(url: str) -> str:
    """Fetch HTML content from URL."""
    print(f"Fetching {url}...")
    response = requests.get(url)
    response.raise_for_status()
    response.encoding = 'utf-8'
    return response.text


def extract_words(html: str) -> List[Tuple[str, str]]:
    """
    Extract word entries from HTML.
    Returns list of tuples: (italian_word, function)
    """
    soup = BeautifulSoup(html, 'html.parser')
    entries = []
    
    # Find all numbered entries with links
    # Pattern: number followed by tab character, then link with word, then text in parentheses
    pattern = re.compile(r'^(\d+)\.\s+')
    
    # Find all <br> tags - entries are separated by <br>
    text_content = soup.get_text()
    
    # Different approach: find all text that matches the pattern
    # number. <word> (function)
    lines = text_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Match pattern like: "11.	aiuto (inter.)"
        match = re.match(r'^\d+\.\s+(.+?)\s+\(([^)]+)\)', line)
        if match:
            word = match.group(1).strip()
            function_abbr = match.group(2).strip()
            
            # Look up the full function name from legend
            function_full = LEGEND.get(function_abbr, function_abbr)
            
            entries.append((word, function_full))
    
    return entries


def save_to_csv(entries: List[Tuple[str, str]], filename: str):
    """Save entries to CSV file."""
    print(f"Saving {len(entries)} entries to {filename}...")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(['italian', 'function'])
        # Write entries
        writer.writerows(entries)
    
    print(f"Saved {filename}")


def main():
    """Main function."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    
    for level, url in URLS.items():
        print(f"\n{'='*60}")
        print(f"Processing level {level}")
        print(f"{'='*60}")
        
        # Fetch and parse
        html = fetch_page(url)
        entries = extract_words(html)
        
        if not entries:
            print(f"WARNING: No entries found for level {level}!")
            continue
        
        # Save to CSV in the same directory as the script
        filename = script_dir / f'{level.lower()}_vocabulary.csv'
        save_to_csv(entries, str(filename))
        
        print(f"Completed level {level}: {len(entries)} words")
    
    print(f"\n{'='*60}")
    print("All levels processed successfully!")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
