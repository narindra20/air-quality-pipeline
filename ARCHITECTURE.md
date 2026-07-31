# ARCHITECTURE.md

## Vue d'ensemble

OpenWeather Air Pollution API (5 villes : Paris, Lyon, Marseille, Toulouse, Nice)
        │  collecte horaire + backfill
        ▼
ORCHESTRATEUR : Apache Airflow (exécuté via Docker Compose, déclenché par GitHub Actions)
        ▼
STOCKAGE (fichiers versionnés dans le repo Git)
  raw/    fichiers JSON bruts, un par ville et par heure, jamais modifiés
  clean/  un seul fichier CSV, reconstruit à chaque run depuis raw/
        ▼
DATA WAREHOUSE : PostgreSQL (Neon, serverless)
  fact_air_quality + dim_city + dim_time (schéma en étoile)

## Stack choisie et justifications

### Orchestrateur : Apache Airflow (via Docker Compose) + GitHub Actions

*Choix :* Un DAG Airflow (aqi_pipeline) définit et enchaîne les tâches (récupération des villes, extraction par ville, construction du clean, chargement du warehouse). Ce DAG est packagé dans une stack Docker Compose (Airflow + Postgres interne). Le déclenchement automatique et récurrent est délégué à un workflow *GitHub Actions* planifié (cron: '17 * * * *'), qui démarre la stack Docker à chaque run, exécute le DAG via airflow dags test, puis détruit l'environnement.

*Justification :* Un scheduler Airflow classique nécessite un serveur qui reste allumé 24/7, ce qu'un groupe d'étudiants sans infrastructure dédiée ne peut pas garantir de façon fiable. GitHub Actions fournit des runners cloud gratuits capables d'exécuter Docker nativement, avec un cron intégré — combiné à Airflow pour la structuration/lisibilité du pipeline (tâches, dépendances, retries, logs), cela donne une automatisation réellement continue et vérifiable (historique des runs consultable dans l'onglet Actions), sans dépendre d'une machine physique allumée en permanence.

Un service pipeline (profile Docker Compose manual) est aussi défini pour lancer la chaîne extraction → clean → warehouse en local, à la main, sans passer par Airflow — utile pour du débogage rapide.

### Stockage brut et propre : fichiers versionnés dans le dépôt Git

*Choix :* raw/ contient un fichier JSON par ville et par heure d'extraction (raw/ville=<Ville>/<année>/<mois>/<jour>/<heure>/raw_<date>_<heure>.json), jamais modifié après écriture. clean/ contient un unique fichier air_quality_clean.csv, entièrement reconstruit à chaque run à partir de l'ensemble des fichiers raw/, dédupliqué sur (ville, heure).

Deux formats de fichiers raw/ coexistent, selon la source : un fichier par (ville, heure) pour l'extraction courante horaire, et un fichier par (ville, mois) pour le backfill historique (raw/<Ville>_<année-mois>_history.json, contenant plusieurs points horaires par fichier car l'endpoint /air_pollution/history renvoie une plage complète en un seul appel). Le script build_clean.py détecte et normalise automatiquement les deux formats vers le même schéma clean/.

*Justification :* Conserver les fichiers bruts tels que reçus de l'API constitue la sauvegarde de référence (source de vérité, rejouable), conformément à la consigne du sujet. Le format JSON préserve fidèlement la réponse de l'API, tandis que le CSV clean/ offre un contrat de données unique et simple à consommer pour le cours IA1. Ces fichiers sont commités automatiquement par le pipeline à chaque run (utilisateur bot dédié aqi-bot), ce qui rend leur contenu directement vérifiable dans l'historique du dépôt sans dépendance à un service tiers.

### Data Warehouse : PostgreSQL sur Neon (serverless)

*Choix :* Une base Postgres hébergée sur Neon, modélisée en schéma en étoile : fact_air_quality (mesures AQI et polluants, clés vers les dimensions) + dim_city (nom, pays, latitude, longitude) + dim_time (date, heure, jour de semaine, week-end). Le chargement est effectué par load_warehouse.py, rejouable et idempotent, à partir de clean/.

