# raw/ — Données brutes (Data Lake)

Zone **intouchable** : aucun fichier ici n'est jamais modifié après écriture.
C'est la sauvegarde de référence. Tout le contenu de `clean/` est
reconstructible à partir de ce dossier.

## Convention de nommage

Un fichier = un appel API = une ville.

```
raw/<slug_ville>/<slug_ville>_<timestamp>.json              # collecte horaire
raw/<slug_ville>/<slug_ville>_backfill_<start>_<end>.json   # backfill historique
```

Exemple :
```
raw/paris/paris_20260718T140000Z.json
raw/paris/paris_backfill_20260401T000000Z_20260408T000000Z.json
```

## Contenu d'un fichier

Chaque fichier JSON contient les métadonnées de l'appel (ville, coordonnées,
date de récupération, source) + la réponse brute de l'API OpenWeatherMap Air
Pollution, sans aucune transformation.

## Comment ces fichiers sont générés

Par `scripts/extraction/extract_aqi.py` :

```bash
export OWM_API_KEY="votre_cle"
python scripts/extraction/extract_aqi.py --mode current            # une collecte "maintenant"
python scripts/extraction/extract_aqi.py --mode backfill --months 3  # historique (3 mois mini)
```

Le script est rejouable sans risque : en mode `backfill`, il saute les
tranches déjà présentes sur disque (pas de doublon, pas d'appel API
inutile).

## Villes suivies

| Ville | Pays | Latitude | Longitude |
|---|---|---|---|
| Antananarivo | MG | -18.8792 | 47.5079 |
| Paris | FR | 48.8566 | 2.3522 |
| New Delhi | IN | 28.6139 | 77.2090 |
| Beijing | CN | 39.9042 | 116.4074 |
| Sao Paulo | BR | -23.5505 | -46.6333 |
