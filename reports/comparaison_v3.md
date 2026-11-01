# Comparaison des modèles v3 (validation)

Généré par `training/comparer_modeles.py` le 2026-11-01T09:25:01+00:00.

Entraînement : 1 130 191 DPE établis avant le 2026-05-01 ; validation : 62 467 DPE du 2026-05-01 au 2026-08-30. Le test n'est pas utilisé ici.

Règle de choix fixée à l'avance : taille ≤ max, puis plus petit Brier, puis accuracy à égalité de Brier (taille max 50 Mo, égalité si écart de Brier ≤ 0.002).

Localisation retenue : **departement** (variables : surface, periode, type_batiment, chauffage, departement).

**Modèle retenu : LightGBM {'num_leaves': 63, 'learning_rate': 0.1, 'min_child_samples': 500}**

| Modèle | Accuracy | F1 macro | À une classe près | Brier | Entraînement | Fichier |
|---|---:|---:|---:|---:|---:|---:|
| Classe majoritaire (C) | 40.6 % | 8.2 % | 79.6 % | 1.1881 | 0 s | 0.0 Mo |
| Répartition des classes (probabilités constantes) | 40.6 % | 8.2 % | 79.6 % | 0.7363 | 0 s | 0.0 Mo |
| LightGBM base, localisation = zone | 48.3 % | 33.1 % | 87.9 % | 0.6323 | 12 s | 1.3 Mo |
| LightGBM base, localisation = departement | 48.7 % | 33.9 % | 87.9 % | 0.6298 | 11 s | 1.0 Mo |
| LightGBM base, localisation = departement_et_zone | 49.0 % | 34.3 % | 88.1 % | 0.6297 | 12 s | 1.0 Mo |
| Régression logistique multinomiale | 47.6 % | 30.9 % | 87.8 % | 0.6369 | 113 s | 0.0 Mo |
| Random Forest 100 arbres, feuilles ≥ 500 | 48.8 % | 30.7 % | 87.9 % | 0.6346 | 135 s | 7.5 Mo |
| Random Forest 100 arbres, feuilles ≥ 500, balanced | 32.6 % | 30.1 % | 67.6 % | 0.7514 | 85 s | 6.8 Mo |
| Random Forest 100 arbres, feuilles ≥ 200 | 48.9 % | 32.0 % | 88.4 % | 0.6329 | 146 s | 18.4 Mo |
| Random Forest 100 arbres, feuilles ≥ 200, balanced | 33.2 % | 30.6 % | 68.2 % | 0.7497 | 120 s | 15.2 Mo |
| Random Forest 60 arbres, feuilles ≥ 100 | 48.7 % | 33.8 % | 88.3 % | 0.6339 | 161 s | 23.7 Mo |
| Random Forest 60 arbres, feuilles ≥ 100, balanced | 32.9 % | 30.5 % | 67.9 % | 0.7536 | 104 s | 19.4 Mo |
| LightGBM {'num_leaves': 31, 'learning_rate': 0.1, 'min_child_samples': 100} | 48.6 % | 33.6 % | 87.7 % | 0.6297 | 9 s | 0.6 Mo |
| LightGBM {'num_leaves': 63, 'learning_rate': 0.1, 'min_child_samples': 100} | 48.7 % | 33.9 % | 87.9 % | 0.6298 | 30 s | 1.0 Mo |
| LightGBM {'num_leaves': 127, 'learning_rate': 0.1, 'min_child_samples': 100} | 48.8 % | 33.8 % | 88.2 % | 0.6305 | 60 s | 1.5 Mo |
| LightGBM {'num_leaves': 255, 'learning_rate': 0.1, 'min_child_samples': 100} | 49.0 % | 33.8 % | 88.2 % | 0.6324 | 85 s | 3.0 Mo |
| LightGBM {'num_leaves': 63, 'learning_rate': 0.05, 'min_child_samples': 100} | 49.1 % | 34.4 % | 88.2 % | 0.6288 | 77 s | 2.0 Mo |
| LightGBM {'num_leaves': 127, 'learning_rate': 0.05, 'min_child_samples': 100} | 48.8 % | 33.9 % | 88.1 % | 0.6299 | 17 s | 3.2 Mo |
| LightGBM {'num_leaves': 63, 'learning_rate': 0.1, 'min_child_samples': 500} | 49.2 % | 34.3 % | 88.1 % | 0.6289 | 10 s | 0.9 Mo |
| LightGBM {'num_leaves': 127, 'learning_rate': 0.1, 'min_child_samples': 500} | 48.8 % | 34.1 % | 88.0 % | 0.6297 | 12 s | 1.5 Mo |
| LightGBM {'num_leaves': 255, 'learning_rate': 0.05, 'min_child_samples': 500} | 48.9 % | 34.3 % | 88.5 % | 0.6304 | 24 s | 6.2 Mo |
| LightGBM {'num_leaves': 511, 'learning_rate': 0.05, 'min_child_samples': 1000} | 48.9 % | 34.2 % | 88.3 % | 0.6304 | 33 s | 12.2 Mo |
| Ordinal : régression CEP et EGES puis seuils | 49.1 % | 32.5 % | 88.7 % | 0.6372 | 19 s | 5.3 Mo |

Tirage aléatoire selon la répartition (graine 42) : accuracy 27.0 %, F1 macro 14.3 %, à une classe près 66.6 %.

Notes :
- Les LightGBM utilisent l'arrêt anticipé sur la validation (50 tours sans progrès de la log-loss) : leurs scores de validation sont légèrement optimistes ; le test reste intact.
- Localisation : la règle « à Brier quasi égal, la plus simple » a été ajoutée après une première exécution où « département + zone » devançait « département » de 0,0001 de Brier ; la zone étant une fonction du département, cet écart est du bruit. Les deux autres règles n'ont pas changé.
- Taille : fichier joblib compressé (niveau 3), comme l'artefact final.
- Temps mesurés sur un PC portable, 16 cœurs logiques.
- Approche ordinale : altitude inconnue à la saisie, donc seuils hors altitude ; probabilités par 200 tirages conjoints de résidus mis de côté sur l'entraînement.
