# Modèle v3 : évaluation finale sur le test temporel

Généré par `training/evaluer_v3.py` le 2026-11-01T09:28:24+00:00.
Modèle : LightGBM {'num_leaves': 63, 'learning_rate': 0.1, 'min_child_samples': 500} ; localisation : departement ; calibration : isotonique.

## Verdict

Le modèle v3 **bat** « toujours C » en accuracy (50.8 % contre 42.2 %), **bat** cette référence à une classe près (89.3 % contre 79.7 %), **bat** le tirage aléatoire (50.8 % contre 27.3 %) et **bat** la répartition constante en score de Brier (0.6144 contre 0.7306).

## Jeu de test

- Exactement le test de `reports/reference_v1.md` : DPE PACA établis après le 2026-08-30 (du 2026-08-31 au 2026-10-26), mêmes exclusions : **32 813 DPE**, étiquette réelle `etiquette_dpe`.
- Vérifié par le script : effectif, exclusions, répartition des classes et métriques des références identiques à `reference_v1.json`.
- Le test n'a servi à aucun choix (modèle, réglages, calibration : validation du 2026-05-01 au 2026-08-30).
- Probabilités calculées avec le code de l'API (`app/ml/modele_v3.py`), calibration comprise.

## Tous les logements (32 813 DPE)

Le modèle v3 **bat** « toujours C » en accuracy (50.8 % contre 42.2 %), **bat** cette référence à une classe près (89.3 % contre 79.7 %), **bat** le tirage aléatoire (50.8 % contre 27.3 %) et **bat** la répartition constante en score de Brier (0.6144 contre 0.7306).

| | Modèle v3 | Modèle v1 (actuel) | Classe majoritaire | Aléatoire selon la répartition |
|---|---:|---:|---:|---:|
| Accuracy | 50.8 % | 30.6 % | 42.2 % | 27.3 % |
| F1 macro | 35.1 % | 28.8 % | 8.5 % | 14.3 % |
| Accuracy à une classe près | 89.3 % | 64.9 % | 79.7 % | 66.3 % |
| Brier multiclasse | 0.6144 | 0.7574 | — | 0.7306 (répartition constante) |
| F1 classe A | 0.600 | 0.547 | 0.000 | 0.045 |
| F1 classe B | 0.231 | 0.324 | 0.000 | 0.112 |
| F1 classe C | 0.645 | 0.352 | 0.594 | 0.427 |
| F1 classe D | 0.429 | 0.336 | 0.000 | 0.248 |
| F1 classe E | 0.132 | 0.254 | 0.000 | 0.114 |
| F1 classe F | 0.178 | 0.074 | 0.000 | 0.038 |
| F1 classe G | 0.240 | 0.125 | 0.000 | 0.018 |

Fiabilité des probabilités du v3 :

| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |
|---|---:|---:|---:|
| 0–10 % | 0 | — | — |
| 10–20 % | 0 | — | — |
| 20–30 % | 885 | 28.8 % | 29.5 % |
| 30–40 % | 8 833 | 35.8 % | 39.4 % |
| 40–50 % | 10 422 | 45.0 % | 46.4 % |
| 50–60 % | 6 078 | 54.6 % | 53.3 % |
| 60–70 % | 3 360 | 64.0 % | 63.1 % |
| 70–80 % | 1 626 | 74.8 % | 77.8 % |
| 80–90 % | 1 306 | 85.6 % | 89.9 % |
| 90–100 % | 303 | 91.7 % | 94.1 % |

Matrice de confusion du v3 :

| Réel ↓ / Prédit → | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 971 | 341 | 284 | 5 | 0 | 0 | 0 |
| **B** | 526 | 651 | 2 871 | 184 | 13 | 0 | 0 |
| **C** | 134 | 364 | 11 112 | 2 165 | 59 | 7 | 11 |
| **D** | 7 | 24 | 4 330 | 3 446 | 190 | 50 | 22 |
| **E** | 0 | 0 | 1 430 | 1 572 | 269 | 102 | 32 |
| **F** | 0 | 0 | 460 | 491 | 82 | 138 | 31 |
| **G** | 0 | 0 | 117 | 150 | 46 | 53 | 73 |

## Chauffage principal électrique (22 440 DPE)

Le modèle v3 **bat** « toujours C » en accuracy (49.9 % contre 44.1 %), **bat** cette référence à une classe près (87.5 % contre 81.1 %), **bat** le tirage aléatoire (49.9 % contre 26.7 %) et **bat** la répartition constante en score de Brier (0.6278 contre 0.7347).

