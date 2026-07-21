import os
import sys
import json
import time
import logging
import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv  # <-- Chargement du .env

# Charge le fichier .env si présent
load_dotenv()

# Configuration du logger pour afficher les messages dans la console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("extract_aqi")

# Definition des 5 villes et de leurs coordonnees GPS
VILLES = [
    {"nom": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"nom": "Marseille", "lat": 43.2965, "lon": 5.3698},
    {"nom": "Lyon", "lat": 45.7640, "lon": 4.8357},
    {"nom": "Toulouse", "lat": 43.6047, "lon": 1.4442},
    {"nom": "Nice", "lat": 43.7102, "lon": 7.2620}
]

def fetch_air_pollution_history(lat, lon, start_ts, end_ts, api_key):
    """Effectue la requete API pour recuperer l'historique de pollution d'une position GPS."""
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

# --- BLOC DE TEST POUR UNE SEULE VILLE (KAN-10) ---
if __name__ == "__main__":
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    
    if not api_key:
        logger.error("Veuillez definir la variable OPENWEATHER_API_KEY dans votre fichier .env.")
        sys.exit(1)
        
    paris = VILLES[0]
    now = int(time.time())
    two_hours_ago = now - 7200
    
    logger.info(f"Test d'extraction pour {paris['nom']}...")
    resultat = fetch_air_pollution_history(
        lat=paris["lat"],
        lon=paris["lon"],
        start_ts=two_hours_ago,
        end_ts=now,
        api_key=api_key
    )
    
    if resultat and "list" in resultat:
        logger.info(f"✅ Test reussi ! {len(resultat['list'])} mesure(s) recue(s) pour {paris['nom']}.")
        print(json.dumps(resultat, indent=2))
    else:
        logger.error("❌ Le test a echoue.")