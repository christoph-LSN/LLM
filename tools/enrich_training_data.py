
# coding: utf-8
"""
Enrich indicator training data:
- erzeugt deterministische 'keywords' und 'short_definition'
- liest robuste Eingabeformate (Liste, Richtext-Wrapper, Einzelobjekt)
- schreibt nur bei echter Inhaltsänderung (optional erzwingbar)
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

# Default-Pfade relativ zum Repo-Root (tools/..)
ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "training_data.json"
OUTPUT = ROOT / "assets/data/indicators.json"

# Erweiterbare Stopwortbasis (Domänenstopwörter bei Bedarf ergänzen)
STOPWORDS = {
    "und", "oder", "der", "die", "das", "mit", "von", "im", "in", "auf", "zu", "für",
    "eine", "einer", "eines", "ist", "sind", "werden", "wird", "als", "auch",
    "am", "an", "bei", "beim", "vom", "zum", "zur", "dass", "nicht", "kein", "ohne",
    "nach", "über", "unter", "zwischen"
}

# Wörter ab 4 Zeichen, deutsch inkl. Umlaute/ß
WORD_RE = re.compile(r"[a-zäöüß]{4,}", re.IGNORECASE)

# Einfache HTML-Bereinigung für additional_info
TAG_RE = re.compile(r"<[^>]+>")


def clean_html(s: str) -> str:
    """Entfernt HTML-Tags und häufige Entities, trimmt Whitespace."""
    if not s:
        return ""
    txt = TAG_RE.sub(" ", s)
    txt = (
        txt.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    return " ".join(txt.split())


def normalize_text(text: str) -> str:
    """Normiert Bindestriche/Trennzeichen zu Leerzeichen, lowercased."""
    if not text:
        return ""
    text = (
        text.replace("–", " ")
        .replace("—", " ")
        .replace("‑", " ")
        .replace("-", " ")
        .replace("/", " ")
    )
    return text.lower()


def tokenize(text: str) -> List[str]:
    """Extrahiert Wörter (>=4 Zeichen), filtert Stopwörter."""
    text = normalize_text(text)
    words = WORD_RE.findall(text)
    return [w for w in words if w not in STOPWORDS]


def extract_keywords(entry: Dict[str, Any], n: int = 12) -> List[str]:
    """
    Keywords aus name/definition/methodology (+cleaned additional_info).
    Deterministische Sortierung: Häufigkeit absteigend, dann alphabetisch.
    """
    parts = [
        str(entry.get("name", "") or ""),
        str(entry.get("definition", "") or ""),
        str(entry.get("methodology", "") or ""),
        clean_html(str(entry.get("additional_info", "") or "")),
    ]
    text = " ".join(parts)
    tokens = tokenize(text)
    if not tokens:
        return []
    counts = Counter(tokens)
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in items[:n]]


def short_text(text: str, max_len: int = 280) -> str:
    """Kürzt auf Wortgrenze; Ellipse nur, wenn tatsächlich gekürzt wurde."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text

    slice_ = text[:max_len]
    if " " in slice_:
        slice_ = slice_.rsplit(" ", 1)[0]
    slice_ = slice_.rstrip(" ,;:-")
    return slice_ + "…"


def enrich(entry: Dict[str, Any], n_keywords: int = 12, short_len: int = 280) -> Dict[str, Any]:
    """Erzeugt 'keywords' und 'short_definition' – Original ansonsten unverändert."""
    entry = dict(entry)
    entry["keywords"] = extract_keywords(entry, n=n_keywords)
    entry["short_definition"] = short_text(str(entry.get("definition", "") or ""), max_len=short_len)
    return entry


