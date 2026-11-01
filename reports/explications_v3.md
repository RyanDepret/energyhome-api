# Explications du modèle v3

Généré par `training/expliquer_v3.py` le 2026-11-01T09:28:01+00:00, sur les 62 467 DPE de la validation.

## Importance globale des variables

Moyenne de |contribution SHAP| (en log-odds), calculée par LightGBM (`pred_contrib`).

| Variable | Classe prédite | Part | Toutes classes | Part |
|---|---:|---:|---:|---:|
| Période de construction | 0.550 | 48.6 % | 5.687 | 44.0 % |
| Énergie de chauffage | 0.257 | 22.7 % | 2.733 | 21.2 % |
| Département | 0.150 | 13.2 % | 1.767 | 13.7 % |
| Surface | 0.110 | 9.7 % | 1.947 | 15.1 % |
| Type de bâtiment | 0.066 | 5.8 % | 0.779 | 6.0 % |

## Contrôles des contributions

Sur 1000 lignes tirées au hasard :

- **Additivité** (contrôle indépendant) : contributions + terme constant = sortie brute du modèle pour chaque classe, à 1.53e-14 près au maximum.
- **Bibliothèque shap** (0.54.1) : écart maximal 0.00e+00 avec les contributions de l'API. Ce n'est pas une vérification indépendante : pour un modèle LightGBM, `shap.TreeExplainer` délègue au même calcul natif (`pred_contrib`). Elle confirme seulement que l'API fournit les mêmes valeurs que shap, qui n'est donc pas nécessaire en production.

## Temps de réponse

Limite visée : 200 ms par prédiction.

| Fonction | Médiane | 95e centile | Maximum |
|---|---:|---:|---:|
| `expliquer` | 20.6 ms | 34.2 ms | 70.9 ms |
| `predire_complet` | 21.2 ms | 35.2 ms | 38.4 ms |

## Exemple de sortie `importances`

Entrée : `{"surface": 74.2, "periode": "1983_1988", "type_batiment": "appartement", "chauffage": "gaz_naturel", "departement": "13", "zone_climatique": "H3"}`, classe prédite **C**.

| critere | valeur | poids |
|---|---|---:|
| Période de construction | 1983_1988 | 0.505 |
| Énergie de chauffage | gaz_naturel | 0.292 |
| Département | 13 | 0.150 |
| Type de bâtiment | appartement | 0.036 |
| Surface | 74.2 | 0.017 |
