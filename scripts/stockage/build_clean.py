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


def _extract_record(raw_path: Path) -> dict | None:
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "timestamp" not in data or "aqi" not in data:
        return None

    datetime_utc = data.get("datetime_utc")
    if not datetime_utc:
        datetime_utc = datetime.fromtimestamp(data["timestamp"], tz=timezone.utc).isoformat()

    components = data.get("components", {})
    record = {
        "city": data["city"],
        "country": data["country"],
        "lat": data["lat"],
        "lon": data["lon"],
        "timestamp": data["timestamp"],
        "datetime_utc": datetime_utc,
        "aqi": data["aqi"],
    }
    for pollutant in POLLUTANTS:
        record[pollutant] = components.get(pollutant)
    return record


def build_clean() -> str:
    raw_dir = _default_dir("RAW_DIR", "/opt/airflow/raw", "raw")
    clean_dir = _default_dir("CLEAN_DIR", "/opt/airflow/clean", "clean")
    clean_dir.mkdir(parents=True, exist_ok=True)

    all_records = []
    errors = 0
    for json_file in raw_dir.rglob("*.json"):
        try:
            record = _extract_record(json_file)
            if record:
                all_records.append(record)
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
        f"Clean généré : {clean_path} ({len(df)} lignes, "
        f"{duplicates_removed} doublons supprimés, {errors} fichiers en erreur ignorés)"
    )
    return str(clean_path)


if __name__ == "__main__":
    build_clean()