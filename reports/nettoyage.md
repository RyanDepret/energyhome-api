# Nettoyage des DPE PACA

Généré par `training/nettoyer.py`. Entrée : `data/dpe_r93_brut.parquet`
(extraction du 2026-10-31T19:53:21+00:00, 1 226 609 lignes, SHA-256 `956077421b096bd5eb8c47d6ab90dbbbdcc6c737e52654a89bb298b1186267be`).
Sortie : `data/dpe_paca.parquet`, **1 225 576 lignes** (99.92 % du brut).

Périmètre de l'extraction : `code_region_ban:93 AND type_batiment:(maison OR appartement)`.
Dates d'établissement après nettoyage : du 2021-07-01 au 2026-10-26.

## Étapes

Appliquées dans cet ordre ; chaque ligne part du résultat de la précédente.

| Étape | Avant | Après | Retirées | Détail |
|---|---:|---:|---:|---|
| Dédoublonnage par numero_dpe | 1 226 609 | 1 226 609 | 0 | sans_identifiant : 0, doublons_identifiant : 0 |
| DPE remplacés (ne garder que le plus récent) | 1 226 609 | 1 226 599 | 10 | avec_numero_dpe_remplace : 89 737, paires_presentes : 10, remplace_plus_recent_que_remplacant : 0, lignes_retirees : 10 |
| Étiquette DPE manquante ou hors A–G | 1 226 599 | 1 226 599 | 0 | manquante : 0, hors_A_G : 0, valeurs_hors_A_G : {} |
| Surface absente, < 9 m² ou > 1000 m² | 1 226 599 | 1 225 576 | 1 023 | absente : 306, inferieure_a_9 : 556, superieure_a_1000 : 161 |

Règles :
- dédoublonnage **par identifiant** (`numero_dpe`), jamais par contenu ; en cas de doublon, on garde la version
  dont `date_derniere_modification_dpe` est la plus récente ;
- DPE remplacés : `avec_numero_dpe_remplace` compte les DPE qui en remplacent un autre ; la plupart des DPE
  remplacés ne sont déjà plus dans le jeu ADEME, seules les `paires_presentes` sont traitées ici. Quand un DPE et celui qu'il remplace (`numero_dpe_remplace`) sont tous deux présents, on ne garde
  que celui dont `date_etablissement_dpe` est la plus récente (à date égale, le remplaçant) ;
- surface : bornes 9–1000 m², identiques à la validation de `/predict`.

## Valeurs inconnues du modèle actuel

Comptées sur le jeu nettoyé, **non supprimées** (1 800 valeurs au total).
- Chauffage, période ou type de bâtiment inconnus : l'API refuse ces logements ; `training/evaluer.py` les exclut
  du test en les comptant.
- `zone_climatique` : sans effet sur l'évaluation, car l'API (comme `training/evaluer.py`) déduit la zone du
  département et n'utilise pas ce champ.

- `periode_construction` : aucune valeur inconnue
- `type_batiment` : aucune valeur inconnue
- `type_energie_principale_chauffage` (503 lignes) :
  - `Bois – Plaquettes forestières` : 402
  - `Charbon` : 59
  - `Butane` : 42
- `zone_climatique` (1 297 lignes) :
  - `(manquant)` : 1 297

## Répartition des classes DPE (PACA, jeu nettoyé)

| Classe | Effectif | Part |
|---|---:|---:|
| A | 43 903 | 3.58 % |
| B | 137 782 | 11.24 % |
| C | 520 553 | 42.47 % |
| D | 315 336 | 25.73 % |
| E | 138 236 | 11.28 % |
| F | 48 360 | 3.95 % |
| G | 21 406 | 1.75 % |
| **Total** | **1 225 576** | 100 % |
