# clean/ — Données propres (contrat de données)

Un seul fichier : `air_quality_clean.csv`, **entièrement reconstruit à
chaque exécution** de `scripts/stockage/build_clean.py` à partir de `raw/`.
Aucun mode append : donc aucun risque de doublon résiduel.

## Génération

```bash
python scripts/stockage/build_clean.py
```

Le script relit tous les fichiers de `raw/`, dédoublonne sur la clé
(ville, heure), trie chronologiquement (ville puis horodatage), et régénère
`clean/air_quality_clean.csv` en entier.

## Contrat de données — `air_quality_clean.csv`

Une ligne = une (ville, heure). Triée chronologiquement. Sans doublon.

| Colonne | Type | Unité / format | Description |
|---|---|---|---|
| `city` | string | — | Nom de la ville |
| `country` | string | code ISO 3166-1 alpha-2 | Pays |
| `latitude` | float | degrés décimaux | Latitude du point de mesure |
| `longitude` | float | degrés décimaux | Longitude du point de mesure |
| `timestamp_utc` | string | ISO 8601, UTC | Horodatage de la mesure |
| `aqi` | int | **échelle OpenWeatherMap 1–5** (1=Good … 5=Very Poor) | ⚠️ Ce n'est PAS l'échelle US EPA 0–500. Ne pas confondre. |
| `co` | float | µg/m³ | Monoxyde de carbone |
| `no` | float | µg/m³ | Monoxyde d'azote |
| `no2` | float | µg/m³ | Dioxyde d'azote |
| `o3` | float | µg/m³ | Ozone |
| `so2` | float | µg/m³ | Dioxyde de soufre |
| `pm2_5` | float | µg/m³ | Particules fines < 2.5 µm |
| `pm10` | float | µg/m³ | Particules fines < 10 µm |
| `nh3` | float | µg/m³ | Ammoniac |

Toutes les valeurs de polluants proviennent telles quelles du champ
`components` de la réponse OpenWeatherMap (déjà en µg/m³, aucune conversion
appliquée).

## Période couverte / trous connus

À compléter par le groupe après le premier backfill complet : date de
début, date de fin, éventuels trous par ville (panne API, ville ajoutée en
cours de route, etc.).

## Interface avec le warehouse

Ce fichier est la seule entrée attendue par
`scripts/warehouse/load_warehouse.py`. Toute évolution de colonnes/unités
ci-dessus doit être communiquée au groupe avant modification, pour ne pas
casser le chargement en aval.
