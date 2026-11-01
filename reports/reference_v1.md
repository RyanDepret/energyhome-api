# Mesure de référence du modèle actuel (v1)

Généré par `training/evaluer.py` le 2026-10-31T20:25:32+00:00.
Modèle : `artifacts/modele_dpe_v2.pkl` (`model_version` = `v2-rf-2025`), chargé via `app/ml/`.
Données : `data/dpe_paca.parquet`, issu de l'extraction du 2026-10-31T19:53:21+00:00
(SHA-256 du brut `956077421b096bd5eb8c47d6ab90dbbbdcc6c737e52654a89bb298b1186267be`).

## Verdict

**Le modèle actuel ne bat pas la référence « classe majoritaire » en accuracy** (30.6 % contre 42.2 % sur le test temporel).

## Jeu de test temporel

- Date d'entraînement retenue : **2026-08-30**, date du commit `f7a44a7` (« Correction du data leakage : nouveau modele ML sans consommation en entree, zones climatiques deduites du code postal, agent enrichi maison/appartement »)
  qui a produit le contenu actuel du modèle (blob `d2fbb53`).
  Le dernier commit qui a touché le fichier, `94c3bbf` du 2026-10-25 (« Déplacement des scripts d'entraînement dans training/ et des artefacts dans artifacts/ »),
  n'a pas changé son contenu (même blob) : ce n'est pas une date d'entraînement.
- Test : DPE PACA nettoyés établis **après** le 2026-08-30 : 32 918 DPE
  (du 2026-08-31 au 2026-10-26).
- Exclus car refusés par l'API : 105
  (période inconnue 0, type de bâtiment inconnu 0,
  chauffage inconnu 105, département sans zone 0).
- **Évalués : 32 813 DPE.**
- Features construites avec `categorical_columns` de l'API ; 500
  lignes tirées au hasard vérifiées identiques à `build_features` (code exact de `/predict`).
- Zone climatique : comme en production, elle est déduite du département ; elle diffère de la zone indiquée
  dans le DPE pour 78 DPE du test.

Références à battre, construites **sans regarder le test**, à partir des 1 192 658 DPE PACA
établis jusqu'au 2026-08-30 :
- « toujours la classe majoritaire » : classe **C** ;
- « tirage aléatoire selon la répartition réelle » : tirage selon cette répartition (graine 42).

## Note corrective du 2026-11-01

La section suivante attribue une partie des erreurs au fait que le modèle aurait appris des étiquettes
calculées avec le coefficient 2,3. Une mesure faite après ce rapport (`training/valider_etiquettes.py`,
`reports/validation_etiquettes.md`) montre que le jeu ADEME extrait le 2026-10-31 publie **tous** les DPE
en 1,9, y compris ceux établis avant 2026 : pour les DPE dont la seule énergie est l'électricité, le rapport
énergie primaire / énergie finale a une médiane de 1,906 avant 2026 (549 768 DPE) et de 1,902 depuis
(95 565 DPE). Cette explication ne vaut donc pas pour les données actuelles ; elle vaut peut-être pour
l'extraction de 2025 qui a servi à entraîner le modèle, ce qui ne peut plus être vérifié.
Les chiffres de ce rapport ne changent pas.

## Attention : coefficient électricité 1,9

Les DPE établis depuis le 1er janvier 2026 utilisent un coefficient de conversion de l'électricité en énergie
primaire de 1,9 (au lieu de 2,3). Le modèle a appris sur des étiquettes majoritairement calculées en 2,3.

- DPE du test établis depuis le 1er janvier 2026 : **32 813 sur 32 813**
  - dont chauffage principal électrique : 22 440
  - dont autres chauffages : 10 373

Les résultats ci-dessous mélangent donc les erreurs propres au modèle et l'effet de ce changement de calcul.

Répartition des classes en PACA (jeu nettoyé complet) avant et depuis le 1er janvier 2026 :

| Classe | Électrique avant 2026 | Électrique depuis 2026 | Autres avant 2026 | Autres depuis 2026 |
|---|---:|---:|---:|---:|
| A | 33 979 (5.5 %) | 7 383 (6.8 %) | 2 288 (0.5 %) | 253 (0.4 %) |
| B | 95 722 (15.6 %) | 18 748 (17.2 %) | 21 142 (4.8 %) | 2 170 (3.8 %) |
| C | 262 131 (42.6 %) | 46 651 (42.8 %) | 189 304 (42.6 %) | 22 467 (39.0 %) |
| D | 129 757 (21.1 %) | 22 128 (20.3 %) | 142 811 (32.1 %) | 20 640 (35.9 %) |
| E | 62 417 (10.2 %) | 9 615 (8.8 %) | 58 305 (13.1 %) | 7 899 (13.7 %) |
| F | 20 533 (3.3 %) | 3 387 (3.1 %) | 21 458 (4.8 %) | 2 982 (5.2 %) |
| G | 10 174 (1.7 %) | 1 117 (1.0 %) | 8 970 (2.0 %) | 1 145 (2.0 %) |
| Total | 614 713 | 109 029 | 444 278 | 57 556 |

Répartition réelle du test comparée à celle utilisée par les références :

| Classe | Test temporel | Avant coupure (références) |
|---|---:|---:|
| A | 1 601 (4.9 %) | 42 302 (3.5 %) |
| B | 4 245 (12.9 %) | 133 537 (11.2 %) |
| C | 13 852 (42.2 %) | 506 608 (42.5 %) |
| D | 8 069 (24.6 %) | 307 262 (25.8 %) |
| E | 3 405 (10.4 %) | 134 825 (11.3 %) |
| F | 1 202 (3.7 %) | 47 158 (4.0 %) |
| G | 439 (1.3 %) | 20 966 (1.8 %) |
| Total | 32 813 | 1 192 658 |

## Résultats

### Tous les logements (32 813 DPE)

**Le modèle actuel ne bat pas la référence « classe majoritaire » en accuracy** (30.6 % contre 42.2 % sur le test temporel).

| | Modèle actuel | Classe majoritaire | Aléatoire selon la répartition |
|---|---:|---:|---:|
| Accuracy | 30.6 % | 42.2 % | 27.3 % |
| F1 macro | 28.8 % | 8.5 % | 14.3 % |
| Accuracy à une classe près | 64.9 % | 79.7 % | 66.3 % |
| F1 classe A | 0.547 | 0.000 | 0.045 |
| F1 classe B | 0.324 | 0.000 | 0.112 |
| F1 classe C | 0.352 | 0.594 | 0.427 |
| F1 classe D | 0.336 | 0.000 | 0.248 |
| F1 classe E | 0.254 | 0.000 | 0.114 |
| F1 classe F | 0.074 | 0.000 | 0.038 |
| F1 classe G | 0.125 | 0.000 | 0.018 |

Calibration du modèle : score de Brier multiclasse **0.7574**
(référence « répartition constante » : 0.7306 ; plus bas = mieux).

| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |
|---|---:|---:|---:|
| 0–10 % | 0 | — | — |
| 10–20 % | 2 174 | 19.0 % | 9.9 % |
| 20–30 % | 14 196 | 24.9 % | 19.5 % |
| 30–40 % | 8 764 | 35.6 % | 40.3 % |
| 40–50 % | 4 373 | 43.6 % | 40.8 % |
| 50–60 % | 1 590 | 53.6 % | 49.7 % |
| 60–70 % | 1 289 | 64.9 % | 49.0 % |
| 70–80 % | 409 | 75.5 % | 74.3 % |
| 80–90 % | 18 | 80.2 % | 83.3 % |
| 90–100 % | 0 | — | — |

Matrice de confusion du modèle :

| Réel ↓ / Prédit → | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 1 350 | 120 | 10 | 4 | 12 | 85 | 20 |
| **B** | 1 104 | 1 515 | 285 | 86 | 434 | 590 | 231 |
| **C** | 784 | 2 850 | 3 212 | 1 809 | 2 334 | 1 885 | 978 |
| **D** | 76 | 521 | 749 | 2 180 | 2 196 | 1 267 | 1 080 |
| **E** | 21 | 69 | 102 | 679 | 1 308 | 611 | 615 |
| **F** | 1 | 21 | 16 | 125 | 445 | 218 | 376 |
| **G** | 1 | 7 | 1 | 7 | 145 | 28 | 250 |

### Chauffage principal électrique (22 440 DPE)

**Le modèle actuel ne bat pas la référence « classe majoritaire » en accuracy** (27.5 % contre 44.1 % sur le test temporel).

| | Modèle actuel | Classe majoritaire | Aléatoire selon la répartition |
|---|---:|---:|---:|
| Accuracy | 27.5 % | 44.1 % | 26.7 % |
| F1 macro | 24.1 % | 8.7 % | 13.4 % |
| Accuracy à une classe près | 56.0 % | 81.1 % | 64.9 % |
| F1 classe A | 0.576 | 0.000 | 0.037 |
| F1 classe B | 0.333 | 0.000 | 0.126 |
| F1 classe C | 0.364 | 0.612 | 0.432 |
| F1 classe D | 0.046 | 0.000 | 0.229 |
| F1 classe E | 0.226 | 0.000 | 0.081 |
| F1 classe F | 0.058 | 0.000 | 0.020 |
| F1 classe G | 0.081 | 0.000 | 0.016 |

Calibration du modèle : score de Brier multiclasse **0.7824**
(référence « répartition constante » : 0.7347 ; plus bas = mieux).

| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |
|---|---:|---:|---:|
| 0–10 % | 0 | — | — |
| 10–20 % | 2 084 | 19.0 % | 9.4 % |
| 20–30 % | 11 587 | 24.6 % | 18.1 % |
| 30–40 % | 3 769 | 35.0 % | 42.5 % |
| 40–50 % | 1 998 | 44.1 % | 36.0 % |
| 50–60 % | 1 361 | 53.6 % | 48.9 % |
| 60–70 % | 1 219 | 65.1 % | 47.2 % |
| 70–80 % | 404 | 75.5 % | 74.3 % |
| 80–90 % | 18 | 80.2 % | 83.3 % |
| 90–100 % | 0 | — | — |

Matrice de confusion du modèle :

| Réel ↓ / Prédit → | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 1 340 | 118 | 10 | 4 | 12 | 85 | 20 |
| **B** | 1 023 | 1 351 | 231 | 61 | 405 | 589 | 231 |
| **C** | 616 | 2 175 | 2 394 | 137 | 1 796 | 1 842 | 942 |
| **D** | 63 | 485 | 518 | 110 | 1 210 | 1 124 | 886 |
| **E** | 17 | 60 | 87 | 35 | 705 | 493 | 431 |
| **F** | 1 | 21 | 15 | 8 | 217 | 143 | 212 |
| **G** | 0 | 5 | 0 | 1 | 66 | 21 | 124 |

### Autres chauffages (10 373 DPE)

**Le modèle actuel ne bat pas la référence « classe majoritaire » en accuracy** (37.3 % contre 38.1 % sur le test temporel).

| | Modèle actuel | Classe majoritaire | Aléatoire selon la répartition |
|---|---:|---:|---:|
| Accuracy | 37.3 % | 38.1 % | 27.6 % |
| F1 macro | 26.9 % | 7.9 % | 13.0 % |
| Accuracy à une classe près | 84.1 % | 76.9 % | 67.5 % |
| F1 classe A | 0.069 | 0.000 | 0.000 |
| F1 classe B | 0.264 | 0.000 | 0.045 |
| F1 classe C | 0.323 | 0.552 | 0.413 |
| F1 classe D | 0.504 | 0.000 | 0.288 |
| F1 classe E | 0.299 | 0.000 | 0.124 |
| F1 classe F | 0.154 | 0.000 | 0.034 |
| F1 classe G | 0.272 | 0.000 | 0.010 |

Calibration du modèle : score de Brier multiclasse **0.7032**
(référence « répartition constante » : 0.7220 ; plus bas = mieux).

| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |
|---|---:|---:|---:|
| 0–10 % | 0 | — | — |
| 10–20 % | 90 | 18.9 % | 22.2 % |
| 20–30 % | 2 609 | 26.3 % | 25.5 % |
| 30–40 % | 4 995 | 36.0 % | 38.6 % |
| 40–50 % | 2 375 | 43.2 % | 44.8 % |
| 50–60 % | 229 | 53.5 % | 54.6 % |
| 60–70 % | 70 | 61.0 % | 81.4 % |
| 70–80 % | 5 | 74.9 % | 80.0 % |
| 80–90 % | 0 | — | — |
| 90–100 % | 0 | — | — |

Matrice de confusion du modèle :

| Réel ↓ / Prédit → | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 10 | 2 | 0 | 0 | 0 | 0 | 0 |
| **B** | 81 | 164 | 54 | 25 | 29 | 1 | 0 |
| **C** | 168 | 675 | 818 | 1 672 | 538 | 43 | 36 |
| **D** | 13 | 36 | 231 | 2 070 | 986 | 143 | 194 |
| **E** | 4 | 9 | 15 | 644 | 603 | 118 | 184 |
| **F** | 0 | 0 | 1 | 117 | 228 | 75 | 164 |
| **G** | 1 | 2 | 1 | 6 | 79 | 7 | 126 |

