# Calibration et courbe d'apprentissage du modèle v3

Généré par `training/calibrer_v3.py` le 2026-11-01T09:25:59+00:00. Modèle : LightGBM {'num_leaves': 63, 'learning_rate': 0.1, 'min_child_samples': 500} (localisation : departement).

## Calibration (validation, 5 plis)

Chaque méthode est apprise sur 4 plis de la validation et mesurée sur le 5e. Méthode retenue (plus petit Brier) : **isotonique**.

| | Sans calibration | Isotonique | Sigmoïde |
|---|---:|---:|---:|
| Brier multiclasse | 0.6289 | 0.6252 | 0.6275 |
| Accuracy | 49.2 % | 50.0 % | 49.3 % |
| F1 macro | 34.3 % | 34.2 % | 34.3 % |
| À une classe près | 88.1 % | 88.3 % | 88.4 % |

Fiabilité — sans calibration :

| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |
|---|---:|---:|---:|
| 0–10 % | 0 | — | — |
| 10–20 % | 0 | — | — |
| 20–30 % | 2 411 | 27.6 % | 29.3 % |
| 30–40 % | 18 025 | 35.9 % | 37.2 % |
| 40–50 % | 20 427 | 44.8 % | 46.7 % |
| 50–60 % | 9 543 | 54.2 % | 55.3 % |
| 60–70 % | 5 955 | 64.8 % | 64.0 % |
| 70–80 % | 3 348 | 74.9 % | 71.7 % |
| 80–90 % | 2 511 | 84.0 % | 81.0 % |
| 90–100 % | 247 | 90.6 % | 89.5 % |

Fiabilité — isotonique :

| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |
|---|---:|---:|---:|
| 0–10 % | 0 | — | — |
| 10–20 % | 0 | — | — |
| 20–30 % | 1 755 | 28.7 % | 28.2 % |
| 30–40 % | 16 964 | 35.7 % | 37.5 % |
| 40–50 % | 19 732 | 44.9 % | 47.0 % |
| 50–60 % | 11 975 | 54.4 % | 55.0 % |
| 60–70 % | 6 266 | 64.0 % | 64.9 % |
| 70–80 % | 3 358 | 74.5 % | 73.0 % |
| 80–90 % | 1 839 | 84.8 % | 79.4 % |
| 90–100 % | 578 | 91.8 % | 89.8 % |

Fiabilité — sigmoide :

| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |
|---|---:|---:|---:|
| 0–10 % | 0 | — | — |
| 10–20 % | 0 | — | — |
| 20–30 % | 1 561 | 27.7 % | 27.0 % |
| 30–40 % | 18 088 | 36.1 % | 37.2 % |
| 40–50 % | 17 763 | 44.7 % | 45.7 % |
| 50–60 % | 13 677 | 54.0 % | 54.8 % |
| 60–70 % | 5 631 | 64.7 % | 64.7 % |
| 70–80 % | 3 225 | 75.3 % | 72.4 % |
| 80–90 % | 2 219 | 84.4 % | 80.2 % |
| 90–100 % | 303 | 90.8 % | 91.7 % |

## Courbe d'apprentissage (validation, sans calibration)

| Lignes d'entraînement | Accuracy | F1 macro | À une classe près | Brier | Itérations | Temps |
|---:|---:|---:|---:|---:|---:|---:|
| 10 000 | 48.0 % | 32.5 % | 88.0 % | 0.6367 | 71 | 1 s |
| 50 000 | 48.7 % | 33.7 % | 88.1 % | 0.6321 | 41 | 2 s |
| 200 000 | 48.9 % | 34.0 % | 88.0 % | 0.6281 | 47 | 4 s |
| 1 130 191 | 49.2 % | 34.3 % | 88.1 % | 0.6289 | 41 | 10 s |
