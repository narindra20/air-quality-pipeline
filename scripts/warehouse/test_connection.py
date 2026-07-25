
import os
import sys
import logging
import psycopg2
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_connection")

DATABASE_URL = os.getenv("DATABASE_URL")


def test_connection() -> None:
    logger.info("Test de connexion au Data Warehouse...")

    if not DATABASE_URL:
        logger.error("DATABASE_URL introuvable dans l'environnement / fichier .env.")
        sys.exit(1)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        logger.info("Connexion réussie à la base de données.")
        logger.info(f"Version PostgreSQL : {db_version[0]}")

        cursor.execute("""
                       SELECT table_name
                       FROM information_schema.tables
                       WHERE table_schema = 'public';
                       """)
        tables = cursor.fetchall()
        logger.info(f"Tables trouvées dans la base : {[t[0] for t in tables]}")

        expected = {"dim_city", "dim_time", "fact_air_quality"}
        found = {t[0] for t in tables}
        missing = expected - found
        if missing:
            logger.warning(f"Tables manquantes, exécutez le script de création de schéma : {missing}")
        else:
            logger.info("Toutes les tables attendues (dim_city, dim_time, fact_air_quality) sont présentes.")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error("Échec de la connexion au Data Warehouse.")
        logger.error(f"Erreur : {e}")
        sys.exit(1)


if _name_ == "_main_":
    test_connection()