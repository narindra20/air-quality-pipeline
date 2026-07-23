import os
import psycopg2
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def test_connection():
    print("⏳ Test de connexion au Data Warehouse...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Requête de vérification
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print("✅ Connexion réussie à la base de données !")
        print(f"📌 Version PostgreSQL : {db_version[0]}")

        # Vérification des tables présentes
        cursor.execute("""
                       SELECT table_name
                       FROM information_schema.tables
                       WHERE table_schema = 'public';
                       """)
        tables = cursor.fetchall()
        print("📋 Tables trouvées dans la base :", [t[0] for t in tables])

        cursor.close()
        conn.close()
    except Exception as e:
        print("❌ Échec de la connexion au Data Warehouse.")
        print(f"Erreur : {e}")

if __name__ == "__main__":
    test_connection()