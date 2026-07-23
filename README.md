## 🗄️ Data Warehouse (Neon PostgreSQL)

### Schéma de Modélisation (Modèle en Étoile)
- **`dim_city`** : Attributs géographiques (`city_id`, `city_name`, `country`, `latitude`, `longitude`).
- **`dim_time`** : Grain temporel horaire (`time_id`, `timestamp_utc`, `date_day`, `hour`, `day_of_week`, `day_name`, `month`, `year`, `is_weekend`).
- **`fact_air_quality`** : Mesures quantitatives de la qualité de l'air (`aqi`, `pm2_5`, `pm10`, `no2`, `o3`, `so2`, `co`).

### Accès au Data Warehouse (Lecture seule pour IA1)
- **Host / URI :** `postgresql://reader:ia1_read_only_password@ep-xyz.region.aws.neon.tech/neondb?sslmode=require`
- **Engine :** PostgreSQL 15+ (Serverless Neon)