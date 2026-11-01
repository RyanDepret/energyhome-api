# Validation du recalcul des étiquettes

Généré par `training/valider_etiquettes.py` le 2026-11-01T08:07:03+00:00. Seuils appliqués (double seuil, bornes incluses) : énergie [70, 110, 180, 250, 330, 420] kWh/m²·an, GES [6, 11, 30, 50, 70, 100] kgCO₂/m²·an. Aucun seuil spécifique aux petites surfaces n'est appliqué.

## DPE établis depuis le 2026-01-01, recalculés en 1,9

- DPE comparés : 166 585, coefficient 1.9
- **Concordance globale : 91.64 %**

| Tranche de surface | DPE | Concordance |
|---|---:|---:|
| < 40 m² | 40 635 | 74.31 % |
| 40–100 m² | 97 831 | 97.19 % |
| > 100 m² | 28 119 | 97.41 % |

Consommations par énergie dont la somme diffère du total de plus de 1 % : 409 DPE (concordance 99.02 %).

Écart de rang réel − recalculé parmi les désaccords (> 0 : DPE officiel plus mauvais) : -3 : 6, -2 : 305, -1 : 10 817, 1 : 2 794

| Désaccords | Total | DPE officiel meilleur | DPE officiel plus mauvais | Valeur EP ou GES pile sur un seuil |
|---|---:|---:|---:|---:|
| < 40 m² | 10 441 | 10 441 | 0 | 1 028 |
| >= 40 m² | 3 481 | 687 | 2 794 | 2 810 |

| Surface (m²) | DPE | Concordance |
|---|---:|---:|
| [0.0, 10.0) | 315 | 2.22 % |
| [10.0, 15.0) | 896 | 19.20 % |
| [15.0, 20.0) | 5 776 | 47.71 % |
| [20.0, 25.0) | 7 355 | 61.86 % |
| [25.0, 30.0) | 8 299 | 75.41 % |
| [30.0, 35.0) | 9 131 | 87.48 % |
| [35.0, 40.0) | 8 863 | 95.49 % |
| [40.0, 45.0) | 10 443 | 97.20 % |
| [45.0, 50.0) | 9 768 | 97.58 % |
| [50.0, inf) | 105 739 | 97.21 % |

| Trimestre | Concordance < 40 m² | Concordance ≥ 40 m² |
|---|---:|---:|
| 2026Q1 | 74.87 % | 97.11 % |
| 2026Q2 | 74.86 % | 97.44 % |
| 2026Q3 | 73.91 % | 97.07 % |
| 2026Q4 | 71.86 % | 97.48 % |

| Chauffage principal | DPE | Concordance |
|---|---:|---:|
| Électricité | 109 029 | 90.37 % |
| Gaz naturel | 43 792 | 94.51 % |
| Fioul domestique | 6 647 | 93.68 % |
| Bois – Bûches | 2 900 | 97.10 % |
| Réseau de Chauffage urbain | 2 127 | 85.38 % |
| Bois – Granulés (pellets) ou briquettes | 1 115 | 94.35 % |
| GPL | 653 | 92.19 % |
| Propane | 186 | 98.39 % |
| Bois – Plaquettes forestières | 112 | 29.46 % |
| Bois – Plaquettes d’industrie | 10 | 100.00 % |
| Charbon | 8 | 75.00 % |
| Butane | 6 | 100.00 % |

Matrice réel (lignes) / recalculé (colonnes) :

| | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 7 282 | 354 | 0 | 0 | 0 | 0 | 0 |
| **B** | 320 | 19 765 | 833 | 0 | 0 | 0 | 0 |
| **C** | 0 | 1 160 | 63 490 | 4 335 | 130 | 3 | 0 |
| **D** | 0 | 0 | 923 | 39 045 | 2 704 | 93 | 3 |
| **E** | 0 | 0 | 0 | 281 | 15 319 | 1 832 | 82 |
| **F** | 0 | 0 | 0 | 0 | 90 | 5 520 | 759 |
| **G** | 0 | 0 | 0 | 0 | 0 | 20 | 2 242 |

Exemples d'écarts (tirés au hasard, graine 42) :

