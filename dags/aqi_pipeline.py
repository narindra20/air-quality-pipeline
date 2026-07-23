from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models import Variable

VILLES_CONFIG_PATH = Path("/opt/airflow/config/villes.json")

default_args = {
    "owner": "datacore",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="aqi_pipeline",
    description="Extraction horaire AQI (5 villes min.) -> clean/ -> data warehouse",
    schedule="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["aqi_pipeline"],
)
def aqi_pipeline():

    @task
    def get_villes() -> list[dict]:
        with open(VILLES_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)

    @task
    def extract_one_ville(ville: dict, execution_date=None) -> str:
        from scripts.extraction.extract_aqi import extract_city

        api_key = Variable.get("OPENWEATHER_API_KEY")
        return extract_city(
            ville=ville,
            api_key=api_key,
            execution_date=str(execution_date),
        )

    @task
    def build_clean(raw_files: list[str]) -> str:
        from scripts.stockage.build_clean import build_clean as _build_clean

        return _build_clean()

    @task
    def load_warehouse(clean_csv_path: str) -> None:
        from scripts.warehouse.load_warehouse import load_warehouse as _load_warehouse

        _load_warehouse(clean_csv_path)

    villes = get_villes()
    raw_files = extract_one_ville.expand(ville=villes)
    clean_path = build_clean(raw_files)
    load_warehouse(clean_path)


aqi_pipeline()