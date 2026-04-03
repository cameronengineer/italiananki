"""
Attempt to match Italian words to their English translations via suffix/prefix/
replacement rules and compute a Jaro similarity score after transformation.

Reads:  sources/8_transferable/2_remove_duplicates.csv
Writes: sources/8_transferable/3_group_words.csv

Adds three columns to each row:
  Initial_Jaro    — raw Jaro score between Italian and English (no transforms)
  Rule_Chain      — space-separated list of rules that improved the score
  Max_Jaro_Score  — Jaro score after the best rule chain is applied

Usage (from project root, with .venv activated):
    python sources/8_transferable/scripts/3_group_words.py
"""

import csv
import pathlib

from Levenshtein import jaro

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent  # sources/8_transferable/

INPUT_CSV = SOURCE_DIR / "2_remove_duplicates.csv"
OUTPUT_CSV = SOURCE_DIR / "3_group_words.csv"

# ---------------------------------------------------------------------------
# Transformation rules: (id, type, target, from_str, to_str)
# type   : "suffix" | "prefix" | "replace"
# target : "it" (transform Italian) | "en" (transform English)
# ---------------------------------------------------------------------------
TRANSFORMATIONS = [
    # Suffixes (IT -> EN)
    ("suffix-zione-tion",    "suffix",  "it", "zione",    "tion"),
    ("suffix-sione-sion",    "suffix",  "it", "sione",    "sion"),
    ("suffix-gione-gion",    "suffix",  "it", "gione",    "gion"),
    ("suffix-anza-ance",     "suffix",  "it", "anza",     "ance"),
    ("suffix-enza-ence",     "suffix",  "it", "enza",     "ence"),
    ("suffix-mento-ment",    "suffix",  "it", "mento",    "ment"),
    ("suffix-ismo-ism",      "suffix",  "it", "ismo",     "ism"),
    ("suffix-ista-ist",      "suffix",  "it", "ista",     "ist"),
    ("suffix-oso-ous",       "suffix",  "it", "oso",      "ous"),
    ("suffix-ico-ic",        "suffix",  "it", "ico",      "ic"),
    ("suffix-ivo-ive",       "suffix",  "it", "ivo",      "ive"),
    ("suffix-iva-ive",       "suffix",  "it", "iva",      "ive"),
    ("suffix-ale-al",        "suffix",  "it", "ale",      "al"),
    ("suffix-bile-ble",      "suffix",  "it", "bile",     "ble"),
    ("suffix-ario-ary",      "suffix",  "it", "ario",     "ary"),
    ("suffix-orio-ory",      "suffix",  "it", "orio",     "ory"),
    ("suffix-logia-logy",    "suffix",  "it", "logia",    "logy"),
    ("suffix-grafia-graphy", "suffix",  "it", "grafia",   "graphy"),
    ("suffix-metro-meter",   "suffix",  "it", "metro",    "meter"),
    ("suffix-fobia-phobia",  "suffix",  "it", "fobia",    "phobia"),
    ("suffix-filo-phile",    "suffix",  "it", "filo",     "phile"),
    ("suffix-crazia-cracy",  "suffix",  "it", "crazia",   "cracy"),
    ("suffix-tudine-tude",   "suffix",  "it", "tudine",   "tude"),
    ("suffix-ura-ure",       "suffix",  "it", "ura",      "ure"),
    ("suffix-ino-ine",       "suffix",  "it", "ino",      "ine"),
    ("suffix-ica-ics",       "suffix",  "it", "ica",      "ics"),
    ("suffix-esi-esis",      "suffix",  "it", "esi",      "esis"),
    ("suffix-aneo-aneous",   "suffix",  "it", "aneo",     "aneous"),
    ("suffix-are-ate",       "suffix",  "it", "are",      "ate"),
    ("suffix-izzare-ize",    "suffix",  "it", "izzare",   "ize"),
    ("suffix-ificare-ify",   "suffix",  "it", "ificare",  "ify"),
    ("suffix-icare-icate",   "suffix",  "it", "icare",    "icate"),
    ("suffix-inare-inate",   "suffix",  "it", "inare",    "inate"),
    ("suffix-durre-duce",    "suffix",  "it", "durre",    "duce"),
    ("suffix-trarre-tract",  "suffix",  "it", "trarre",   "tract"),
    ("suffix-mettere-mit",   "suffix",  "it", "mettere",  "mit"),
    ("suffix-porre-pose",    "suffix",  "it", "porre",    "pose"),
    ("suffix-cludere-clude", "suffix",  "it", "cludere",  "clude"),
    ("suffix-scrivere-scribe","suffix", "it", "scrivere", "scribe"),
    ("suffix-tenere-tain",   "suffix",  "it", "tenere",   "tain"),
    ("suffix-cepire-ceive",  "suffix",  "it", "cepire",   "ceive"),
    ("suffix-cevere-ceive",  "suffix",  "it", "cevere",   "ceive"),
    ("suffix-ferire-fer",    "suffix",  "it", "ferire",   "fer"),
    ("suffix-quisire-quire", "suffix",  "it", "quisire",  "quire"),
    ("suffix-cedere-cede",   "suffix",  "it", "cedere",   "cede"),
    ("suffix-venire-vene",   "suffix",  "it", "venire",   "vene"),
    ("suffix-solvere-solve", "suffix",  "it", "solvere",  "solve"),
    ("suffix-rompere-rupt",  "suffix",  "it", "rompere",  "rupt"),
    ("suffix-primere-press", "suffix",  "it", "primere",  "press"),
    ("suffix-tendere-tend",  "suffix",  "it", "tendere",  "tend"),
    ("suffix-sistere-sist",  "suffix",  "it", "sistere",  "sist"),
    ("suffix-gredire-gress", "suffix",  "it", "gredire",  "gress"),
    ("suffix-vertire-vert",  "suffix",  "it", "vertire",  "vert"),
    ("suffix-formare-form",  "suffix",  "it", "formare",  "form"),
    ("suffix-portare-port",  "suffix",  "it", "portare",  "port"),
    ("suffix-struire-struct","suffix",  "it", "struire",  "struct"),
    ("suffix-ità-ity",       "suffix",  "it", "ità",      "ity"),
    ("suffix-tà-ty",         "suffix",  "it", "tà",       "ty"),
    ("suffix-ia-y",          "suffix",  "it", "ia",       "y"),
    ("suffix-o-",            "suffix",  "it", "o",        ""),
    ("suffix-a-",            "suffix",  "it", "a",        ""),
    ("suffix-e-",            "suffix",  "it", "e",        ""),
    ("suffix-re-er",         "suffix",  "it", "re",       "er"),
    ("suffix-er-e",          "suffix",  "it", "e",        "er"),
    ("suffix-al-a",          "suffix",  "it", "a",        "al"),
    ("suffix-on-o",          "suffix",  "it", "o",        "on"),
    ("suffix-is-i",          "suffix",  "it", "i",        "is"),
    ("suffix-able-ale",      "suffix",  "it", "ale",      "able"),
    ("suffix-ed-e",          "suffix",  "it", "e",        "ed"),
    ("suffix-es-e",          "suffix",  "it", "e",        "es"),
    ("suffix-ey-y",          "suffix",  "it", "y",        "ey"),
    ("suffix-none-to",       "suffix",  "it", "to",       ""),
    ("suffix-tion-to",       "suffix",  "it", "to",       "tion"),
    ("suffix-imento-ment",   "suffix",  "it", "imento",   "ment"),
    ("suffix-ano-an",        "suffix",  "it", "ano",      "an"),
    ("suffix-ssione-ssion",  "suffix",  "it", "ssione",   "ssion"),
    ("suffix-ione-ion",      "suffix",  "it", "ione",     "ion"),
    ("suffix-e-ey",          "suffix",  "it", "e",        "ey"),
    ("suffix-abile-ible",    "suffix",  "it", "abile",    "ible"),
    ("suffix-o-ous",         "suffix",  "it", "o",        "ous"),
    ("suffix-ato-ate",       "suffix",  "it", "ato",      "ate"),
    ("suffix-are-e",         "suffix",  "it", "are",      "e"),
    ("suffix-are-ary",       "suffix",  "it", "are",      "ary"),
    ("suffix-icare-ice",     "suffix",  "it", "icare",    "ice"),
    ("suffix-ere-e",         "suffix",  "it", "ere",      "e"),
    ("suffix-a-e",           "suffix",  "it", "a",        "e"),
    ("suffix-o-e",           "suffix",  "it", "o",        "e"),
    ("suffix-o-ion",         "suffix",  "it", "o",        "ion"),
    # Prefixes (IT -> EN)
    ("prefix-h-none",        "prefix",  "it", "",         "h"),
    # Replacements (global)
    ("replace-c-cc",         "replace", "it", "c",        "cc"),
    ("replace-cc-c",         "replace", "it", "cc",       "c"),
    ("replace-z-t",          "replace", "it", "z",        "t"),
    ("replace-zz-z",         "replace", "it", "zz",       "z"),
    ("replace-f-ph",         "replace", "it", "f",        "ph"),
    ("replace-tt-ct",        "replace", "it", "tt",       "ct"),
    ("replace-zione-ction",  "replace", "it", "zione",    "ction"),
    ("replace-dm-m",         "replace", "it", "m",        "dm"),
    ("replace-g-gg",         "replace", "it", "g",        "gg"),
    ("replace-o-ov",         "replace", "it", "ov",       "o"),
    ("replace-ch-c",         "replace", "it", "c",        "ch"),
    ("replace-ff-f",         "replace", "it", "f",        "ff"),
    ("replace-m-mm",         "replace", "it", "mm",       "m"),
    ("replace-ci-cy",        "replace", "it", "ci",       "cy"),
    ("replace-ll-l",         "replace", "it", "ll",       "l"),
    ("replace-bb-b",         "replace", "it", "bb",       "b"),
    ("replace-tras-trans",   "replace", "it", "tras",     "trans"),
    ("replace-t-th",         "replace", "it", "t",        "th"),
    ("replace-e-ea",         "replace", "it", "e",        "ea"),
    ("replace-a-ea",         "replace", "it", "a",        "ea"),
    ("replace-l-li",         "replace", "it", "l",        "li"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def normalize(word: str) -> str:
    if not word:
        return ""
    w = word.lower().strip()
    if w.startswith("to "):
        w = w[3:].strip()
    return w.replace("-", "").replace(" ", "")


def apply_transformation(word: str, ttype: str, from_str: str, to_str: str) -> str:
    if ttype == "suffix":
        if word.endswith(from_str):
            return word[: -len(from_str)] + to_str if from_str else word + to_str
    elif ttype == "prefix":
        if word.startswith(from_str):
            return to_str + word[len(from_str):]
    elif ttype == "replace":
        return word.replace(from_str, to_str)
    return word


def get_best_rule_chain(
    it_word: str, en_word: str
) -> tuple[list[str], float, float]:
    """
    Greedily apply transformations that improve the Jaro score.
    Returns (rule_chain, final_score, initial_score).
    If a perfect match (>=0.999) is not reached, returns ([], initial_score, initial_score).
    """
    it = normalize(it_word)
    en = normalize(en_word)

    if not it or not en:
        return [], 0.0, 0.0

    initial_score = jaro(it, en)

    def recurse(curr_it: str, curr_en: str, chain: list[str]) -> tuple[list[str], float]:
        current_score = jaro(curr_it, curr_en)
        best_score = current_score
        best_rule = None
        best_it, best_en = curr_it, curr_en

        for rid, rtype, target, from_str, to_str in TRANSFORMATIONS:
            temp_it = curr_it
            temp_en = curr_en
            if target == "it":
                temp_it = apply_transformation(curr_it, rtype, from_str, to_str)
            else:
                temp_en = apply_transformation(curr_en, rtype, from_str, to_str)

            if temp_it == curr_it and temp_en == curr_en:
                continue

            score = jaro(temp_it, temp_en)
            if score > best_score:
                best_score = score
                best_rule = rid
                best_it, best_en = temp_it, temp_en

        if best_rule:
            return recurse(best_it, best_en, chain + [best_rule])
        return chain, current_score

    final_chain, final_score = recurse(it, en, [])

    if final_score < 0.999:
        return [], initial_score, initial_score

    return final_chain, final_score, initial_score


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not INPUT_CSV.exists():
        print(f"Error: {INPUT_CSV} not found.")
        return

    print("Processing words …")
    results = []
    fieldnames: list[str] = []
    matched = 0

    with open(INPUT_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or []) + [
            "Initial_Jaro", "Rule_Chain", "Max_Jaro_Score"
        ]

        for row in reader:
            en = row.get("English_Translation", "")
            it = row.get("Word", "")
            chain, max_score, initial_score = get_best_rule_chain(it, en)

            row["Initial_Jaro"] = initial_score
            row["Rule_Chain"] = " + ".join(chain)
            row["Max_Jaro_Score"] = max_score

            if chain:
                matched += 1
            results.append(row)

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Processed {len(results)} words.")
    print(f"Matched   {matched} words (score improved to >=0.999 via rules).")
    print(f"Written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
