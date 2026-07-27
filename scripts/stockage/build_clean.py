import os
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("build_clean")

POLLUTANTS = ["co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]


def _default_dir(env_var: str, airflow_path: str, local_path: str) -> Path:
    if os.environ.get(env_var):
        return Path(os.environ[env_var])
    if Path("/opt/airflow").exists():
        return Path(airflow_path)
    return Path(local_path)


def _components_to_record(city, country, lat, lon, timestamp, aqi, components) -> dict:
    record = {
        "city": city,
        "country": country,
        "lat": lat,
        "lon": lon,
        "timestamp": timestamp,
        "datetime_utc": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
        "aqi": aqi,
    }
    for pollutant in POLLUTANTS:
        record[pollutant] = (components or {}).get(pollutant)
    return record


def _extract_records(raw_path: Path) -> list[dict]:
    """
    Retourne une liste de records à partir d'un fichier raw.

    Deux formats supportés :
    - format "horaire" (extraction courante) : un point par fichier, champs
      city/country/lat/lon/timestamp/aqi/components à la racine.
    - format "backfill/history" (endpoint /air_pollution/history) : plusieurs
      points par fichier, enveloppés avec les métadonnées ville/pays/lat/lon
      car l'API ne renvoie pas le nom de la ville pour ce endpoint.
    """
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- Format backfill/history ---
    if "api_response" in data:
        city = data["ville"]
        country = data.get("pays")
        lat = data["lat"]
        lon = data["lon"]
        records = []
        for point in data["api_response"].get("list", []):
            if "dt" not in point:
                continue
            records.append(
                _components_to_record(
                    city=city,
                    country=country,
                    lat=lat,
                    lon=lon,
                    timestamp=point["dt"],
                    aqi=point.get("main", {}).get("aqi"),
                    components=point.get("components", {}),
                )
            )
        return records

    # --- Format horaire (un seul point) ---
    if "timestamp" in data and "aqi" in data:
        return [
            _components_to_record(
                city=data["city"],
                country=data["country"],
                lat=data["lat"],
                lon=data["lon"],
                timestamp=data["timestamp"],
                aqi=data["aqi"],
                components=data.get("components", {}),
            )
        ]

    return []


def build_clean() -> str:
    raw_dir = _default_dir("RAW_DIR", "/opt/airflow/raw", "raw")
    clean_dir = _default_dir("CLEAN_DIR", "/opt/airflow/clean", "clean")
    clean_dir.mkdir(parents=True, exist_ok=True)

    all_records = []
    errors = 0
    files_seen = 0
    for json_file in raw_dir.rglob("*.json"):
        files_seen += 1
        try:
            records = _extract_records(json_file)
            if not records:
                logger.warning(f"Aucun point exploitable dans {json_file}")
            all_records.extend(records)
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Erreur lecture {json_file}: {e}")
            errors += 1

    if not all_records:
        raise ValueError("Aucune donnée trouvée dans raw/")

    df = pd.DataFrame(all_records)

    before = len(df)
    df = df.drop_duplicates(subset=["city", "timestamp"], keep="last")
    duplicates_removed = before - len(df)

    df = df.sort_values(["city", "timestamp"]).reset_index(drop=True)

    clean_path = clean_dir / "air_quality_clean.csv"
    df.to_csv(clean_path, index=False, encoding="utf-8")

    logger.info(
        f"Clean généré : {clean_path} ({len(df)} lignes à partir de {files_seen} fichiers raw, "
        f"{duplicates_removed} doublons supprimés, {errors} fichiers en erreur ignorés)"
    )
    return str(clean_path)


if __name__ == "__main__":
    build_clean()