import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("extract_aqi")

BASE_URL_CURRENT = "https://api.openweathermap.org/data/2.5/air_pollution"
BASE_URL_HISTORY = "https://api.openweathermap.org/data/2.5/air_pollution/history"


def _base_dir() -> Path:
    return Path("/opt/airflow/raw") if Path("/opt/airflow").exists() else Path("raw")


def _write_record(nom_ville: str, pays: str, lat: float, lon: float, item: dict, base_dir: Path) -> Path | None:
    dt = datetime.fromtimestamp(item["dt"], tz=timezone.utc)

    raw_path = (
            base_dir
            / f"ville={nom_ville}"
            / str(dt.year)
            / f"{dt.month:02d}"
            / f"{dt.day:02d}"
            / f"{dt.hour:02d}"
    )
    raw_path.mkdir(parents=True, exist_ok=True)

    filename = f"raw_{dt.strftime('%Y%m%d_%H')}.json"
    full_path = raw_path / filename

    if full_path.exists():
        logger.info(f"Déjà présent, on ne réécrit pas (idempotence) : {full_path}")
        return full_path

    raw_data = {
        "city": nom_ville,
        "country": pays,
        "lat": lat,
        "lon": lon,
        "timestamp": item["dt"],
        "datetime_utc": dt.isoformat(),
        "aqi": item["main"]["aqi"],
        "components": item["components"],
    }

    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, indent=2, ensure_ascii=False)

    return full_path


def extract_city(ville: dict, api_key: str, execution_date: str = None) -> str:
    nom_ville = ville.get("ville") or ville.get("nom") or ville.get("name", "inconnue")
    pays = ville.get("pays", "France")
    lat = ville.get("lat")
    lon = ville.get("lon")

    params = {"lat": lat, "lon": lon, "appid": api_key}

    try:
        response = requests.get(BASE_URL_CURRENT, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        item = data["list"][0]
        full_path = _write_record(nom_ville, pays, lat, lon, item, _base_dir())

        logger.info(f"Extrait : {nom_ville} → {full_path}")
        return str(full_path)

    except Exception as e:
        logger.error(f"Erreur lors de l'extraction pour {nom_ville}: {e}")
        raise


def extract_city_history(
        ville: dict, api_key: str, start_ts: int, end_ts: int, max_retries: int = 3
) -> None:
    nom_ville = ville.get("ville") or ville.get("nom") or ville.get("name", "inconnue")
    pays = ville.get("pays", "France")
    lat = ville.get("lat")
    lon = ville.get("lon")

    params = {"lat": lat, "lon": lon, "start": start_ts, "end": end_ts, "appid": api_key}

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(BASE_URL_HISTORY, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            base_dir = _base_dir()
            records = data.get("list", [])
            written = 0
            skipped = 0

            for item in records:
                full_path = _write_record(nom_ville, pays, lat, lon, item, base_dir)
                if full_path is not None:
                    written += 1

            logger.info(
                f"Backfill terminé pour {nom_ville} : {len(records)} mesures reçues, "
                f"{written} fichiers traités (nouveaux ou déjà existants)."
            )
            return

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout pour {nom_ville} (tentative {attempt}/{max_retries}).")
            if attempt < max_retries:
                time.sleep(5)
            else:
                logger.error(f"Échec définitif pour {nom_ville} après {max_retries} tentatives (timeout).")
        except Exception as e:
            logger.error(f"Erreur lors du backfill pour {nom_ville}: {e}")
            return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script d'extraction des données AQI")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["backfill", "current"],
        default="backfill",
        help="Mode d'extraction ('backfill' pour l'historique, 'current' pour l'instant T)",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        help="Nombre de mois d'historique à récupérer en mode backfill (défaut : 3, idéal : 12)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        logger.error("ERREUR : La variable OPENWEATHER_API_KEY est introuvable dans l'environnement / fichier .env.")
        sys.exit(1)

    villes_path = Path("config/villes.json")
    if villes_path.exists():
        with open(villes_path, encoding="utf-8") as f:
            villes = json.load(f)
    else:
        logger.error(f"Fichier de configuration {villes_path} introuvable.")
        sys.exit(1)

    if args.mode == "backfill":
        now = int(time.time())
        start = now - (args.months * 30 * 24 * 3600)
        logger.info(f"=== Début de l'extraction Backfill ({args.months} mois) ===")
        for ville in villes:
            extract_city_history(ville, api_key, start, now)
            time.sleep(1)
        logger.info("=== Backfill terminé avec succès ===")

    elif args.mode == "current":
        logger.info("=== Début de l'extraction courante ===")
        for ville in villes:
            extract_city(ville, api_key)
        logger.info("=== Extraction courante terminée avec succès ===")