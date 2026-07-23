import json
import os
from pathlib import Path

import pandas as pd

POLLUTANTS = ["co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]


def _default_dir(env_var: str, airflow_path: str, local_path: str) -> Path:
    """Utilise la variable d'env si definie, sinon detecte si on tourne dans
    le conteneur Airflow (/opt/airflow existe) ou en local."""
    if os.environ.get(env_var):
        return Path(os.environ[env_var])
    if Path("/opt/airflow").exists():
        return Path(airflow_path)
    return Path(local_path)


def _extract_record(raw_path: Path) -> dict | None:
    """Un fichier raw = une seule mesure (format plat)."""
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "timestamp" not in data or "aqi" not in data:
        return None

    components = data.get("components", {})
    record = {
        "city": data["city"],
        "country": data["country"],
        "lat": data["lat"],
        "lon": data["lon"],
        "timestamp": data["timestamp"],
        "aqi": data["aqi"],
    }
    for pollutant in POLLUTANTS:
        record[pollutant] = components.get(pollutant)
    return record


def build_clean() -> str:
    """
    Reconstruit clean/ entierement depuis raw/.

    Returns:
        str: Chemin du fichier CSV clean genere
    """
    raw_dir = _default_dir("RAW_DIR", "/opt/airflow/raw", "raw")
    clean_dir = _default_dir("CLEAN_DIR", "/opt/airflow/clean", "clean")
    clean_dir.mkdir(parents=True, exist_ok=True)

    all_records = []
    for json_file in raw_dir.rglob("*.json"):
        try:
            record = _extract_record(json_file)
            if record:
                all_records.append(record)
        except (KeyError, json.JSONDecodeError) as e:
            print(f" Erreur lecture {json_file}: {e}")

    if not all_records:
        raise ValueError("Aucune donnee trouvee dans raw/")

    df = pd.DataFrame(all_records)

    df = df.drop_duplicates(subset=["city", "timestamp"], keep="last")

    df = df.sort_values(["city", "timestamp"])

    clean_path = clean_dir / "air_quality_clean.csv"
    df.to_csv(clean_path, index=False, encoding="utf-8")

    print(f" Clean genere : {clean_path} ({len(df)} lignes)")
    return str(clean_path)


if __name__ == "__main__":
    build_clean()