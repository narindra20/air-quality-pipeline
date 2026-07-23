# raw/ — Donnees brutes (Data Lake)

Zone **intouchable** : aucun fichier ici n'est jamais modifie apres ecriture.
C'est la sauvegarde de reference. Tout le contenu de `clean/` est
reconstructible a partir de ce dossier.

## Villes suivies

| Ville | Pays | Latitude | Longitude |
|---|---|---|---|
| Paris | France | 48.8566 | 2.3522 |
| Marseille | France | 43.2965 | 5.3698 |
| Lyon | France | 45.7640 | 4.8357 |
| Toulouse | France | 43.6047 | 1.4442 |
| Nice | France | 43.7102 | 7.2620 |

Source : [OpenWeatherMap Air Pollution API](https://openweathermap.org/api/air-pollution)
(current + history endpoints).

## Convention de nommage

Un fichier = une mesure horaire.

```
data/raw/ville=<Nom>/<annee>/<mois>/<jour>/<heure>/raw_<YYYYMMDD_HH>.json
```

Exemple :
```
data/raw/ville=Paris/2026/07/21/14/raw_20260721_14.json
```

## Contenu d'un fichier

```json
{
  "city": "Paris",
  "country": "France",
  "lat": 48.8566,
  "lon": 2.3522,
  "timestamp": 1753113600,
  "aqi": 2,
  "components": {
    "co": 200.1, "no": 0.1, "no2": 10.2, "o3": 50.5,
    "so2": 1.1, "pm2_5": 8.3, "pm10": 12.1, "nh3": 0.5
  }
}
```

## Comment ces fichiers sont generes

Par `scripts/extraction/extract_aqi.py`, a partir de `config/villes.json` :

```bash
export OPENWEATHER_API_KEY="votre_cle"
python scripts/extraction/extract_aqi.py --mode current    # une collecte "maintenant"
python scripts/extraction/extract_aqi.py --mode backfill   # historique (3 mois)
```

La cle API n'est jamais ecrite dans le code : lue depuis la variable
d'environnement `OPENWEATHER_API_KEY` (via `.env` local, exclu du Git).

## Periode couverte / trous connus

A completer par le groupe apres le backfill complet des 5 nouvelles villes
(date de debut, date de fin, eventuels trous).
