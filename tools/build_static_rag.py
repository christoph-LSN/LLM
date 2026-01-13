
#!/usr/bin/env python3
# tools/build_static_rag.py
# Erzeugt assets/data/facts.json und assets/data/docs.json aus Open-SDG CSV/Metadaten.
# Architektur A (rein statisch): Keine externen Services, nur Dateiverarbeitung.

import os, sys, json, csv, glob, re
from typing import Dict, Any, List

    print("Missing dependency: pyyaml", file=sys.stderr)# --------------------- Abhängigkeiten prüfen ---------------------
    sys.exit(1)

# --------------------- Konfiguration ------------------------------
# Pfade können per ENV überschrieben werden (z. B. im CI)
CSV_DIR  = os.getenv("CSV_DIR",  "indicator_CSV")
META_DIR = os.getenv("META_DIR", "indicator_meta")
OUT_DIR  = os.getenv("OUT_DIR",  "assets/data")

# Für korrekte Links in den JSONs (GitHub Pages Projektseiten -> "/<RepoName>")
SITE_BASEURL = (os.getenv("SITE_BASEURL", "") or "").rstrip("/")
# Standard-URL-Prefix der Indikatorseiten in Open SDG ist "/indicators"
INDICATOR_URL_PREFIX = (os.getenv("INDICATOR_URL_PREFIX", "/indicators") or "").strip("/")

# Maximale Länge der Kurzdefinition in docs.json
SUMMARY_MAXLEN = int(os.getenv("SUMMARY_MAXLEN", "600"))

# --------------------- Hilfsfunktionen ----------------------------
def indicator_url(ind_id: str) -> str:
    """Baue die Indikator-URL: /<baseurl>/indicators/<id>/"""
    base = SITE_BASEURL + "/" if SITE_BASEURL else "/"
    return f"{base}{INDICATOR_URL_PREFIX}/{ind_id}/".replace("//", "/")

def load_meta_yaml() -> Dict[str, Dict[str, Any]]:
    """Lade alle YAML-Metadateien in ein Dict: {id: meta}"""
    meta_map: Dict[str, Dict[str, Any]] = {}
    paths = sorted(glob.glob(os.path.join(META_DIR, "*.y*ml")))
    if not paths:
        print(f"[WARN] Keine Metadateien in {META_DIR} gefunden.", file=sys.stderr)
    for path in paths:
        ind_id = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}
            meta_map[ind_id] = meta
        except Exception as e:
            print(f"[WARN] Konnte Meta nicht laden: {path} ({e})", file=sys.stderr)
    return meta_map

def meta_unit(meta: Dict[str, Any]) -> str:
    for k in ("UNIT_MEASURE", "unit_measure", "COMPUTATION_UNITS", "CUNIT"):
        v = meta.get(k)
        if v: return str(v)
    return ""

def meta_source(meta: Dict[str, Any]) -> str:
    for k in ("DATA_SOURCE_TYPE", "COMPILING_ORG", "CONTACT_ORGANISATION", "SOURCE_TYPE", "source"):
        v = meta.get(k)
        if isinstance(v, list):
            v = ", ".join([str(x) for x in v if x])
        if v: return str(v)
    return ""

def meta_title(meta: Dict[str, Any]) -> str:
    return str(meta.get("SDG_INDICATOR") or meta.get("SDG_INDICATOR_INFO") or "")

def meta_summary(meta: Dict[str, Any], maxlen: int = SUMMARY_MAXLEN) -> str:
    s = str(meta.get("STAT_CONC_DEF") or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= maxlen else s[:maxlen-1].rstrip() + "…"

def parse_float(val) -> float:
    if val is None or val == "":
        raise ValueError("empty")
    # Erlaube deutschsprachige CSVs mit Komma als Dezimaltrenner
    return float(str(val).replace(",", "."))

# --------------------- Hauptlogik --------------------------------
def build():
    # Zielordner sicherstellen
    os.makedirs(OUT_DIR, exist_ok=True)

    # Metadaten laden (für Einheit/Quelle/Titel/Definition)
    meta_map = load_meta_yaml()

    facts: Dict[str, Any] = {}
    docs:  List[Dict[str, Any]] = []

    # 1) CSV -> facts.json
    csv_paths = sorted(glob.glob(os.path.join(CSV_DIR, "indicator_*.csv")))
    if not csv_paths:
        print(f"[WARN] Keine CSVs in {CSV_DIR} gefunden.", file=sys.stderr)

    for path in csv_paths:
        ind_id = os.path.basename(path).replace("indicator_", "").replace(".csv", "")
        series: List[Dict[str, Any]] = []
        try:
            with open(path, newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    y_raw = row.get("Year") or row.get("Jahr")
                    v_raw = row.get("Value") or row.get("Wert")
                    try:
                        y = int(float(y_raw))
                        v = parse_float(v_raw)
                    except Exception:
                        # Zeile überspringen, wenn Jahr/Wert fehlt/ungültig ist
                        continue
                    series.append({"year": y, "value": v})
        except Exception as e:
            print(f"[WARN] Konnte CSV nicht lesen: {path} ({e})", file=sys.stderr)

        m = meta_map.get(ind_id, {})
        facts[ind_id] = {
            "unit"  : meta_unit(m) or "N/A",
            "source": meta_source(m) or "N/A",
            "url"   : indicator_url(ind_id),
            "series": sorted(series, key=lambda x: x["year"])
        }

    # 2) Meta -> docs.json
    for ind_id, m in meta_map.items():
        docs.append({
            "id"      : ind_id,
            "title"   : meta_title(m),
            "summary" : meta_summary(m, SUMMARY_MAXLEN),
            "snippets": [meta_source(m), meta_unit(m)],
            "url"     : indicator_url(ind_id)
        })


try:
    import yaml
except ImportError:
