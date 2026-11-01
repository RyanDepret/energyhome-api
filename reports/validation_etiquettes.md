# Validation du recalcul des étiquettes

Généré par `training/valider_etiquettes.py` le 2026-11-01T08:54:47+00:00.

Règles appliquées (Arrêté du 25 mars 2024 (NOR TREL2330369A), JORF du 20 avril 2024, texte 15, annexe 1 ; Légifrance JORFARTI000049446339) : CEP et EGES arrondis à l'entier inférieur, inégalités strictes, seuils petites surfaces (≤ 40 m², interpolation linéaire) et altitude (> 800 m en H1b, H1c, H2d). La surface utilisée est `surface_habitable_logement` : le jeu ADEME ne publie pas la surface de référence.

Recalculer un DPE à son propre coefficient n'applique aucune correction : les deux premières sections valident les seuils, pas le coefficient. Le coefficient réellement présent dans les données est mesuré plus bas.

## DPE établis depuis le 2026-01-01, coefficient 1,9 (aucune correction : seuils seuls)

- DPE comparés : 166 585, coefficient 1.9
- **Concordance globale : 99.98 %**
- Désaccords : 30 (étiquette officielle meilleure : 30, plus mauvaise : 0)

| Tranche de surface | DPE | Concordance |
|---|---:|---:|
| < 40 m² | 40 635 | 99.93 % |
| 40–100 m² | 97 831 | 100.00 % |
| > 100 m² | 28 119 | 100.00 % |

| Surface (m²) | DPE | Concordance |
|---|---:|---:|
| [0.0, 10.0) | 315 | 100.00 % |
| [10.0, 15.0) | 896 | 99.67 % |
| [15.0, 20.0) | 5 776 | 99.95 % |
| [20.0, 25.0) | 7 355 | 99.85 % |
| [25.0, 30.0) | 8 299 | 99.92 % |
| [30.0, 35.0) | 9 131 | 99.99 % |
| [35.0, 40.0) | 8 863 | 99.97 % |
| [40.0, 40.0001) | 392 | 99.49 % |
| [40.0001, 45.0) | 10 051 | 100.00 % |
| [45.0, 50.0) | 9 768 | 100.00 % |
| [50.0, inf) | 105 739 | 100.00 % |

| Chauffage principal | DPE | Concordance |
|---|---:|---:|
| Électricité | 109 029 | 99.97 % |
| Gaz naturel | 43 792 | 100.00 % |
| Fioul domestique | 6 647 | 100.00 % |
| Bois – Bûches | 2 900 | 100.00 % |
| Réseau de Chauffage urbain | 2 127 | 99.95 % |
| Bois – Granulés (pellets) ou briquettes | 1 115 | 100.00 % |
| GPL | 653 | 100.00 % |
| Propane | 186 | 100.00 % |
| Bois – Plaquettes forestières | 112 | 100.00 % |
| Bois – Plaquettes d’industrie | 10 | 100.00 % |
| Charbon | 8 | 100.00 % |
| Butane | 6 | 100.00 % |

Matrice réel (lignes) / recalculé (colonnes) :

| | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 7 636 | 0 | 0 | 0 | 0 | 0 | 0 |
| **B** | 0 | 20 917 | 1 | 0 | 0 | 0 | 0 |
| **C** | 0 | 0 | 69 106 | 12 | 0 | 0 | 0 |
| **D** | 0 | 0 | 0 | 42 759 | 9 | 0 | 0 |
| **E** | 0 | 0 | 0 | 0 | 17 508 | 6 | 0 |
| **F** | 0 | 0 | 0 | 0 | 0 | 6 367 | 2 |
| **G** | 0 | 0 | 0 | 0 | 0 | 0 | 2 262 |

Exemples d'écarts (tirés au hasard, graine 42) :

| N° DPE | Date | Surface | Chauffage | Zone | Altitude | CEP | EGES | Réel | Recalculé |
|---|---|---:|---|---|---|---:|---:|---|---|
| 2613E2630653R | 2026-10-14 | 14.5 | Électricité | H3 | inférieur à 400m | 341.0 | 13.0 | D | E |
| 2683E1536227B | 2026-06-08 | 23.0 | Électricité | H3 | inférieur à 400m | 217.0 | 8.0 | C | D |
| 2613E2041578Y | 2026-07-30 | 15.9 | Électricité | H3 | inférieur à 400m | 326.0 | 12.0 | D | E |
| 2613E1568538C | 2026-06-11 | 29.5 | Électricité | H3 | inférieur à 400m | 268.0 | 10.0 | D | E |
| 2683E0593517Z | 2026-03-02 | 19.6 | Électricité | H3 | inférieur à 400m | 302.0 | 12.0 | D | E |
| 2606E0909996H | 2026-03-31 | 22.5 | Électricité | H3 | inférieur à 400m | 289.7 | 11.3 | D | E |
| 2606E2664853U | 2026-10-19 | 22.5 | Électricité | H3 | inférieur à 400m | 289.7 | 11.3 | D | E |
| 2684E2336378D | 2026-09-12 | 39.5 | Électricité | H2d | inférieur à 400m | 251.0 | 9.0 | D | E |
| 2683E1177518O | 2026-04-29 | 40.0 | Électricité | H3 | inférieur à 400m | 250.0 | 9.0 | D | E |
| 2606E0044855Q | 2026-01-08 | 20.8 | Électricité | H3 | inférieur à 400m | 472.0 | 18.0 | F | G |
| 2613E0381411J | 2026-02-09 | 21.5 | Électricité | H3 | inférieur à 400m | 223.0 | 8.0 | C | D |
| 2683E1559234Y | 2026-06-10 | 24.5 | Électricité | H3 | inférieur à 400m | 212.0 | 7.0 | C | D |
| 2606E0382760Z | 2026-02-10 | 20.8 | Électricité | H3 | 400-800m | 226.4 | 8.6 | C | D |
| 2613E1259897H | 2026-05-07 | 13.9 | Électricité | H3 | inférieur à 400m | 274.4 | 10.3 | C | D |
| 2613E1071338A | 2026-04-17 | 18.5 | Électricité | H3 | inférieur à 400m | 238.0 | 9.0 | C | D |

## DPE établis avant 2026, coefficient lu dans la table datée : 2,3 (aucune correction : seuils seuls)

- DPE comparés : 1 058 991, coefficient 2.3
- **Concordance globale : 99.72 %**
- Désaccords : 3 008 (étiquette officielle meilleure : 80, plus mauvaise : 2 928)

| Tranche de surface | DPE | Concordance |
|---|---:|---:|
| < 40 m² | 223 268 | 99.30 % |
| 40–100 m² | 685 450 | 99.85 % |
| > 100 m² | 150 273 | 99.73 % |

| Surface (m²) | DPE | Concordance |
|---|---:|---:|
| [0.0, 10.0) | 490 | 99.39 % |
| [10.0, 15.0) | 5 183 | 99.19 % |
| [15.0, 20.0) | 27 407 | 99.35 % |
| [20.0, 25.0) | 38 245 | 99.25 % |
| [25.0, 30.0) | 47 478 | 99.24 % |
| [30.0, 35.0) | 51 688 | 99.32 % |
| [35.0, 40.0) | 52 777 | 99.35 % |
| [40.0, 40.0001) | 3 533 | 99.52 % |
| [40.0001, 45.0) | 60 545 | 99.82 % |
| [45.0, 50.0) | 69 266 | 99.89 % |
| [50.0, inf) | 702 379 | 99.82 % |

| Chauffage principal | DPE | Concordance |
|---|---:|---:|
| Électricité | 614 456 | 99.53 % |
| Gaz naturel | 335 650 | 99.98 % |
| Fioul domestique | 43 272 | 99.94 % |
| Réseau de Chauffage urbain | 31 138 | 99.97 % |
| Bois – Bûches | 23 989 | 99.96 % |
| Bois – Granulés (pellets) ou briquettes | 5 185 | 99.96 % |
| GPL | 3 534 | 99.94 % |
| Propane | 1 098 | 100.00 % |
| Bois – Plaquettes forestières | 290 | 100.00 % |
| Électricité d'origine renouvelable utilisée dans le bâtiment | 257 | 100.00 % |
| Charbon | 51 | 100.00 % |
| Butane | 36 | 100.00 % |
| Bois – Plaquettes d’industrie | 35 | 100.00 % |

Matrice réel (lignes) / recalculé (colonnes) :

| | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 36 267 | 0 | 0 | 0 | 0 | 0 | 0 |
| **B** | 82 | 116 771 | 11 | 0 | 0 | 0 | 0 |
| **C** | 263 | 412 | 450 745 | 15 | 0 | 0 | 0 |
| **D** | 233 | 249 | 594 | 271 479 | 13 | 0 | 0 |
| **E** | 109 | 160 | 122 | 304 | 120 004 | 23 | 0 |
| **F** | 50 | 50 | 61 | 10 | 103 | 41 699 | 18 |
| **G** | 19 | 41 | 22 | 12 | 2 | 30 | 19 018 |

Exemples d'écarts (tirés au hasard, graine 42) :

| N° DPE | Date | Surface | Chauffage | Zone | Altitude | CEP | EGES | Réel | Recalculé |
|---|---|---:|---|---|---|---:|---:|---|---|
| 2106E0186508Q | 2021-07-29 | 22.0 | Électricité | H3 | inférieur à 400m | 56.3 | 0.2 | F | A |
| 2183E0389393W | 2021-09-23 | 113.3 | Électricité | H3 | inférieur à 400m | 102.5 | 3.1 | D | B |
| 2206E0333790J | 2022-02-08 | 20.6 | Électricité | H3 | inférieur à 400m | 127.0 | 3.0 | C | B |
| 2383E4194151U | 2023-12-06 | 26.5 | Électricité | H3 | inférieur à 400m | 205.9 | 7.0 | D | C |
| 2183E0538357G | 2021-07-19 | 65.7 | Électricité | H3 | inférieur à 400m | 185.2 | 31.6 | E | D |
| 2513E1391177M | 2025-04-24 | 23.6 | Électricité | H3 | inférieur à 400m | 122.9 | 4.0 | C | B |
| 2113E0355174B | 2021-09-18 | 109.0 | Électricité | H3 | inférieur à 400m | 100.4 | 3.1 | E | B |
| 2113E0801016V | 2021-11-29 | 16.1 | Électricité | H3 | inférieur à 400m | 138.0 | 13.0 | F | C |
| 2484E1468893G | 2024-04-23 | 28.6 | Électricité | H2d | inférieur à 400m | 270.9 | 10.0 | E | D |
| 2306E0638979L | 2023-02-27 | 31.6 | Électricité | H3 | inférieur à 400m | 115.7 | 4.0 | C | B |
| 2183E0434374X | 2021-10-04 | 24.4 | Électricité | H3 | inférieur à 400m | 186.0 | 5.4 | E | C |
| 2113E0874699U | 2021-12-08 | 54.5 | Électricité | H3 | inférieur à 400m | 31.9 | 3.0 | B | A |
| 2106E0375868S | 2021-09-23 | 38.0 | Électricité | H3 | inférieur à 400m | 67.6 | 6.7 | E | A |
| 2406E3978721C | 2024-11-12 | 35.2 | Électricité | H3 | inférieur à 400m | 72.9 | 2.6 | B | A |
| 2183E0631419O | 2021-10-27 | 60.0 | Électricité | H3 | inférieur à 400m | 93.7 | 2.9 | E | B |

## Petites surfaces (≤ 40 m²) avant et après le 1er juillet 2024

DPE établis avant 2026 (coefficient 2,3), recalculés avec ou sans les seuils petites surfaces :

| Seuils appliqués | Avant le 2024-07-01 | Depuis le 2024-07-01 |
|---|---:|---:|
| Petites surfaces (arrêté 2024) | 99.12 % (147 200 DPE) | 99.65 % (79 601 DPE) |
| Standards | 75.49 % (147 200 DPE) | 77.38 % (79 601 DPE) |

DPE ≤ 40 m² établis depuis le 2026-01-01 (coefficient 1,9) : 99.93 % avec les seuils petites surfaces, 74.02 % avec les seuils standards (41 027 DPE).