*Justification :* Neon offre une base Postgres managée, gratuite pour ce volume de données, accessible depuis n'importe où (y compris les runners GitHub Actions éphémères) sans configuration réseau complexe, contrairement à une base auto-hébergée qui nécessiterait un serveur permanent. Le schéma en étoile respecte les règles de modélisation dimensionnelle du cours (pas de mesures dans les dimensions, pas de colonnes descriptives dans la table de faits) et permet des requêtes analytiques simples pour le cours IA1.

### Sécurité des identifiants

*Choix :* Toutes les clés (API OpenWeather, chaînes de connexion Neon) sont stockées en tant que secrets GitHub Actions (OPENWEATHER_API_KEY, NEON_DATABASE_URL, NEON_DATABASE_URL_WRITER), jamais committées dans le code ni l'historique Git. Le format attendu localement est documenté dans .env.example (sans valeurs réelles).

La base expose deux rôles Postgres distincts en plus du rôle propriétaire Neon (neondb_owner, usage interne/vérifications) : dw_writer (droits complets sur les tables, utilisé exclusivement par le pipeline pour charger le warehouse) et ia1_reader (lecture seule, destiné à la consommation des données par le cours IA1). Cette séparation limite l'exposition en écriture au strict nécessaire.

*Justification :* Conforme à l'exigence du sujet ("clé API en secret, jamais dans le code ni l'historique Git"), et permet une rotation des identifiants sans modification du code. La séparation des rôles writer/reader applique le principe du moindre privilège : un accès en lecture pour un consommateur externe (IA1) ne peut jamais accidentellement corrompre les données.

## Diagramme des composants

| Composant | Rôle | Technologie |
|---|---|---|
| Extraction | Appelle l'API OpenWeather Air Pollution pour chaque ville | Python (extract_aqi.py, backfill_aqi.py) |
| Orchestration | Enchaîne extraction → clean → warehouse, gère les dépendances et retries | Apache Airflow (DAG aqi_pipeline) |
| Exécution automatisée | Démarre la stack Docker et déclenche le DAG toutes les heures | GitHub Actions (deploy.yml) |
| Backfill historique | Récupère l'historique mensuel par ville, à la demande | GitHub Actions (backfill.yml), appelle directement backfill_aqi.py → build_clean.py → load_warehouse.py (sans passer par un DAG Airflow dédié) |
| Stockage brut | Sauvegarde immuable, un fichier par (ville, heure) ou (ville, mois) | JSON dans raw/ (Git) |
| Stockage propre | Fichier unique, dédupliqué, reconstruit à chaque run | CSV dans clean/ (Git) |
| Data Warehouse | Modélisation dimensionnelle pour analyse | PostgreSQL (Neon) |

## Limites connues

- *Période couverte* : du 2026-04-01 au 2026-07-30 (~4 mois), au-delà du minimum de 3 mois requis.
- *Couverture horaire* : 14 030 lignes sur 14 465 attendues (5 villes × 2893 heures), soit 3,01 % de 
  lignes manquantes au global. Le taux est identique pour les 5 villes (135 heures manquantes chacune, 
  4,67 % par ville) — cette homogénéité confirme que les trous proviennent de runs GitHub Actions 
  entiers non exécutés, plutôt que d'erreurs API isolées à une ville.
- *Cause* : GitHub Actions ne garantit pas l'exactitude temporelle des workflows planifiés (schedule:) ;
  sous forte charge de l'infrastructure GitHub, certains runs horaires peuvent être retardés ou sautés 
  entièrement. Comportement documenté par GitHub, combiné à notre concurrency: cancel-in-progress: false 
  qui empêche plusieurs runs simultanés.
- *Mitigation* : le pipeline de backfill (AQI Backfill Pipeline, workflow_dispatch) permet de 
  relancer une collecte historique et de reconstruire clean/ depuis raw/, comblant les trous 
  identifiés a posteriori.