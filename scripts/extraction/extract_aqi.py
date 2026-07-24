import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("extract_aqi")


def extract_city(ville: dict, api_key: str, execution_date: str = None) -> str:
    nom_ville = ville.get("ville") or ville.get("nom") or ville.get("name", "inconnue")
    pays = ville.get("pays", "France")
    lat = ville.get("lat")
    lon = ville.get("lon")

    url = "http://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        raw_data = {
            "city": nom_ville,
            "country": pays,
            "lat": lat,
            "lon": lon,
            "timestamp": data["list"][0]["dt"],
            "aqi": data["list"][0]["main"]["aqi"],
            "components": data["list"][0]["components"]
        }

        base_dir = Path("/opt/airflow/raw") if Path("/opt/airflow").exists() else Path("raw")

        dt = datetime.fromtimestamp(data["list"][0]["dt"])
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

        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Extrait : {nom_ville} → {full_path}")
        return str(full_path)

    except Exception as e:
        logger.error(f"Erreur lors de l'extraction pour {nom_ville}: {e}")
        raise


def extract_city_history(ville: dict, api_key: str, start_ts: int, end_ts: int, max_retries: int = 3) -> None:
    nom_ville = ville.get("ville") or ville.get("nom") or ville.get("name", "inconnue")
    pays = ville.get("pays", "France")
    lat = ville.get("lat")
    lon = ville.get("lon")

    url = "http://api.openweathermap.org/data/2.5/air_pollution/history"
    params = {
        "lat": lat,
        "lon": lon,
        "start": start_ts,
        "end": end_ts,
        "appid": api_key
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            base_dir = Path("/opt/airflow/raw") if Path("/opt/airflow").exists() else Path("raw")
            records = data.get("list", [])

            for item in records:
                raw_data = {
                    "city": nom_ville,
                    "country": pays,
                    "lat": lat,
                    "lon": lon,
                    "timestamp": item["dt"],
                    "aqi": item["main"]["aqi"],
                    "components": item["components"]
                }

                dt = datetime.fromtimestamp(item["dt"])
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

                with open(full_path, "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Backfill terminé pour {nom_ville} ({len(records)} enregistrements enregistrés).")
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
        help="Mode d'extraction ('backfill' pour l'historique de 3 mois, 'current' pour l'instant T)"
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
        three_months_ago = now - (90 * 24 * 3600)
        logger.info("=== Debut de l'extraction Backfill (3 mois) ===")
        for ville in villes:
            extract_city_history(ville, api_key, three_months_ago, now)
            time.sleep(1)
        logger.info("== Backfill termine avec succes ==")

    elif args.mode == "current":
        logger.info("== Debut de l'extraction courante ==")
        for ville in villes:
            extract_city(ville, api_key)
        logger.info("== Extraction courante terminee avec succes ==")