def load_indicators(input_path: Path) -> List[Dict[str, Any]]:
    """
    Liest die Indikatoren robust ein und gibt eine Liste[dict] zurück.
    Unterstützte Formate:
      A) Root = list[dict]
      B) Richtext-Wrapper -> irgendein Key endet auf ':content' und hat 'value.text' (JSON-String)
      C) Einzelobjekt {name, definition, methodology, ...} -> wird zu [obj]
    """
    raw = json.loads(input_path.read_text(encoding="utf-8"))

    # A) Bereits eine Liste
    if isinstance(raw, list):
        print(f"[INFO] Input form: list with {len(raw)} entries")
        return raw

    # B) Richtext-Wrapper
    if isinstance(raw, dict):
        for k, v in raw.items():
            if (
                isinstance(v, dict)
                and "value" in v
                and isinstance(v["value"], dict)
                and "text" in v["value"]
            ):
                txt = v["value"]["text"]
                try:
                    inner = json.loads(txt)
                    if isinstance(inner, list):
                        print(f"[INFO] Input form: richtext wrapper -> parsed list with {len(inner)} entries")
                        return inner
                except Exception as e:
                    print(f"[WARN] Could not parse inner text as JSON: {e}", file=sys.stderr)

        # C) Einzelobjekt
        if {"name", "definition", "methodology"}.issubset(set(raw.keys())):
            print("[INFO] Input form: single indicator object -> wrapped as list[1]")
            return [raw]

    raise ValueError("Unbekanntes Eingabeformat: erwarte Liste, Richtext-Wrapper (value.text) oder Einzelobjekt.")


def dump_json_pretty(obj: Any) -> str:
    """Stabil formatiertes JSON (UTF-8, indent=2)."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def write_if_changed(out_path: Path, content: str) -> bool:
    """
    Schreibt 'content' nach 'out_path', aber nur wenn sich der Inhalt geändert hat.
    Rückgabe: True = geschrieben, False = unverändert.
    """
    try:
        old = out_path.read_text(encoding="utf-8")
        old_sha = hashlib.sha256(old.encode("utf-8")).hexdigest()
        new_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if old_sha == new_sha:
            print("[INFO] Output unchanged – skipping write.")
            return False
    except FileNotFoundError:
        pass

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Enrich indicator training data with keywords and short definitions."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT,
        help="Pfad zur Input-JSON (Liste / Richtext-Wrapper / Einzelobjekt)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help="Zielpfad für angereicherte JSON",
    )
    parser.add_argument(
        "--keywords",
        type=int,
        default=12,
        help="Anzahl der Keywords pro Eintrag",
    )
    parser.add_argument(
        "--short-len",
        type=int,
        default=280,
        help="Maximale Länge der Kurzdefinition",
    )
    parser.add_argument(
        "--always-write",
        action="store_true",
        help="Datei immer schreiben (auch wenn Inhalt unverändert ist).",
    )
    args = parser.parse_args()

    # Pfade loggen
    try:
        print(f"[INFO] Input : {args.input.resolve()}")
        print(f"[INFO] Output: {args.output.resolve()}")
    except Exception:
        pass

    # Einlesen
    try:
        data = load_indicators(args.input)
    except Exception as e:
        print(f"[FEHLER] Konnte Input nicht lesen/parsen: {e}", file=sys.stderr)
        sys.exit(1)

    # Anreichern
    enriched = [enrich(e, n_keywords=args.keywords, short_len=args.short_len) for e in data]

    # Debug-Vorschau
    if enriched:
        first = enriched[0]
        k = first.get("keywords", [])[:8]
        sd = first.get("short_definition", "")[:140]
        keys_preview = [kk for kk in ("id", "name", "keywords", "short_definition", "csv_data") if kk in first]
        print(f"[INFO] First enriched entry keys: {keys_preview}")
        print(f"[INFO] Sample keywords(0): {k}")
        print(f"[INFO] short_definition(0): {sd}")

    # Schreiben
    content = dump_json_pretty(enriched)
    try:
        if args.always_write:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(content, encoding="utf-8")
            print(f"[OK] geschrieben (forced): {args.output}  (Indikatoren: {len(enriched)})")
        else:
            changed = write_if_changed(args.output, content)
            if changed:
                print(f"[OK] geschrieben: {args.output}  (Indikatoren: {len(enriched)})")
            else:
                print(f"[OK] unverändert: {args.output}  (Indikatoren: {len(enriched)})")
    except Exception as e:
        print(f"[FEHLER] Konnte Output nicht schreiben: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
