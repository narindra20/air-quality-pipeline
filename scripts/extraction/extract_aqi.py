
import argparse
import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path
import requests


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("extract_aqi")


VILLES = [
    {"nom": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"nom": "Marseille", "lat": 43.2965, "lon": 5.3698},
    {"nom": "Lyon", "lat": 45.7640, "lon": 4.8357},
    {"nom": "Toulouse", "lat": 43.6047, "lon": 1.4442},
    {"nom": "Nice", "lat": 43.7102, "lon": 7.2620}
]


BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "raw"

def get_api_key():
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        try:
            from google.colab import userdata
            api_key = userdata.get("OPENWEATHER_API_KEY")
        except ImportError:
            pass
            
    if not api_key:
        logger.error("La variable d'environnement 'OPENWEATHER_API_KEY' est introuvable.")
        sys.exit(1)
    return api_key

def fetch_air_pollution_history(lat, lon, start_ts, end_ts, api_key):
    url = "http://api.openweathermap.org/data/2.5/air_pollution/history"
    params = {
        "lat": lat,
        "lon": lon,
        "start": start_ts,
        "end": end_ts,
        "appid": api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            logger.warning("Rate limit atteint (429). Pause de 10 secondes...")
            time.sleep(10)
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
                
        logger.error(f"Erreur API ({response.status_code}): {response.text}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la requête : {str(e)}")
        return None

def save_single_hour_record(record, city_name, lat, lon, extracted_at):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp_mesure = record.get("dt")
    if not timestamp_mesure:
        return
        
    date_mesure = datetime.datetime.fromtimestamp(timestamp_mesure)
    date_str = date_mesure.strftime("%Y%m%d_%H%M")
    
    single_json_content = {
        "target_city": city_name,
        "latitude": lat,
        "longitude": lon,
        "extracted_at": extracted_at,
        "coord": {"lat": lat, "lon": lon},
        "list": [record]  
    }
    
    filename = f"aqi_{city_name.lower()}_{date_str}.json"
    file_path = RAW_DIR / filename
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(single_json_content, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Impossible de sauvegarder le fichier {filename} : {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Pipeline ETL - Extraction Qualité de l'Air (OpenWeather)")
    parser.add_argument(
        "--mode", 
        choices=["backfill", "hourly"], 
        default="backfill",
        help="Mode 'backfill' (12 mois d'historique) ou 'hourly' (les 2 dernières heures)."
    )
    args = parser.parse_args()
    
    api_key = get_api_key()
    now = datetime.datetime.now()
    extracted_at_iso = now.isoformat()
    
    if args.mode == "backfill":
        start_date = datetime.datetime(2025, 7, 1, 0, 0, 0)
        end_date = now
        logger.info(f" Mode BACKFILL : Récupération idéale de 12 mois ({start_date.date()} au {end_date.date()})")
    else:
        start_date = now - datetime.timedelta(hours=2)
        end_date = now
        logger.info(f" Mode HOURLY : Récupération incrémentale (Routine)")
        
    start_ts = int(time.mktime(start_date.timetuple()))
    end_ts = int(time.mktime(end_date.timetuple()))
    
    for ville in VILLES:
        logger.info(f"Extraction en cours pour : {ville['nom']}")
        
        raw_response = fetch_air_pollution_history(
            lat=ville["lat"],
            lon=ville["lon"],
            start_ts=start_ts,
            end_ts=end_ts,
            api_key=api_key
        )
        
        if raw_response and "list" in raw_response:
            records = raw_response["list"]
            logger.info(f"-> {len(records)} points horaires trouvés pour {ville['nom']}. Génération des fichiers individuels dans raw/...")
            
            for record in records:
                save_single_hour_record(
                    record=record,
                    city_name=ville["nom"],
                    lat=ville["lat"],
                    lon=ville["lon"],
                    extracted_at=extracted_at_iso
                )
            logger.info(f"✅ Terminé avec succès pour {ville['nom']}.")
        else:
            logger.error(f"❌ Échec de l'extraction ou aucune donnée pour {ville['nom']}.")
            
        time.sleep(1) 

if __name__ == "__main__":
    main()