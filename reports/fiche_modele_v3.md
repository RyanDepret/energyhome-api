# Fiche du modèle v3 — estimation de la classe DPE

Version `v3-lightgbm-2026-11`, exportée le 2026-11-01. Fiche générée par `training/fiche_v3.py` à partir des rapports du dépôt.

## Usage prévu

Donner une **estimation indicative** de la classe DPE (A à G) d'un logement de la région PACA à partir de cinq informations que tout le monde connaît. **Ce n'est pas un DPE officiel** : un DPE est établi par un diagnostiqueur certifié qui visite le logement.

## Données

- Source : ADEME, base publique des DPE de logements existants (`dpe03existant`), région PACA, maisons et appartements.
- Entraînement : 1 130 191 DPE établis du 2021-07-01 au 2026-04-30.
- Validation (choix du modèle, des réglages et de la calibration) : 62 467 DPE du 2026-05-01 au 2026-08-30.
- Test (utilisé une seule fois, à la fin) : 32 813 DPE du 2026-08-31 au 2026-10-26, identique à celui de la mesure du modèle précédent.
- Empreinte SHA-256 des données d'entraînement : `71a5e6cdd03de8a5…`.

## Variables

Uniquement ce que l'utilisateur saisit : surface, période de construction, type de bâtiment, énergie de chauffage et département (déduit du code postal). Aucune consommation, émission ni étiquette en entrée. La zone climatique, entièrement déterminée par le département, n'apporte rien de plus (`reports/comparaison_v3.md`).

Importance moyenne dans les prédictions (contributions SHAP, validation) : période de construction 48.6 %, énergie de chauffage 22.7 %, département 13.2 %, surface 9.7 %, type de bâtiment 5.8 %.

## Cible

L'étiquette DPE officielle (`etiquette_dpe`), au coefficient électricité 1.9. Le jeu ADEME publie déjà tous les DPE à ce coefficient, y compris ceux établis avant 2026 (rapport énergie primaire / finale médian des logements tout électriques : 1.905) ; ce coefficient est contrôlé automatiquement à chaque préparation des données. Les seuils officiels (petites surfaces, altitude) reproduisent 99.98 % des étiquettes 2026.

## Modèle

LightGBM {'num_leaves': 63, 'learning_rate': 0.1, 'min_child_samples': 500}, choisi sur la validation parmi 23 candidats (références, régression logistique, Random Forest, LightGBM, approche ordinale) ; calibration : isotonique. Fichier du modèle : 0.9 Mo.

## Résultats sur le test

| | Modèle v3 | Modèle précédent (v1) | Toujours « C » | Répartition constante |
|---|---:|---:|---:|---:|
| Accuracy | 50.8 % | 30.6 % | 42.2 % | — |
| Accuracy à une classe près | 89.3 % | 64.9 % | 79.7 % | — |
| F1 macro | 35.1 % | 28.8 % | 8.5 % | — |
| Brier multiclasse (plus bas = mieux) | 0.614 | 0.757 | — | 0.731 |

Bat « toujours C » en accuracy : oui ; à une classe près : oui ; la répartition constante en Brier : oui. Détail par type de chauffage : `reports/modele_v3.md`.

## Écart entre entraînement, validation et test

| | Entraînement (1 130 191) | Validation (62 467) | Test (32 813) |
|---|---:|---:|---:|
| Accuracy | 50.6 % | 50.0 % | 50.8 % |
| Accuracy à une classe près | 88.4 % | 88.3 % | 89.3 % |
| Brier multiclasse (plus bas = mieux) | 0.6104 | 0.6252 | 0.6144 |

Pas de sur-apprentissage mesurable : l'accuracy d'entraînement dépasse celle du moins bon jeu non vu de 0.6 point(s) et le Brier est plus élevé de 0.015 hors entraînement. Le modèle ne fait guère mieux sur les logements qu'il a vus (50.6 % d'accuracy) que sur les autres : sa précision est limitée par l'information contenue dans les cinq variables, pas par un apprentissage par cœur.

Mesures : entraînement calculé par `training/ecart_v3.py` avec le modèle servi (calibration comprise) ; validation avec la calibration isotonique mesurée hors pli (`reports/calibration_v3.md`) ; test repris de `reports/modele_v3.md`. La validation a servi à l'arrêt précoce, au choix du modèle et à la calibration. Sans calibration : Brier 0.6088 sur l'entraînement contre 0.6289 sur la validation.

## Limites connues

- **Cinq variables seulement** : l'isolation, les fenêtres, le système de chauffage exact, la ventilation ou les travaux ne sont pas observés. Deux logements identiques sur ces cinq critères reçoivent la même estimation alors que leurs DPE réels peuvent différer ; c'est la principale limite de précision.
- **Classes extrêmes rarement prédites** : sur le test, le modèle prédit E, F ou G pour 1 178 logements alors que 5 046 le sont réellement ; il tire les estimations vers C et D. Le F1 est plus faible que celui du v1 pour les classes B, E (le v1 prédisait beaucoup plus souvent les classes extrêmes, à tort dans la plupart des cas).
- **PACA uniquement** : le modèle n'a vu aucun logement d'une autre région.
- Courbe d'apprentissage (Brier de validation) : 10 000 lignes → 0.637, 50 000 lignes → 0.632, 200 000 lignes → 0.628, 1 130 191 lignes → 0.629. Le Brier ne s'améliore plus au-delà de 200 000 lignes : plus de logements décrits par les mêmes cinq variables (France métropolitaine) aideraient peu ; d'autres variables aideraient davantage.
- Altitude : non demandée à l'utilisateur ; les seuils spécifiques au-dessus de 800 m (Hautes-Alpes, Alpes-de-Haute-Provence) ne sont appris qu'à travers le département.
- Chauffages rares (charbon, plaquettes, butane) : peu d'exemples, estimations moins fiables.
- Le coefficient électricité passe à 1,7 au 1er janvier 2027 : le modèle devra être réentraîné (cible recalculable par `training/etiquettes.py`).
