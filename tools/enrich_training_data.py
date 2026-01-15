
# coding: utf-8
"""
Enrich indicator training data for UI use:
- 'keywords' (deterministisch) und 'short_definition'
- UI-Kacheln/Kataloge: latest_year/value, units, time_coverage, trend_5y
- Navigations-/SEO-Hilfen: slug, name_normalized
- Metadaten: sources (Domains aus Links), data_status_parsed (year)
- Coverage: region_coverage (Anzahl Regionen/Jahre)
- robustes Einlesen (Liste, Richtext-Wrapper, Einzelobjekt)
- idempotentes Schreiben (nur bei echter Änderung, optional erzwingbar)
"""

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from html import unescape as html_unescape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Default-Pfade relativ zum Repo-Root (tools/..)
ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "training_data.json"
OUTPUT = ROOT / "assets/data/indicators.json"

# ---------- Basiskonstanten ----------

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

# Link-Erkennung (auch falls HTML bereits escaped ist)
URL_RE = re.compile(r"https?://[^\s\"'<>)]+")

# Keys, die je nach Quelle variieren können
YEAR_KEYS = ["Year", "\ufeffYear", "year"]
VALUE_KEYS = ["Value", "value", "Wert"]
REGION_KEYS = ["Gebietseinheit", "Region", "region", "gebietseinheit"]
GEOCODE_KEYS = ["GeoCode", "Geo", "Code", "geocode"]
UNITS_KEYS = ["Units", "Unit", "Einheit", "units"]

# ---------- Utilities ----------

def clean_html(s: str) -> str:
    """Entfernt HTML-Tags und häufige Entities, trimmt Whitespace."""
    if not s:
        return ""
    s = html_unescape(s)
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
        .replace("·", " ")
    )
    return text.lower()

def strip_diacritics(s: str) -> str:
    """Diakritika entfernen (für name_normalized)."""
    if not s:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )

def to_slug(*parts: str) -> str:
    """Erstellt einen URL-/SEO-freundlichen Slug aus id + name."""
    joined = " ".join(p for p in parts if p)
    lower = joined.lower()
    # deutsche Umlaute
    repl = (
        ("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"),
        ("à", "a"), ("á", "a"), ("è", "e"), ("é", "e"), ("ê", "e"),
        ("ì", "i"), ("í", "i"), ("ò", "o"), ("ó", "o"), ("ù", "u"), ("ú", "u")
    )
    for a, b in repl:
        lower = lower.replace(a, b)
    # Diakritika entfernen
    lower = strip_diacritics(lower)
    # nur a-z0-9 und Leerzeichen/- zulassen
    lower = re.sub(r"[^a-z0-9\s\-]", " ", lower)
    # Whitespace -> '-'
    lower = re.sub(r"\s+", "-", lower).strip("-")
    # Mehrfache '-' auf eins
    lower = re.sub(r"-{2,}", "-", lower)
    return lower

def tokenize(text: str) -> List[str]:
    """Extrahiert Wörter (>=4 Zeichen), filtert Stopwörter."""
    text = normalize_text(text)
    words = WORD_RE.findall(text)
    return [w for w in words if w not in STOPWORDS]

