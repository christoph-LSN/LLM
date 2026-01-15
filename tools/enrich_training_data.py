import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "training_data.json"
OUTPUT = ROOT / "assets/data/indicators.json"

STOPWORDS = {
    "und","oder","der","die","das","mit","von","im","in","auf","zu","für",
    "eine","einer","eines","ist","sind","werden","wird","als","auch"
}

def tokenize(text):
    words = re.findall(r"[a-zäöüß\-]{4,}", text.lower())
    return [w for w in words if w not in STOPWORDS]

def extract_keywords(entry, n=12):
    text = " ".join([
        entry.get("name",""),
        entry.get("definition",""),
        entry.get("methodology","")
    ])
    tokens = tokenize(text)
    return [w for w,_ in Counter(tokens).most_common(n)]

def short_text(text, max_len=280):
    if not text:
        return ""
    return text[:max_len].rsplit(" ",1)[0] + "…"

def enrich(entry):
    entry["keywords"] = extract_keywords(entry)
    entry["short_definition"] = short_text(entry.get("definition",""))
    return entry

def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    enriched = [enrich(e) for e in data]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[OK] geschrieben: {OUTPUT}  (Indikatoren: {len(enriched)})")

if __name__ == "__main__":
    main()