| Trimestre | DPE ≤ 40 m² | Seuils petites surfaces | Seuils standards |
|---|---:|---:|---:|
| 2021Q3 | 5 900 | 93.97 % | 73.44 % |
| 2021Q4 | 8 479 | 95.82 % | 75.48 % |
| 2022Q1 | 10 215 | 98.81 % | 75.17 % |
| 2022Q2 | 11 899 | 99.66 % | 74.67 % |
| 2022Q3 | 11 080 | 99.52 % | 74.00 % |
| 2022Q4 | 11 707 | 99.62 % | 76.82 % |
| 2023Q1 | 15 347 | 99.67 % | 75.43 % |
| 2023Q2 | 14 742 | 99.66 % | 73.22 % |
| 2023Q3 | 15 178 | 99.59 % | 74.25 % |
| 2023Q4 | 14 566 | 99.53 % | 76.48 % |
| 2024Q1 | 14 444 | 99.65 % | 79.82 % |
| 2024Q2 | 13 643 | 99.69 % | 75.68 % |
| 2024Q3 | 13 181 | 99.70 % | 78.03 % |
| 2024Q4 | 14 650 | 99.69 % | 77.14 % |
| 2025Q1 | 15 423 | 99.64 % | 78.66 % |
| 2025Q2 | 12 975 | 99.63 % | 76.38 % |
| 2025Q3 | 12 116 | 99.63 % | 76.86 % |
| 2025Q4 | 11 256 | 99.57 % | 76.87 % |

## Effet de la règle d'altitude (> 800 m en H1b, H1c, H2d)

Jointure de `classe_altitude` par `numero_dpe` : 1 224 279 DPE renseignés, 1 297 sans valeur. Répartition : inférieur à 400m : 1 133 218, 400-800m : 51 159, supérieur à 800m : 39 514, <NA> : 1 297, Non affecté : 388.

DPE établis depuis le 2026-01-01 (coefficient 1.9) : concordance 99.37 % sans la règle, 99.98 % avec. DPE concernés par la règle : 4 662 ; à plus de 800 m mais hors zones H1b/H1c/H2d : 871.

| Département | DPE | Concernés | Concordance sans | Concordance avec | Concernés : sans | Concernés : avec |
|---|---:|---:|---:|---:|---:|---:|
| **04** | 5 372 | 1 122 | 95.53 % | 100.00 % | 78.61 % | 100.00 % |
| **05** | 6 170 | 3 495 | 87.44 % | 100.00 % | 77.83 % | 100.00 % |
| 06 | 40 280 | 5 | 99.99 % | 99.99 % | 80.00 % | 100.00 % |
| 13 | 62 556 | 2 | 99.97 % | 99.97 % | 100.00 % | 100.00 % |
| 83 | 35 205 | 7 | 99.98 % | 99.98 % | 100.00 % | 100.00 % |
| **84** | 17 002 | 31 | 99.94 % | 99.99 % | 70.97 % | 100.00 % |

## Coefficient électricité réellement présent dans les données

DPE dont la seule énergie est l'électricité : rapport CEP / CEF par m² (égal au coefficient appliqué, aux arrondis près).