| | Modèle v3 | Modèle v1 (actuel) | Classe majoritaire | Aléatoire selon la répartition |
|---|---:|---:|---:|---:|
| Accuracy | 49.9 % | 27.5 % | 44.1 % | 26.7 % |
| F1 macro | 27.6 % | 24.1 % | 8.7 % | 13.4 % |
| Accuracy à une classe près | 87.5 % | 56.0 % | 81.1 % | 64.9 % |
| Brier multiclasse | 0.6278 | 0.7824 | — | 0.7347 (répartition constante) |
| F1 classe A | 0.601 | 0.576 | 0.000 | 0.037 |
| F1 classe B | 0.245 | 0.333 | 0.000 | 0.126 |
| F1 classe C | 0.650 | 0.364 | 0.612 | 0.432 |
| F1 classe D | 0.181 | 0.046 | 0.000 | 0.229 |
| F1 classe E | 0.186 | 0.226 | 0.000 | 0.081 |
| F1 classe F | 0.000 | 0.058 | 0.000 | 0.020 |
| F1 classe G | 0.071 | 0.081 | 0.000 | 0.016 |

Fiabilité des probabilités du v3 :

| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |
|---|---:|---:|---:|
| 0–10 % | 0 | — | — |
| 10–20 % | 0 | — | — |
| 20–30 % | 737 | 29.0 % | 30.0 % |
| 30–40 % | 7 353 | 36.1 % | 38.6 % |
| 40–50 % | 6 492 | 43.8 % | 47.1 % |
| 50–60 % | 3 598 | 55.4 % | 56.5 % |
| 60–70 % | 2 660 | 63.8 % | 63.5 % |
| 70–80 % | 1 048 | 74.5 % | 80.4 % |
| 80–90 % | 537 | 86.0 % | 92.7 % |
| 90–100 % | 15 | 91.5 % | 86.7 % |

Matrice de confusion du v3 :

| Réel ↓ / Prédit → | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 965 | 339 | 280 | 5 | 0 | 0 | 0 |
| **B** | 520 | 642 | 2 555 | 161 | 13 | 0 | 0 |
| **C** | 132 | 354 | 8 804 | 553 | 52 | 0 | 7 |
| **D** | 7 | 21 | 3 684 | 556 | 120 | 0 | 8 |
| **E** | 0 | 0 | 1 334 | 274 | 214 | 0 | 6 |
| **F** | 0 | 0 | 438 | 128 | 46 | 0 | 5 |
| **G** | 0 | 0 | 111 | 65 | 32 | 0 | 9 |

## Autres chauffages (10 373 DPE)

Le modèle v3 **bat** « toujours C » en accuracy (52.7 % contre 38.1 %), **bat** cette référence à une classe près (93.0 % contre 76.9 %), **bat** le tirage aléatoire (52.7 % contre 27.6 %) et **bat** la répartition constante en score de Brier (0.5854 contre 0.7220).

| | Modèle v3 | Modèle v1 (actuel) | Classe majoritaire | Aléatoire selon la répartition |
|---|---:|---:|---:|---:|
| Accuracy | 52.7 % | 37.3 % | 38.1 % | 27.6 % |
| F1 macro | 34.8 % | 26.9 % | 7.9 % | 13.0 % |
| Accuracy à une classe près | 93.0 % | 84.1 % | 76.9 % | 67.5 % |
| Brier multiclasse | 0.5854 | 0.7032 | — | 0.7220 (répartition constante) |
| F1 classe A | 0.462 | 0.069 | 0.000 | 0.000 |
| F1 classe B | 0.048 | 0.264 | 0.000 | 0.045 |
| F1 classe C | 0.628 | 0.323 | 0.552 | 0.413 |
| F1 classe D | 0.581 | 0.504 | 0.000 | 0.288 |
| F1 classe E | 0.063 | 0.299 | 0.000 | 0.124 |
| F1 classe F | 0.295 | 0.154 | 0.000 | 0.034 |
| F1 classe G | 0.360 | 0.272 | 0.000 | 0.010 |

Fiabilité des probabilités du v3 :

| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |
|---|---:|---:|---:|
| 0–10 % | 0 | — | — |
| 10–20 % | 0 | — | — |
| 20–30 % | 148 | 28.2 % | 27.0 % |
| 30–40 % | 1 480 | 34.2 % | 43.4 % |
| 40–50 % | 3 930 | 46.9 % | 45.3 % |
| 50–60 % | 2 480 | 53.4 % | 48.6 % |
| 60–70 % | 700 | 64.6 % | 61.6 % |
| 70–80 % | 578 | 75.3 % | 73.0 % |
| 80–90 % | 769 | 85.3 % | 87.9 % |
| 90–100 % | 288 | 91.7 % | 94.4 % |

Matrice de confusion du v3 :

| Réel ↓ / Prédit → | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 6 | 2 | 4 | 0 | 0 | 0 | 0 |
| **B** | 6 | 9 | 316 | 23 | 0 | 0 | 0 |
| **C** | 2 | 10 | 2 308 | 1 612 | 7 | 7 | 4 |
| **D** | 0 | 3 | 646 | 2 890 | 70 | 50 | 14 |
| **E** | 0 | 0 | 96 | 1 298 | 55 | 102 | 26 |
| **F** | 0 | 0 | 22 | 363 | 36 | 138 | 26 |
| **G** | 0 | 0 | 6 | 85 | 14 | 53 | 64 |
