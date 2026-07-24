# clean/ — Donnees propres (contrat de donnees)

Un seul fichier : `air_quality_clean.csv`, **entierement reconstruit a
chaque execution** de `scripts/stockage/build_clean.py` a partir de `raw/`.

## Generation

```bash
python scripts/stockage/build_clean.py
```

## Contrat de donnees — `air_quality_clean.csv`

Une ligne = une (ville, heure). Triee chronologiquement. Sans doublon.

| Colonne | Type | Unite / format | Description |
|---|---|---|---|
| `city` | string | — | Nom de la ville |
| `country` | string | nom complet | Pays (ex. "France") |
| `lat` | float | degres decimaux | Latitude |
| `lon` | float | degres decimaux | Longitude |
| `timestamp` | int | Unix timestamp (UTC) | Horodatage de la mesure |
| `aqi` | int | **echelle OpenWeatherMap 1-5** (1=Good ... 5=Very Poor) | Attention : ce n'est PAS l'echelle US EPA 0-500 |
| `co` | float | µg/m3 | Monoxyde de carbone |
| `no` | float | µg/m3 | Monoxyde d'azote |
| `no2` | float | µg/m3 | Dioxyde d'azote |
| `o3` | float | µg/m3 | Ozone |
| `so2` | float | µg/m3 | Dioxyde de soufre |
| `pm2_5` | float | µg/m3 | Particules fines < 2.5 µm |
| `pm10` | float | µg/m3 | Particules fines < 10 µm |
| `nh3` | float | µg/m3 | Ammoniac |

## Periode couverte / trous connus

A completer apres le backfill complet des 5 nouvelles villes.

## Interface avec le warehouse

Ce fichier est la seule entree attendue par `scripts/warehouse/load_warehouse.py`.
