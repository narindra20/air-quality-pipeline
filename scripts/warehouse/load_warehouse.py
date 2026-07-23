import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

# Charger les variables d'environnement (Database URL de Neon)
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

CLEAN_CSV_PATH = "clean/clean_air_quality.csv"

def connect_db():
    return psycopg2.connect(DATABASE_URL)

def load_warehouse():
    if not os.path.exists(CLEAN_CSV_PATH):
        print(f"Fichier {CLEAN_CSV_PATH} introuvable.")
        return

    df = pd.read_csv(CLEAN_CSV_PATH)

    # Validation du format d'horodatage
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    conn = connect_db()
    cursor = conn.cursor()

    # 1. Récupérer le mapping city_name -> city_id
    cursor.execute("SELECT city_name, city_id FROM dim_city;")
    city_map = {row[0]: row[1] for row in cursor.fetchall()}

    # 2. Préparer et insérer les données de la dimension Temps (dim_time)
    time_data = []
    seen_time_ids = set()

    for ts in df['timestamp'].unique():
        ts = pd.to_datetime(ts)
        time_id = ts.strftime("%Y-%m-%d-%H")
        if time_id not in seen_time_ids:
            seen_time_ids.add(time_id)
            time_data.append((
                time_id,
                ts.to_pydatetime(),
                ts.date(),
                ts.hour,
                ts.dayofweek + 1,
                ts.strftime("%A"),
                ts.month,
                ts.year,
                ts.dayofweek >= 5
            ))

    query_dim_time = """
                     INSERT INTO dim_time (time_id, timestamp_utc, date_day, hour, day_of_week, day_name, month, year, is_weekend)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                         ON CONFLICT (time_id) DO NOTHING; \
                     """
    execute_batch(cursor, query_dim_time, time_data)

    # 3. Préparer et insérer la table de faits (fact_air_quality)
    fact_data = []
    for _, row in df.iterrows():
        city_name = row['ville']
        if city_name not in city_map:
            continue

        city_id = city_map[city_name]
        time_id = row['timestamp'].strftime("%Y-%m-%d-%H")

        # Récupération sécurisée des métriques (avec None/NULL par défaut)
        aqi = row.get('aqi', None)
        pm2_5 = row.get('pm2_5', None)
        pm10 = row.get('pm10', None)
        no2 = row.get('no2', None)
        o3 = row.get('o3', None)
        so2 = row.get('so2', None)
        co = row.get('co', None)

        fact_data.append((city_id, time_id, aqi, pm2_5, pm10, no2, o3, so2, co))

    query_fact = """
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
    execute_batch(cursor, query_fact, fact_data)

    conn.commit()
    cursor.close()
    conn.close()
    print("Entrepôt de données (Warehouse) chargé avec succès.")

if __name__ == "__main__":
    load_warehouse()