| N° DPE | Date | Surface | Chauffage | EP DPE | EP recalc. | GES | Classe EP | Classe GES | Réel | Recalculé |
|---|---|---:|---|---:|---:|---:|---|---|---|---|
| 2613E2567093B | 2026-10-07 | 152.6 | Fioul domestique | 139.0 | 139.0 | 30.0 | C | C | D | C |
| 2613E0671144Y | 2026-03-09 | 21.3 | Électricité | 191.0 | 191.0 | 7.0 | D | B | C | D |
| 2613E2596552C | 2026-10-12 | 25.5 | Électricité | 258.0 | 258.0 | 10.0 | E | B | D | E |
| 2606E2503300F | 2026-09-30 | 59.3 | Électricité | 47.0 | 47.0 | 6.0 | A | A | B | A |
| 2683E0509576M | 2026-02-21 | 154.8 | Fioul domestique | 175.0 | 175.0 | 30.0 | C | C | D | C |
| 2613E2173706U | 2026-08-21 | 18.5 | Électricité | 207.0 | 207.0 | 7.0 | D | B | C | D |
| 2684E0846068N | 2026-03-25 | 21.0 | Électricité | 193.0 | 193.0 | 7.0 | D | B | C | D |
| 2613E0406246O | 2026-02-11 | 114.8 | Fioul domestique | 265.0 | 265.0 | 70.0 | E | E | F | E |
| 2613E0319108C | 2026-02-03 | 28.3 | Électricité | 271.0 | 271.0 | 10.0 | E | B | D | E |
| 2613E2063678Y | 2026-08-03 | 27.8 | Électricité | 200.0 | 200.0 | 7.0 | D | B | C | D |
| 2613E2570898K | 2026-10-08 | 22.0 | Électricité | 263.0 | 263.0 | 10.0 | E | B | D | E |
| 2613E2435313P | 2026-09-23 | 40.5 | Gaz naturel | 231.0 | 231.0 | 50.0 | D | D | E | D |
| 2613E1785992S | 2026-07-01 | 59.6 | Électricité | 180.0 | 180.0 | 6.0 | C | A | D | C |
| 2613E0204922I | 2026-01-23 | 50.9 | Gaz naturel | 144.0 | 144.0 | 30.0 | C | C | D | C |
| 2605E1922432C | 2026-07-17 | 30.4 | Électricité | 348.0 | 348.0 | 13.0 | F | C | E | F |

## Contrôle : DPE établis avant 2026, recalculés en 2,3

- DPE comparés : 1 058 991, coefficient 2.3
- **Concordance globale : 92.97 %**

| Tranche de surface | DPE | Concordance |
|---|---:|---:|
| < 40 m² | 223 268 | 75.56 % |
| 40–100 m² | 685 450 | 97.53 % |
| > 100 m² | 150 273 | 98.02 % |

Consommations par énergie dont la somme diffère du total de plus de 1 % : 78 132 DPE (concordance 93.41 %).

Écart de rang réel − recalculé parmi les désaccords (> 0 : DPE officiel plus mauvais) : -5 : 1, -4 : 7, -3 : 64, -2 : 1 688, -1 : 55 969, 1 : 15 354, 2 : 665, 3 : 420, 4 : 175, 5 : 84, 6 : 15

| Désaccords | Total | DPE officiel meilleur | DPE officiel plus mauvais | Valeur EP ou GES pile sur un seuil |
|---|---:|---:|---:|---:|
| < 40 m² | 54 559 | 54 067 | 492 | 5 666 |
| >= 40 m² | 19 883 | 3 662 | 16 221 | 15 030 |

| Surface (m²) | DPE | Concordance |
|---|---:|---:|
| [0.0, 10.0) | 490 | 15.10 % |
| [10.0, 15.0) | 5 183 | 18.64 % |
| [15.0, 20.0) | 27 407 | 47.58 % |
| [20.0, 25.0) | 38 245 | 61.52 % |
| [25.0, 30.0) | 47 478 | 75.29 % |
| [30.0, 35.0) | 51 688 | 87.13 % |
| [35.0, 40.0) | 52 777 | 95.34 % |
| [40.0, 45.0) | 64 078 | 97.99 % |
| [45.0, 50.0) | 69 266 | 97.85 % |
| [50.0, inf) | 702 379 | 97.56 % |

| Trimestre | Concordance < 40 m² | Concordance ≥ 40 m² |
|---|---:|---:|
| 2021Q3 | 71.94 % | 94.92 % |
| 2021Q4 | 74.90 % | 95.72 % |
| 2022Q1 | 74.13 % | 98.29 % |
| 2022Q2 | 73.78 % | 97.98 % |
| 2022Q3 | 73.32 % | 98.60 % |
| 2022Q4 | 76.12 % | 98.31 % |
| 2023Q1 | 74.78 % | 98.54 % |
| 2023Q2 | 72.42 % | 98.11 % |
| 2023Q3 | 73.55 % | 97.68 % |
| 2023Q4 | 76.44 % | 97.58 % |
| 2024Q1 | 78.91 % | 96.97 % |
| 2024Q2 | 75.27 % | 97.53 % |
| 2024Q3 | 77.37 % | 97.72 % |
| 2024Q4 | 78.61 % | 96.72 % |
| 2025Q1 | 78.14 % | 97.71 % |
| 2025Q2 | 75.62 % | 98.16 % |
| 2025Q3 | 75.18 % | 98.19 % |
| 2025Q4 | 76.41 % | 97.42 % |

