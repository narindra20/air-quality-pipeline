# TODO: OpenWeather API extraction script (backfill + hourly)
"""
extract_aqi.py
---------------
Collecte des données de qualité de l'air (OpenWeatherMap Air Pollution API)
pour les 5 villes définies dans cities.json.

Deux modes :

  --mode current    : un appel "maintenant" par ville (collecte horaire,
                       pensé pour être rejoué toutes les heures par le DAG).
  --mode backfill    : historique sur une période donnée, découpé en
                       tranches de 7 jours (un appel = une tranche = 1 ville).

Dans les deux cas : un fichier brut = un appel API = une ville, écrit dans
raw/<slug_ville>/... . raw/ n'est JAMAIS modifié après écriture (append-only,
c'est notre sauvegarde). clean/ est reconstruit à part par
scripts/stockage/build_clean.py.

Usage :
    export OWM_API_KEY="votre_cle"          # jamais en dur dans le code
    python scripts/extraction/extract_aqi.py --mode current
    python scripts/extraction/extract_aqi.py --mode backfill --months 3
    python scripts/extraction/extract_aqi.py --mode backfill --start 2025-07-01 --end 2026-07-01
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent.parent.parent  # racine du repo
CITIES_FILE = Path(__file__).resolve().parent / "cities.json"
RAW_DIR = ROOT / "raw"

CURRENT_URL = "http://api.openweathermap.org/data/2.5/air_pollution"
HISTORY_URL = "http://api.openweathermap.org/data/2.5/air_pollution/history"
CHUNK_DAYS = 7
EARLIEST_AVAILABLE = datetime(2020, 11, 27, tzinfo=timezone.utc)


def get_api_key() -> str:
    """La clé ne doit JAMAIS être écrite en dur : uniquement via variable
    d'environnement / secret (OWM_API_KEY)."""
    key = os.environ.get("OWM_API_KEY")
    if not key:
        sys.exit("Erreur : variable d'environnement OWM_API_KEY manquante.")
    return key


def load_cities():
    with open(CITIES_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_raw(city: dict, payload: dict, source: str, filename: str, extra: dict | None = None):
    city_dir = RAW_DIR / city["slug"]
    city_dir.mkdir(parents=True, exist_ok=True)
    out_path = city_dir / filename

    record = {
        "city": city["city"],
        "slug": city["slug"],
        "country": city["country"],
        "lat": city["lat"],
        "lon": city["lon"],
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "raw_response": payload,
    }
    if extra:
        record.update(extra)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return out_path


# ---------------------------------------------------------------------------
# Mode "current" : collecte horaire
# ---------------------------------------------------------------------------

def run_current(cities, api_key):
    now = datetime.now(timezone.utc)
    ok, failed = 0, 0

    for city in cities:
        url = f"{CURRENT_URL}?lat={city['lat']}&lon={city['lon']}&appid={api_key}"
        try:
            with urlopen(url, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            stamp = now.strftime("%Y%m%dT%H%M%SZ")
            path = save_raw(city, payload, "openweathermap_air_pollution_current",
                             f"{city['slug']}_{stamp}.json")
            print(f"[OK]   {city['city']:<15} -> {path.relative_to(ROOT)}")
            ok += 1
        except (URLError, HTTPError) as e:
            print(f"[FAIL] {city['city']:<15} -> erreur réseau/API : {e}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] {city['city']:<15} -> erreur inattendue : {e}")
            failed += 1
        time.sleep(1)

    print(f"\nTerminé (current) : {ok} succès, {failed} échec(s) sur {len(cities)} villes.")
    if failed == len(cities):
        sys.exit(1)


# ---------------------------------------------------------------------------
# Mode "backfill" : historique
# ---------------------------------------------------------------------------

def daterange_chunks(start: datetime, end: datetime, days: int):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days), end)
        yield cur, nxt
        cur = nxt


def run_backfill(cities, api_key, months: int, start_arg: str | None, end_arg: str | None):
    end = (datetime.strptime(end_arg, "%Y-%m-%d").replace(tzinfo=timezone.utc)
           if end_arg else datetime.now(timezone.utc))
    if start_arg:
        start = datetime.strptime(start_arg, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        start = end - timedelta(days=30 * months)
    start = max(start, EARLIEST_AVAILABLE)

    if start >= end:
        sys.exit("Erreur : la date de début doit être avant la date de fin.")

    print(f"Backfill du {start.date()} au {end.date()} pour {len(cities)} ville(s)\n")

    total, skipped, ok, failed = 0, 0, 0, 0
    for city in cities:
        for c_start, c_end in daterange_chunks(start, end, CHUNK_DAYS):
            total += 1
            stamp_start = c_start.strftime("%Y%m%dT%H%M%SZ")
            stamp_end = c_end.strftime("%Y%m%dT%H%M%SZ")
            filename = f"{city['slug']}_backfill_{stamp_start}_{stamp_end}.json"
            expected = RAW_DIR / city["slug"] / filename
            if expected.exists():
                skipped += 1
                continue

            url = (f"{HISTORY_URL}?lat={city['lat']}&lon={city['lon']}"
                   f"&start={int(c_start.timestamp())}&end={int(c_end.timestamp())}"
                   f"&appid={api_key}")
            try:
                with urlopen(url, timeout=30) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                save_raw(city, payload, "openweathermap_air_pollution_history", filename,
                          extra={"window_start_utc": c_start.isoformat(),
                                 "window_end_utc": c_end.isoformat()})
                print(f"[OK]   {city['city']:<15} {c_start.date()} -> {c_end.date()}")
                ok += 1
            except (URLError, HTTPError) as e:
                print(f"[FAIL] {city['city']:<15} {c_start.date()} -> {c_end.date()} : {e}")
                failed += 1
            except Exception as e:
                print(f"[FAIL] {city['city']:<15} {c_start.date()} -> {c_end.date()} : {e}")
                failed += 1
            time.sleep(0.5)

    print(f"\nTerminé (backfill) : {ok} succès, {skipped} déjà présents, {failed} échec(s) sur {total} appels prévus.")


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extraction AQI (OpenWeatherMap)")
    parser.add_argument("--mode", choices=["current", "backfill"], required=True)
    parser.add_argument("--months", type=int, default=3, help="Backfill : nb de mois (défaut 3, mini imposé)")
    parser.add_argument("--start", type=str, help="Backfill : date de début YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="Backfill : date de fin YYYY-MM-DD")
    args = parser.parse_args()

    api_key = get_api_key()
    cities = load_cities()

    if args.mode == "current":
        run_current(cities, api_key)
    else:
        run_backfill(cities, api_key, args.months, args.start, args.end)


if __name__ == "__main__":
    main()
