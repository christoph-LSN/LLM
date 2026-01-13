# tools/build_static_rag.py
import json, os, csv, glob, yaml

OUT_DIR = "assets/data"
os.makedirs(OUT_DIR, exist_ok=True)

facts = {}
docs  = []

# CSV -> facts.json
for path in glob.glob("indicator_CSV/indicator_*.csv"):
    ind_id = os.path.basename(path).replace("indicator_", "").replace(".csv", "")
    series = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            y = int(row.get("Year") or row.get("Jahr") or 0)
            v = float(row.get("Value") or row.get("Wert") or "nan")
            series.append({"year": y, "value": v})
    facts[ind_id] = {"unit": "N/A", "series": sorted(series, key=lambda x: x["year"]),
                     "source": "N/A", "url": f"/{ind_id}/"}

# Meta (YAML/MD) -> docs.json
for path in glob.glob("indicator_meta/*.y*ml"):
    ind_id = os.path.basename(path).split(".")[0]
    with open(path, encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    docs.append({
        "id": ind_id,
        "title": meta.get("SDG_INDICATOR", ""),
        "summary": (meta.get("STAT_CONC_DEF", "") or "")[:400],
        "snippets": [meta.get("DATA_SOURCE_TYPE", ""), meta.get("COMPILING_ORG", "")],
        "url": f"/{ind_id}/"
    })

with open(os.path.join(OUT_DIR, "facts.json"), "w", encoding="utf-8") as f:
    json.dump(facts, f, ensure_ascii=False)

with open(os.path.join(OUT_DIR, "docs.json"), "w", encoding="utf-8") as f:
    json.dump(docs, f, ensure_ascii=False)
