
# coding: utf-8
import json
import re
import sys
import argparse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "training_data.json"
OUTPUT = ROOT / "assets/data/indicators.json"

# Erweiterbare Stopwortbasis (bewusst klein gehalten; Domänenwörter ggf. ergänzen)
STOPWORDS = {
    "und","oder","der","die","das","mit","von","im","in","auf","zu","für",
    "eine","einer","eines","ist","sind","werden","wird","als","auch",
    "am","an","bei","beim","vom","zum","zur","dass","nicht","kein","ohne","nach","über","unter","zwischen"
}

WORD_RE = re.compile(r"[a-zäöüß]{4,}", re.IGNORECASE)

def normalize_text(text: str) -> str:
    """Normiert Bindestriche zu Leerzeichen und lowercased."""
    if not text:
        return ""
    # Bindestriche zu Leerzeichen, um Komposita ggf. aufzuspalten
    text = text.replace("-", " ")
    return text.lower()

def tokenize(text: str):
    """Extrahiert Wörter (>=4 Zeichen), filtert Stopwörter."""
    text = normalize_text(text)
    words = WORD_RE.findall(text)
    return [w for w in words if w not in STOPWORDS]

def extract_keywords(entry: dict, n: int = 12):
    """Zählt Häufigkeiten, gibt deterministisch (häufigkeit, dann alphabetisch) die Top-n zurück."""
    parts = [
        str(entry.get("name", "") or ""),
        str(entry.get("definition", "") or ""),
        str(entry.get("methodology", "") or "")
    ]
    text = " ".join(parts)
    tokens = tokenize(text)
    if not tokens:
        return []
    counts = Counter(tokens)
    # Sortierung: erst nach Häufigkeit (absteigend), dann alphabetisch (aufsteigend) für Stabilität
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in items[:n]]

def short_text(text: str, max_len: int = 280):
    """Schneidet intelligent ab: nur Ellipse, wenn wirklich gekürzt; hält Wortgrenzen, fall-back harte Grenze."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text  # Keine Ellipse, weil nicht gekürzt

    slice_ = text[:max_len]

    # Versuche, auf letztes Leerzeichen zu kürzen
    if " " in slice_:
        slice_ = slice_.rsplit(" ", 1)[0]

    # Trim und ggf. Satzzeichen vor Ellipse entfernen
    slice_ = slice_.rstrip(" ,;:-")
    return slice_ + "…"

def enrich(entry: dict, n_keywords: int = 12, short_len: int = 280):
    entry = dict(entry)  # nicht in-place modifizieren, falls Original noch benötigt
    entry["keywords"] = extract_keywords(entry, n=n_keywords)
    entry["short_definition"] = short_text(str(entry.get("definition", "") or ""), max_len=short_len)
    return entry

def main():
    parser = argparse.ArgumentParser(description="Enrich indicator training data with keywords and short definitions.")
    parser.add_argument("--input", type=Path, default=INPUT, help="Pfad zur Input-JSON (Array von Objekten)")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Zielpfad für angereicherte JSON")
    parser.add_argument("--keywords", type=int, default=12, help="Anzahl der Keywords pro Eintrag")
    parser.add_argument("--short-len", type=int, default=280, help="Maximale Länge der Kurzdefinition")
    args = parser.parse_args()

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Input-JSON muss ein Array von Objekten sein.")
    except Exception as e:
        print(f"[FEHLER] Konnte Input nicht lesen/parsen: {e}", file=sys.stderr)
        sys.exit(1)

    enriched = [enrich(e, n_keywords=args.keywords, short_len=args.short_len) for e in data]

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] geschrieben: {args.output}  (Indikatoren: {len(enriched)})")
    except Exception as e:
        print(f"[FEHLER] Konnte Output nicht schreiben: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
