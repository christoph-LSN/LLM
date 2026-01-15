
# coding: utf-8
import json
import re
import sys
import argparse
import hashlib
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "training_data.json"
OUTPUT = ROOT / "assets/data/indicators.json"

# Erweiterbare Stopwortbasis (bewusst klein; Domänenwörter ggf. ergänzen)
STOPWORDS = {
    "und","oder","der","die","das","mit","von","im","in","auf","zu","für",
    "eine","einer","eines","ist","sind","werden","wird","als","auch",
    "am","an","bei","beim","vom","zum","zur","dass","nicht","kein","ohne",
    "nach","über","unter","zwischen"
}

# Wörter >= 4 Zeichen (Klein/Groß egal)
WORD_RE = re.compile(r"[a-zäöüß]{4,}", re.IGNORECASE)

# Einfache HTML-Bereinigung (Tags entfernen)
TAG_RE = re.compile(r"<[^>]+>")

def clean_html(s: str) -> str:
    if not s:
        return ""
    # Tags raus, Entities grob entschärfen
    txt = TAG_RE.sub(" ", s)
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&")
    return " ".join(txt.split())

def normalize_text(text: str) -> str:
    """Normiert Bindestriche zu Leerzeichen, lowercased, vereinheitlicht Trennzeichen."""
    if not text:
        return ""
    # Verschiedene Bindestriche/Trennzeichen zu Leerzeichen
    text = (text
            .replace("–", " ")
            .replace("—", " ")
            .replace("‑", " ")
            .replace("-", " ")
            .replace("/", " "))
    return text.lower()

def tokenize(text: str) -> List[str]:
    """Extrahiert Wörter (>=4 Zeichen), filtert Stopwörter."""
    text = normalize_text(text)
    words = WORD_RE.findall(text)
    return [w for w in words if w not in STOPWORDS]

def extract_keywords(entry: Dict[str, Any], n: int = 12) -> List[str]:
    """
    Zählt Häufigkeiten aus name/definition/methodology (+cleaned additional_info),
    deterministisch sortiert (freq desc, alpha asc), gibt Top-n zurück.
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
    """Schneidet intelligent ab: nur Ellipse, wenn wirklich gekürzt; hält Wortgrenzen, Fallback harte Grenze."""
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

def enrich(entry: Dict[str, Any], n_keywords: int = 12, short_len: int = 280) -> Dict[str, Any]:
    """Erzeugt 'keywords' und 'short_definition' – Original bleibt ansonsten unverändert."""
    entry = dict(entry)  # nicht in-place modifizieren
    entry["keywords"] = extract_keywords(entry, n=n_keywords)
    entry["short_definition"] = short_text(str(entry.get("definition", "") or ""), max_len=short_len)
    return entry

def load_indicators(input_path: Path) -> List[Dict[str, Any]]:
    """
    Liest die Indikatoren robust ein und gibt eine Liste von Dicts zurück.
    Unterstützt:
      A) Root = list[dict]
      B) Richtext-Wrapper -> value.text enthält JSON-Array als String
      C) Einzelobjekt {name,definition,methodology,...} -> [obj]
    """
    raw = json.loads(input_path.read_text(encoding="utf-8"))

    # A) Bereits eine Liste
    if isinstance(raw, list):
        print(f"[INFO] Input form: list with {len(raw)} entries")
        return raw

    # B) Richtext-Wrapper mit :content/value/text
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, dict) and "value" in v and isinstance(v["value"], dict) and "text" in v["value"]:
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
    Schreibt content nach out_path, aber nur wenn sich der Inhalt geändert hat.
    Rückgabe: True, wenn geschrieben wurde; False, wenn identisch (unchanged).
    """
    try:
        old = out_path.read_text(encoding="utf-8")
        if hashlib.sha256(old.encode("utf-8")).hexdigest() == hashlib.sha256(content.encode("utf-8")).hexdigest():
            print("[INFO] Output unchanged – skipping write.")
            return False
    except FileNotFoundError:
        pass

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return True

def main():
    parser = argparse.ArgumentParser(description="Enrich indicator training data with keywords and short definitions.")
    parser.add_argument("--input", type=Path, default=INPUT, help="Pfad zur Input-JSON (Liste / Richtext-Wrapper / Einzelobjekt)")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Zielpfad für angereicherte JSON")
    parser.add_argument("--keywords", type=int, default=12, help="Anzahl der Keywords pro Eintrag")
    parser.add_argument("--short-len", type=int, default=280, help="Maximale Länge der Kurzdefinition")
    args = parser.parse_args()

    try:
        data = load_indicators(args.input)
    except Exception as e:
        print(f"[FEHLER] Konnte Input nicht lesen/parsen: {e}", file=sys.stderr)
        sys.exit(1)

    enriched = [enrich(e, n_keywords=args.keywords, short_len=args.short_len) for e in data]

    # Debug-Vorschau ins Log
    if enriched:
        k = enriched[0].get("keywords", [])[:8]
        sd = enriched[0].get("short_definition", "")[:140]
        print(f"[INFO] First enriched entry keys: {list(enriched[0].keys())}")
        print(f"[INFO] Sample keywords(0): {k}")
        print(f"[INFO] short_definition(0): {sd}")

    # Stabilisieren + optional nur bei Änderung schreiben
    content = dump_json_pretty(enriched)
    try:
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
