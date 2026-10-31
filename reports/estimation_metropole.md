# Estimation d'une extraction France métropolitaine (sans téléchargement)

Généré par `training/telecharger_dpe.py --metropole` le 2026-10-31T20:26:27+00:00.
Source : `https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant` (données mises à jour le 2026-10-28T20:13:07.863Z).
Périmètre : maisons et appartements des 13 régions métropolitaines (Corse comprise, DOM exclus).

## Volume

- Requête de comptage : `code_region_ban:(11 OR 24 OR 27 OR 28 OR 32 OR 44 OR 52 OR 53 OR 75 OR 76 OR 84 OR 93 OR 94) AND type_batiment:(maison OR appartement)`
- **14 934 380 lignes** (somme par région : 14 934 380 ; écart : 0)

| Code | Région | DPE maisons + appartements |
|---|---|---:|
| 11 | Île-de-France | 3 297 010 |
| 24 | Centre-Val de Loire | 576 076 |
| 27 | Bourgogne-Franche-Comté | 568 291 |
| 28 | Normandie | 807 197 |
| 32 | Hauts-de-France | 1 275 879 |
| 44 | Grand Est | 1 249 757 |
| 52 | Pays de la Loire | 820 545 |
| 53 | Bretagne | 672 325 |
| 75 | Nouvelle-Aquitaine | 1 302 867 |
| 76 | Occitanie | 1 287 997 |
| 84 | Auvergne-Rhône-Alpes | 1 796 954 |
| 93 | Provence-Alpes-Côte d'Azur | 1 226 609 |
| 94 | Corse | 52 873 |

## Taille et durée estimées par l'API

Mesures de référence : extraction de la région 93 (1 226 609 lignes, 123 pages).

| | Valeur |
|---|---:|
| Pages de 10 000 lignes | 1 494 |
| Octets JSON reçus par ligne (mesurés) | 688 |
| Octets Parquet par ligne (mesurés) | 35 |
| Volume JSON à transférer | 10.27 Go |
| Fichier Parquet final | 0.53 Go |
| Secondes par page (mesurées) | 13.01 |
| Durée estimée (débit mesuré + pause de 0.5 s) | 5 h 36 min |
| Durée minimale imposée par la limite de 600 req/min | 0 h 02 min |

## Export complet disponible ?

data.ademe.fr :
- jeu virtuel : True
- fichier source : None ; fichier original : None ; fichiers de données stockés : []
- `GET /full` : HTTP 404
- `GET /data-files` : []

data.gouv.fr (fiche « DPE Logements existants (depuis juillet 2021) », HTTP 200) :
- Consultez les données — format `url` — https://data.ademe.fr/datasets/dpe03existant
- Description des champs — format `url` — https://data.ademe.fr/datasets/dpe03existant

Exports complets (CSV/Parquet) trouvés :
- aucun

## Conclusion

Aucun export complet (CSV ou Parquet) n'a été trouvé sur data.ademe.fr ni sur data.gouv.fr : le jeu est servi uniquement par l'API. L'extraction métropole par l'API reste faisable avec le même script (1 494 pages, durée estimée 5 h 36 min, reprise possible), de préférence région par région pour limiter la perte en cas de coupure.
