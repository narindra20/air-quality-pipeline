import os
import sys
import logging
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("load_warehouse")

DATABASE_URL = os.getenv("DATABASE_URL_WRITER")
DEFAULT_CLEAN_CSV_PATH = os.path.join("clean", "air_quality_clean.csv")


def get_db_connection() -> psycopg2.extensions.connection:
    if not DATABASE_URL:
        logger.error("Erreur : DATABASE_URL introuvable dans l'environnement / fichier .env.")
        sys.exit(1)
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.error(f"Erreur de connexion : {e}")
        sys.exit(1)


def load_warehouse(clean_csv_path: str = DEFAULT_CLEAN_CSV_PATH) -> None:
    logger.info("Début du chargement du Data Warehouse...")

    if not os.path.exists(clean_csv_path):
        logger.error(f"Fichier introuvable : {clean_csv_path}")
        sys.exit(1)

    logger.info(f"Lecture : {clean_csv_path}")
    df = pd.read_csv(clean_csv_path)

    if df.empty:
        logger.warning("Fichier vide. Fin du traitement.")
        return

    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        logger.info("Traitement de dim_city...")
        unique_cities = df[["city", "country", "lat", "lon"]].drop_duplicates()

        city_insert_query = """
                            INSERT INTO dim_city (city_name, country, latitude, longitude)
                            VALUES (%s, %s, %s, %s)
                                ON CONFLICT (city_name) DO UPDATE SET
                                latitude = EXCLUDED.latitude,
                                                               longitude = EXCLUDED.longitude; \
                            """
        cities_data = [
            (row["city"], row["country"], float(row["lat"]), float(row["lon"]))
            for _, row in unique_cities.iterrows()
        ]
        execute_batch(cursor, city_insert_query, cities_data)

        cursor.execute("SELECT city_name, city_id FROM dim_city;")
        city_map = {row[0]: row[1] for row in cursor.fetchall()}

        logger.info("Traitement de dim_time...")
        unique_timestamps = df["datetime_utc"].drop_duplicates()
        time_data = []

        for ts in unique_timestamps:
            time_id = ts.strftime("%Y-%m-%d-%H")
            time_data.append((
                time_id,
                ts.to_pydatetime(),
                ts.date(),
                ts.hour,
                ts.isoweekday(),
                ts.strftime("%A"),
                ts.month,
                ts.year,
                ts.isoweekday() >= 6,
            ))

        time_insert_query = """
                            INSERT INTO dim_time
                            (time_id, timestamp_utc, date_day, hour, day_of_week, day_name, month, year, is_weekend)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (time_id) DO NOTHING; \
                            """
        execute_batch(cursor, time_insert_query, time_data)


        logger.info("Traitement de fact_air_quality...")
        fact_data = []
        skipped = 0

        for _, row in df.iterrows():
            city_name = row["city"]
            if city_name not in city_map:
                skipped += 1
                continue

            city_id = city_map[city_name]
            time_id = row["datetime_utc"].strftime("%Y-%m-%d-%H")

            def safe_val(col: str):
                val = row.get(col, None)
                return float(val) if pd.notna(val) else None

            fact_data.append((
                city_id,
                time_id,
                safe_val("aqi"),
                safe_val("pm2_5"),
                safe_val("pm10"),
                safe_val("no2"),
                safe_val("o3"),
                safe_val("so2"),
                safe_val("co"),
            ))

        fact_insert_query = """
                            INSERT INTO fact_air_quality (city_id, time_id, aqi, pm2_5, pm10, no2, o3, so2, co)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (city_id, time_id) DO UPDATE SET
                                aqi = EXCLUDED.aqi,
                                                                      pm2_5 = EXCLUDED.pm2_5,
                                                                      pm10 = EXCLUDED.pm10,
                                                                      no2 = EXCLUDED.no2,
                                                                      o3 = EXCLUDED.o3,
                                                                      so2 = EXCLUDED.so2,
                                                                      co = EXCLUDED.co; \
                            """
        execute_batch(cursor, fact_insert_query, fact_data)

        conn.commit()
        logger.info("Data Warehouse chargé avec succès.")
        if skipped:
            logger.warning(f"{skipped} lignes ignorées (ville absente de dim_city, ne devrait pas arriver).")

        cursor.execute("SELECT COUNT(*) FROM fact_air_quality;")
        total_rows = cursor.fetchone()[0]
        logger.info(f"Total mesures en base : {total_rows} lignes.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors du chargement : {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    load_warehouse()