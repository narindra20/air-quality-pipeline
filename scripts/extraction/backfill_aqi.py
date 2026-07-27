from __future__ import annotations

import argparse
import json
import os
import time
from calendar import monthrange
from datetime import datetime, timezone
from pathlib import Path

import requests

RAW_DIR = Path("raw")
VILLES_CONFIG_PATH = Path("config/villes.json")
HISTORY_URL = "http://api.openweathermap.org/data/2.5/air_pollution/history"

OWM_HISTORY_START = datetime(2020, 11, 27, tzinfo=timezone.utc)
MAX_CALLS_PER_MIN = 55


def month_chunks(start: datetime, end: datetime):
    current = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while current < end:
        _, days_in_month = monthrange(current.year, current.month)
        chunk_end = current.replace(day=days_in_month, hour=23, minute=59, second=59)
        chunk_end = min(chunk_end, end)
        yield current, chunk_end
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)


def fetch_history(lat: float, lon: float, start: datetime, end: datetime, api_key: str) -> dict:
    params = {
        "lat": lat,
        "lon": lon,
        "start": int(start.timestamp()),
        "end": int(end.timestamp()),
        "appid": api_key,
    }
    resp = requests.get(HISTORY_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def save_raw(ville: dict, chunk_start: datetime, payload: dict) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{ville['ville']}_{chunk_start:%Y-%m}_history.json"
    path = RAW_DIR / filename
    wrapped = {
        "ville": ville["ville"],
        "pays": ville.get("pays"),
        "lat": ville["lat"],
        "lon": ville["lon"],
        "source_endpoint": "air_pollution/history",
        "api_response": payload,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(wrapped, f, ensure_ascii=False, indent=2)
    return path


def parse_period_args(args) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    if args.end:
        end = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    if args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        year, month = end.year, end.month - args.months
        while month <= 0:
            month += 12
            year -= 1
        start = end.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)

    start = max(start, OWM_HISTORY_START)
    return start, end


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=3)
    parser.add_argument("--start", type=str)
    parser.add_argument("--end", type=str)
    args = parser.parse_args()

    api_key = os.environ["OPENWEATHER_API_KEY"]
    start, end = parse_period_args(args)

    with open(VILLES_CONFIG_PATH, encoding="utf-8") as f:
        villes = json.load(f)

    calls_this_minute = 0
    minute_window_start = time.monotonic()
    total_calls = 0
    total_points = 0

    print(f"Backfill AQI : {len(villes)} ville(s), période {start:%Y-%m-%d} -> {end:%Y-%m-%d}\n")

    for ville in villes:
        for chunk_start, chunk_end in month_chunks(start, end):
            if calls_this_minute >= MAX_CALLS_PER_MIN:
                elapsed = time.monotonic() - minute_window_start
                if elapsed < 60:
                    time.sleep(60 - elapsed)
                calls_this_minute = 0
                minute_window_start = time.monotonic()

            print(f"[{ville['ville']}] {chunk_start:%Y-%m} ...", end=" ", flush=True)
            try:
                payload = fetch_history(
                    lat=ville["lat"],
                    lon=ville["lon"],
                    start=chunk_start,
                    end=chunk_end,
                    api_key=api_key,
                )
                path = save_raw(ville, chunk_start, payload)
                n_points = len(payload.get("list", []))
                total_points += n_points
                print(f"OK -> {path.name} ({n_points} points)")
            except requests.HTTPError as exc:
                print(f"ERREUR: {exc}")

            calls_this_minute += 1
            total_calls += 1

    print(f"\nTerminé : {total_calls} appels API, {total_points} points horaires récupérés au total.")
    print("Prochaine étape : lancer scripts/stockage/build_clean.py pour reconstruire clean/ à partir de raw/.")


if __name__ == "__main__":
    main()