| Période | DPE | 10e centile | Médiane | 90e centile | Part entre 1,85 et 1,95 | Part entre 2,25 et 2,35 |
|---|---:|---:|---:|---:|---:|---:|
| Avant 2026 | 549 768 | 1.899 | 1.906 | 1.924 | 97.89 % | 0.59 % |
| Depuis 2026 | 95 565 | 1.896 | 1.902 | 1.917 | 99.34 % | 0.00 % |
| 2021Q3 | 15 691 | 1.899 | 1.906 | 1.931 | 88.60 % | 6.10 % |
| 2021Q4 | 20 891 | 1.899 | 1.906 | 1.931 | 89.87 % | 7.21 % |
| 2022Q1 | 24 821 | 1.899 | 1.906 | 1.924 | 95.04 % | 3.04 % |
| 2022Q2 | 28 017 | 1.899 | 1.905 | 1.920 | 99.51 % | 0.00 % |
| 2022Q3 | 28 016 | 1.899 | 1.903 | 1.920 | 99.52 % | 0.00 % |
| 2022Q4 | 28 008 | 1.899 | 1.904 | 1.921 | 99.35 % | 0.00 % |
| 2023Q1 | 34 206 | 1.899 | 1.905 | 1.921 | 99.30 % | 0.00 % |
| 2023Q2 | 34 374 | 1.899 | 1.906 | 1.922 | 99.22 % | 0.00 % |
| 2023Q3 | 30 811 | 1.899 | 1.905 | 1.920 | 99.24 % | 0.00 % |
| 2023Q4 | 32 827 | 1.899 | 1.906 | 1.922 | 99.22 % | 0.00 % |
| 2024Q1 | 33 781 | 1.899 | 1.906 | 1.924 | 98.96 % | 0.00 % |
| 2024Q2 | 35 678 | 1.899 | 1.907 | 1.925 | 98.69 % | 0.00 % |
| 2024Q3 | 33 894 | 1.899 | 1.906 | 1.924 | 98.66 % | 0.00 % |
| 2024Q4 | 40 533 | 1.899 | 1.908 | 1.931 | 95.53 % | 0.00 % |
| 2025Q1 | 39 260 | 1.899 | 1.906 | 1.924 | 98.67 % | 0.00 % |
| 2025Q2 | 31 587 | 1.899 | 1.906 | 1.924 | 98.35 % | 0.00 % |
| 2025Q3 | 28 865 | 1.899 | 1.907 | 1.924 | 98.56 % | 0.00 % |
| 2025Q4 | 28 508 | 1.899 | 1.907 | 1.925 | 98.45 % | 0.00 % |
| 2026Q1 | 30 526 | 1.896 | 1.902 | 1.917 | 99.42 % | 0.00 % |
| 2026Q2 | 29 111 | 1.896 | 1.902 | 1.918 | 99.30 % | 0.00 % |
| 2026Q3 | 27 712 | 1.896 | 1.902 | 1.918 | 99.23 % | 0.00 % |
| 2026Q4 | 8 216 | 1.896 | 1.902 | 1.917 | 99.53 % | 0.00 % |

## Effet de la cible d'entraînement (DPE d'avant 2026 ramenés en 1,9)

**Attention** : ce calcul suppose, comme la table datée, que les DPE d'avant 2026 sont publiés en 2,3. La section précédente montre qu'ils sont publiés en 1,9 : ce décalage serait alors une double correction.

Cible = `etiquette_dpe` décalée de (classe recalculée en 1,9 − classe recalculée en 2,3), mêmes seuils.

- DPE : 1 058 991 ; décalages : -3 : 6, -2 : 903, -1 : 332 891, 0 : 725 191
- Étiquettes changées : 51.22 % des chauffages électriques, 4.26 % des autres

| Classe | Officielle | Cible 1,9 |
|---|---:|---:|
| A | 36 267 | 65 646 |
| B | 116 864 | 200 750 |
| C | 451 435 | 444 869 |
| D | 272 568 | 222 649 |
| E | 120 722 | 84 919 |
| F | 41 991 | 28 629 |
| G | 19 144 | 11 529 |

Chauffage électrique — parts par classe (614 713 DPE avant 2026, 109 029 depuis) :

| Classe | Avant 2026, officielle (2,3) | Avant 2026, cible 1,9 | Depuis 2026, officielle (1,9) |
|---|---:|---:|---:|
| A | 5.53 % | 10.11 % | 6.77 % |
| B | 15.57 % | 28.89 % | 17.20 % |
| C | 42.64 % | 40.88 % | 42.79 % |
| D | 21.11 % | 13.40 % | 20.30 % |
| E | 10.15 % | 4.88 % | 8.82 % |
| F | 3.34 % | 1.33 % | 3.11 % |
| G | 1.66 % | 0.51 % | 1.02 % |

Autres chauffages — parts par classe (444 278 DPE avant 2026, 57 556 depuis) :

| Classe | Avant 2026, officielle (2,3) | Avant 2026, cible 1,9 | Depuis 2026, officielle (1,9) |
|---|---:|---:|---:|
| A | 0.51 % | 0.78 % | 0.44 % |
| B | 4.76 % | 5.22 % | 3.77 % |
| C | 42.61 % | 43.56 % | 39.04 % |
| D | 32.14 % | 31.57 % | 35.86 % |
| E | 13.12 % | 12.37 % | 13.72 % |
| F | 4.83 % | 4.61 % | 5.18 % |
| G | 2.02 % | 1.89 % | 1.99 % |
