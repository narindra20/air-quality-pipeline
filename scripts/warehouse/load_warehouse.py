import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CLEAN_CSV_PATH = os.path.join("clean", "clean_air_quality.csv")


def get_db_connection():
    """Établit la connexion à la base de données Neon PostgreSQL."""
    if not DATABASE_URL:
        print("❌ Erreur : La variable d'environnement DATABASE_URL est introuvable.")
        sys.exit(1)
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ Erreur lors de la connexion à la base de données : {e}")
        sys.exit(1)


def load_warehouse():
    print("🚀 Début du chargement du Data Warehouse...")

    # 1. Vérification de l'existence du fichier clean/
    if not os.path.exists(CLEAN_CSV_PATH):
        print(f"⚠️ Fichier source introuvable : {CLEAN_CSV_PATH}")
        sys.exit(1)

    print(f"📂 Lecture du fichier : {CLEAN_CSV_PATH}")
    df = pd.read_csv(CLEAN_CSV_PATH)

    if df.empty:
        print("⚠️ Le fichier clean_air_quality.csv est vide. Fin du traitement.")
        return

    # Normalisation de l'horodatage en UTC
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # -------------------------------------------------------------
        # 2. ALIMENTATION / RECUPERATION DE LA DIMENSION VILLE (dim_city)
        # -------------------------------------------------------------
        print("🏙️ Traitement de dim_city...")
        unique_cities = df[['ville', 'latitude', 'longitude']].drop_duplicates()

        city_insert_query = """
                            INSERT INTO dim_city (city_name, country, latitude, longitude)
                            VALUES (%s, %s, %s, %s)
                                ON CONFLICT (city_name) DO UPDATE SET
                                latitude = EXCLUDED.latitude,
                                                               longitude = EXCLUDED.longitude; \
                            """

        # Par défaut 'France', ajustable si vous avez d'autres pays
        cities_data = [
            (row['ville'], 'France', float(row['latitude']), float(row['longitude']))
            for _, row in unique_cities.iterrows()
        ]
        execute_batch(cursor, city_insert_query, cities_data)

        # Récupération de la table de correspondance city_name -> city_id
        cursor.execute("SELECT city_name, city_id FROM dim_city;")
        city_map = {row[0]: row[1] for row in cursor.fetchall()}

        # -------------------------------------------------------------
        # 3. ALIMENTATION REJOUABLE DE LA DIMENSION TEMPS (dim_time)
        # -------------------------------------------------------------
        print("⏰ Traitement de dim_time...")
        unique_timestamps = df['timestamp'].drop_duplicates()

        time_data = []
        for ts in unique_timestamps:
            time_id = ts.strftime("%Y-%m-%d-%H")
            date_day = ts.date()
            hour = ts.hour
            day_of_week = ts.isoweekday()  # 1 = Lundi, 7 = Dimanche
            day_name = ts.strftime("%A")
            month = ts.month
            year = ts.year
            is_weekend = day_of_week >= 6

            time_data.append((
                time_id,
                ts.to_pydatetime(),
                date_day,
                hour,
                day_of_week,
                day_name,
                month,
                year,
                is_weekend
            ))

        time_insert_query = """
                            INSERT INTO dim_time (time_id, timestamp_utc, date_day, hour, day_of_week, day_name, month, year, is_weekend)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (time_id) DO NOTHING; \
                            """
        execute_batch(cursor, time_insert_query, time_data)

        # -------------------------------------------------------------
        # 4. ALIMENTATION REJOUABLE DE LA TABLE DE FAITS (fact_air_quality)
        # -------------------------------------------------------------
        print("📊 Traitement de fact_air_quality...")
        fact_data = []

        for _, row in df.iterrows():
            city_name = row['ville']
            if city_name not in city_map:
                continue

            city_id = city_map[city_name]
            time_id = row['timestamp'].strftime("%Y-%m-%d-%H")

            # Extraction sécurisée des métriques avec conversion NaN/None -> NULL SQL
            def safe_val(col):
                val = row.get(col, None)
                return float(val) if pd.notna(val) else None

            aqi = safe_val('aqi')
            pm2_5 = safe_val('pm2_5')
            pm10 = safe_val('pm10')
            no2 = safe_val('no2')
            o3 = safe_val('o3')
            so2 = safe_val('so2')
            co = safe_val('co')

            fact_data.append((city_id, time_id, aqi, pm2_5, pm10, no2, o3, so2, co))

        # Utilisation de ON CONFLICT ... DO UPDATE pour rendre l'insertion rejouable (UPSERT)
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

        # Validation de la transaction
        conn.commit()
        print("✅ Data Warehouse mis à jour et rechargé avec succès !")

        # Affichage du nombre total de lignes dans la table de faits
        cursor.execute("SELECT COUNT(*) FROM fact_air_quality;")
        total_rows = cursor.fetchone()[0]
        print(f"📈 Total de mesures stockées dans fact_air_quality : {total_rows} lignes.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors du chargement dans la base : {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    load_warehouse()