| Chauffage principal | DPE | Concordance |
|---|---:|---:|
| Électricité | 614 456 | 91.18 % |
| Gaz naturel | 335 650 | 95.53 % |
| Fioul domestique | 43 272 | 94.13 % |
| Réseau de Chauffage urbain | 31 138 | 94.40 % |
| Bois – Bûches | 23 989 | 97.79 % |
| Bois – Granulés (pellets) ou briquettes | 5 185 | 96.89 % |
| GPL | 3 534 | 94.11 % |
| Propane | 1 098 | 97.81 % |
| Bois – Plaquettes forestières | 290 | 95.86 % |
| Électricité d'origine renouvelable utilisée dans le bâtiment | 257 | 99.61 % |
| Charbon | 51 | 90.20 % |
| Butane | 36 | 100.00 % |
| Bois – Plaquettes d’industrie | 35 | 77.14 % |

Matrice réel (lignes) / recalculé (colonnes) :

| | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 35 238 | 1 026 | 3 | 0 | 0 | 0 | 0 |
| **B** | 1 260 | 111 738 | 3 865 | 0 | 0 | 0 | 1 |
| **C** | 253 | 5 612 | 419 439 | 25 152 | 949 | 23 | 7 |
| **D** | 193 | 274 | 6 180 | 252 722 | 12 747 | 411 | 41 |
| **E** | 97 | 159 | 123 | 1 710 | 108 959 | 9 349 | 325 |
| **F** | 42 | 56 | 55 | 12 | 481 | 37 515 | 3 830 |
| **G** | 15 | 42 | 22 | 13 | 3 | 111 | 18 938 |

Exemples d'écarts (tirés au hasard, graine 42) :

| N° DPE | Date | Surface | Chauffage | EP DPE | EP recalc. | GES | Classe EP | Classe GES | Réel | Recalculé |
|---|---|---:|---|---:|---:|---:|---|---|---|---|
| 2206E0150335K | 2022-01-25 | 23.0 | Électricité | 202.4 | 202.4 | 7.4 | D | B | C | D |
| 2383E3368221G | 2023-10-07 | 32.6 | Électricité | 185.4 | 185.4 | 7.0 | D | B | C | D |
| 2584E2143461F | 2025-06-30 | 14.7 | Électricité | 257.1 | 257.1 | 9.0 | E | B | C | E |
| 2313E4239077A | 2023-12-10 | 77.0 | Gaz naturel | 149.7 | 149.7 | 30.0 | C | C | D | C |
| 2506E3933127N | 2025-12-16 | 32.6 | Gaz naturel | 233.3 | 233.3 | 50.8 | D | E | D | E |
| 2306E0009034U | 2023-01-03 | 20.8 | Électricité | 216.4 | 216.4 | 8.0 | D | B | C | D |
| 2583E0206962L | 2025-01-21 | 20.6 | Électricité | 226.9 | 226.9 | 8.0 | D | B | C | D |
| 2484E4434584H | 2024-12-13 | 65.0 | Gaz naturel | 138.3 | 138.3 | 30.0 | C | C | D | C |
| 2284E2255051A | 2022-09-30 | 154.6 | Gaz naturel | 176.3 | 176.3 | 30.0 | C | C | D | C |
| 2383E0116702V | 2023-01-13 | 89.0 | Gaz naturel | 240.1 | 240.1 | 50.0 | D | D | E | D |
| 2283E2426918G | 2022-09-30 | 15.7 | Gaz naturel | 183.8 | 183.8 | 35.0 | D | D | C | D |
| 2104E0631400U | 2021-11-04 | 64.0 | Électricité | 81.8 | 81.8 | 2.6 | B | A | G | B |
| 2406E3918200J | 2024-11-06 | 18.5 | Électricité | 219.5 | 219.5 | 8.0 | D | B | C | D |
| 2105E0291998X | 2021-09-09 | 154.8 | Électricité | 327.3 | 327.3 | 103.0 | E | G | F | G |
| 2283E2673990A | 2022-11-11 | 26.8 | Électricité | 111.4 | 111.4 | 3.0 | C | A | B | C |