def parse_year(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(str(v).strip())
    except Exception:
        # 4-stellige Jahreszahl irgendwo im String
        m = re.search(r"\b(19|20)\d{2}\b", str(v))
        return int(m.group(0)) if m else None

def parse_number(v: Any) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    # Dezimal-Komma -> Punkt
    s = s.replace(" ", "").replace("\u00a0", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None

def get_first_key(d: Dict[str, Any], candidates: List[str]) -> Optional[str]:
    for k in candidates:
        if k in d:
            return k
    # Fallback: case-insensitive
    lower = {k.lower(): k for k in d}
    for k in candidates:
        if k.lower() in lower:
            return lower[k.lower()]
    return None

def extract_urls(s: str) -> List[str]:
    """Findet http(s):// Links — auch wenn HTML zuvor escaped war."""
    if not s:
        return []
    s = html_unescape(s)
    # Links in href="...":
    hrefs = re.findall(r'href="\'["\']', s)
    raw = URL_RE.findall(s)
    urls = set(hrefs) | set(raw)
    # nur http(s)
    return [u for u in urls if u.startswith("http://") or u.startswith("https://")]

def extract_domains(urls: List[str]) -> List[str]:
    hosts = []
    for u in urls:
        try:
            h = urlparse(u).hostname or ""
            h = h.lower()
            if h.startswith("www."):
                h = h[4:]
            if h and h not in hosts:
                hosts.append(h)
        except Exception:
            pass
    return hosts

# ---------- Enrichment: Text ----------

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

# ---------- Enrichment: CSV / Zeitreihen ----------

def derive_units(rows: List[Dict[str, Any]]) -> Optional[str]:
    # 1) Explizite Units-Spalte
    for row in rows:
        uk = get_first_key(row, UNITS_KEYS)
        if uk and str(row.get(uk, "")).strip():
            return str(row[uk]).strip()
    # 2) Heuristik auf Basis 'name'/'definition'
    # Vorsichtig: nur %-Hinweise => Prozent
    # ansonsten default None (UI kann "—" anzeigen)
    return "%"

def filter_rows_for_region(rows: List[Dict[str, Any]], region_name: str) -> List[Dict[str, Any]]:
    picked = []
    for r in rows:
        rk = get_first_key(r, REGION_KEYS)
        if rk and str(r.get(rk, "")).strip().lower() == region_name.lower():
            picked.append(r)
    return picked

def by_year_series(rows: List[Dict[str, Any]]) -> Dict[int, float]:
    """Extrahiert {year -> value} aus beliebigen Reihen (parallel Regions ignoriert)."""
    series = {}
    for r in rows:
        yk = get_first_key(r, YEAR_KEYS)
        vk = get_first_key(r, VALUE_KEYS)
        if not yk or not vk:
            continue
        y = parse_year(r.get(yk))
        v = parse_number(r.get(vk))
        if y is None or v is None:
            continue
        # Bei Mehrfachtreffern pro Jahr: Mittelwert (konservativ)
        if y in series:
            series[y] = (series[y] + v) / 2.0
        else:
            series[y] = v
    return series

def series_for_region(rows: List[Dict[str, Any]], region_name: str) -> Dict[int, float]:
    return by_year_series(filter_rows_for_region(rows, region_name))

def time_coverage(rows: List[Dict[str, Any]]) -> Optional[Dict[str, int]]:
    ys = []
    for r in rows:
        yk = get_first_key(r, YEAR_KEYS)
        if not yk:
            continue
        y = parse_year(r.get(yk))
        if y is not None:
            ys.append(y)
    if not ys:
        return None
    return {"from": min(ys), "to": max(ys), "n_years": len(set(ys))}

def latest_year_value(series: Dict[int, float]) -> Tuple[Optional[int], Optional[float]]:
    if not series:
        return (None, None)
    y = max(series.keys())
    return (y, series.get(y))

def trend_5y(series: Dict[int, float]) -> Optional[Dict[str, Any]]:
    if not series:
        return None
    years = sorted(series.keys())
    if len(years) < 2:
        return None
    y_latest = years[-1]
    # nächstgelegenes Jahr ~5 Jahre früher (oder das älteste, wenn <5 Abstände)
    y_candidates = [y for y in years if y < y_latest]
    if not y_candidates:
        return None
    y_prev = max([y for y in years if y <= y_latest - 5] or [years[0]])
    v_latest = series.get(y_latest)
    v_prev = series.get(y_prev)
    if v_latest is None or v_prev is None:
        return None
    delta = v_latest - v_prev
    eps = 1e-12
    direction = "→"
    if delta > eps:
        direction = "↑"
    elif delta < -eps:
        direction = "↓"
    return {"direction": direction, "delta": delta, "from_year": y_prev, "to_year": y_latest}

def region_coverage(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    geos = set()
    names = set()
    years = set()
    for r in rows:
        gk = get_first_key(r, GEOCODE_KEYS)
        rk = get_first_key(r, REGION_KEYS)
        yk = get_first_key(r, YEAR_KEYS)
        if gk and r.get(gk):
            geos.add(str(r[gk]))
        if rk and r.get(rk):
            names.add(str(r[rk]))
        if yk and r.get(yk) is not None:
            y = parse_year(r.get(yk))
            if y is not None:
                years.add(y)
    return {"n_regions": len(names), "n_geocodes": len(geos), "n_years": len(years)}

# ---------- Loader / Writer ----------

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

# ---------- Orchestrierung ----------

def enrich_text_fields(entry: Dict[str, Any], n_keywords: int, short_len: int) -> None:
    entry["keywords"] = extract_keywords(entry, n=n_keywords)
    entry["short_definition"] = short_text(str(entry.get("definition", "") or ""), max_len=short_len)

def enrich_ui_profile(entry: Dict[str, Any], ref_region: str) -> None:
    rows = entry.get("csv_data") or []
    if not isinstance(rows, list) or not rows:
        # immer noch sinnvolle Defaults
        entry["latest_year"] = None
        entry["latest_value"] = None
        entry["units"] = None
        entry["time_coverage"] = None
        entry["trend_5y"] = None
        entry["region_coverage"] = {"n_regions": 0, "n_geocodes": 0, "n_years": 0}
    else:
        # Units
        units = derive_units(rows)
        entry["units"] = units

        # Series (Referenzregion bevorzugt)
        series_ref = series_for_region(rows, ref_region)
        series_all = by_year_series(rows)

        # latest_year/value
        y, v = latest_year_value(series_ref if series_ref else series_all)
        entry["latest_year"] = y
        entry["latest_value"] = v

        # time coverage
        entry["time_coverage"] = time_coverage(rows)

        # trend 5y (bevorzugt Region, sonst Gesamt)
        tr = trend_5y(series_ref if series_ref else series_all)
        entry["trend_5y"] = tr

        # coverage
        entry["region_coverage"] = region_coverage(rows)

    # sources aus additional_info
    urls = extract_urls(str(entry.get("additional_info", "") or ""))
    entry["sources"] = extract_domains(urls)

    # data_status_parsed (z. B. "- Datenstand 2023")
    year = None
    m = re.search(r"(19|20)\d{2}", str(entry.get("data_status", "") or ""))
    if m:
        year = int(m.group(0))
    entry["data_status_parsed"] = {"raw": entry.get("data_status"), "year": year}

    # slug + name_normalized
    entry["slug"] = to_slug(entry.get("id"), entry.get("name"))
    entry["name_normalized"] = strip_diacritics(str(entry.get("name", "") or "")).lower()

def main():
    parser = argparse.ArgumentParser(
        description="Enrich indicator training data (UI profile)."
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
        "--ref-region",
        type=str,
        default="Niedersachsen",
        help="Bevorzugte Referenzregion für latest/trend (Default: Niedersachsen)",
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
    enriched: List[Dict[str, Any]] = []
    for e in data:
        e2 = dict(e)  # kopie
        enrich_text_fields(e2, n_keywords=args.keywords, short_len=args.short_len)
        enrich_ui_profile(e2, ref_region=args.ref_region)
        enriched.append(e2)

    # Debug-Vorschau
    if enriched:
        first = enriched[0]
        keys_preview = [
            k for k in (
                "id", "name",
                "keywords", "short_definition",
                "latest_year", "latest_value", "units",
                "time_coverage", "trend_5y",
                "sources", "data_status_parsed",
                "slug", "name_normalized",
                "region_coverage"
            ) if k in first
        ]
        print(f"[INFO] First enriched keys: {keys_preview}")
        print(f"[INFO] Sample keywords(0): {first.get('keywords', [])[:8]}")
        print(f"[INFO] short_definition(0): {(first.get('short_definition') or '')[:120]}")
        print(f"[INFO] latest: year={first.get('latest_year')} value={first.get('latest_value')} units={first.get('units')}")
        print(f"[INFO] time_coverage: {first.get('time_coverage')}")
        print(f"[INFO] trend_5y: {first.get('trend_5y')}")
        print(f"[INFO] sources: {first.get('sources')}")
        print(f"[INFO] slug: {first.get('slug')}")

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
