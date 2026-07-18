"""
build_clean.py
---------------
Reconstruit ENTIÈREMENT clean/air_quality_clean.csv à partir de raw/.
Ne lit jamais rien d'autre que raw/, n'écrit jamais dans raw/.

Règles appliquées :
  - une ligne par (ville, heure)
  - triée chronologiquement (ville puis horodatage)
  - dédoublonnée : si plusieurs fichiers raw contiennent la même
    (ville, heure) -- normal, la collecte horaire et le backfill peuvent se
    recouper -- on ne garde qu'une seule ligne.

Usage :
    python scripts/stockage/build_clean.py
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # racine du repo
RAW_DIR = ROOT / "raw"
CLEAN_DIR = ROOT / "clean"
CLEAN_FILE = CLEAN_DIR / "air_quality_clean.csv"

FIELDNAMES = [
    "city", "country", "latitude", "longitude",
    "timestamp_utc",
    "aqi",
    "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3",
]


def iter_raw_files():
    if not RAW_DIR.exists():
        return
    yield from sorted(RAW_DIR.glob("*/*.json"))


def extract_rows(raw_record: dict):
    """Un fichier raw peut contenir 1 (collecte horaire) ou N (backfill)
    mesures dans raw_response.list. On les extrait toutes."""
    rows = []
    payload = raw_record.get("raw_response", {})
    for entry in payload.get("list", []):
        dt_unix = entry.get("dt")
        if dt_unix is None:
            continue
        ts = datetime.fromtimestamp(dt_unix, tz=timezone.utc).isoformat()
        components = entry.get("components", {})
        rows.append({
            "city": raw_record["city"],
            "country": raw_record["country"],
            "latitude": raw_record["lat"],
            "longitude": raw_record["lon"],
            "timestamp_utc": ts,
            "aqi": entry.get("main", {}).get("aqi"),
            "co": components.get("co"),
            "no": components.get("no"),
            "no2": components.get("no2"),
            "o3": components.get("o3"),
            "so2": components.get("so2"),
            "pm2_5": components.get("pm2_5"),
            "pm10": components.get("pm10"),
            "nh3": components.get("nh3"),
        })
    return rows


def main():
    dedup = {}  # (city, timestamp_utc) -> row  (dernier fichier lu gagne)

    n_files = 0
    for raw_path in iter_raw_files():
        n_files += 1
        try:
            with open(raw_path, encoding="utf-8") as f:
                raw_record = json.load(f)
        except json.JSONDecodeError:
            print(f"[SKIP] {raw_path} : JSON invalide")
            continue

        for row in extract_rows(raw_record):
            key = (row["city"], row["timestamp_utc"])
            dedup[key] = row

    rows = sorted(dedup.values(), key=lambda r: (r["city"], r["timestamp_utc"]))

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLEAN_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Fichiers raw lus     : {n_files}")
    print(f"Lignes clean écrites : {len(rows)}")
    print(f"Fichier généré       : {CLEAN_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
