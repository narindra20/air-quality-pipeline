import os
import sys
import json
import time
import logging
import datetime
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

VILLES = [
    {"nom": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"nom": "Marseille", "lat": 43.2965, "lon": 5.3698},
    {"nom": "Lyon", "lat": 45.7640, "lon": 4.8357},
    {"nom": "Toulouse", "lat": 43.6047, "lon": 1.4442},
    {"nom": "Nice", "lat": 43.7102, "lon": 7.2620}
]

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
        logger.error(f"Erreur API ({response.status_code}): {response.text}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la requete : {str(e)}")
        return None

if __name__ == "__main__":
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    
    if not api_key:
        logger.error("Veuillez definir la variable OPENWEATHER_API_KEY dans votre fichier .env.")
        sys.exit(1)
        
    
    now = int(time.time())
    three_months_ago = now - (90 * 24 * 3600)
    
    logger.info("=== Debut de l'extraction sur 3 mois pour les 5 villes ===")
    
    for ville in VILLES:
        logger.info(f"Recuperation des donnees pour {ville['nom']}...")
        resultat = fetch_air_pollution_history(
            lat=ville["lat"],
            lon=ville["lon"],
            start_ts=three_months_ago,
            end_ts=now,
            api_key=api_key
        )
        
        if resultat and "list" in resultat:
            logger.info(f" {ville['nom']}: {len(resultat['list'])} enregistrements recuperes.")
        else:
            logger.error(f" Echec de la recuperation pour {ville['nom']}.")
        
        
        time.sleep(1)
        
    logger.info("=== Fin de l'extraction ===")