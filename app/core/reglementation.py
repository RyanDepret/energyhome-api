"""Règles réglementaires datées utilisées par le modèle et le site.

Chaque valeur est rattachée à sa date d'effet et à sa source : la valeur en
vigueur se lit dans la table, jamais en dur dans le code.
"""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Coefficient:
    """Coefficient de conversion de l'électricité en énergie primaire."""

    date_effet: date
    valeur: float
    source: str


# Triée par date d'effet croissante
COEFFICIENTS_ELECTRICITE: tuple[Coefficient, ...] = (
    Coefficient(date(2021, 7, 1), 2.3, "méthode DPE 2021"),
    Coefficient(date(2026, 1, 1), 1.9, "arrêté du 13 août 2025"),
    Coefficient(date(2027, 1, 1), 1.7, "arrêté du 19 août 2026 (Légifrance JORFTEXT000054747079)"),
)


def coefficient_en_vigueur(jour: date | datetime) -> Coefficient:
    """Ligne de la table applicable au jour donné.

    Lève ValueError avant l'entrée en vigueur de la méthode DPE 2021.
    """
    if isinstance(jour, datetime):
        jour = jour.date()
    applicable = None
    for ligne in COEFFICIENTS_ELECTRICITE:
        if jour >= ligne.date_effet:
            applicable = ligne
    if applicable is None:
        premiere = COEFFICIENTS_ELECTRICITE[0].date_effet
        raise ValueError(f"Aucun coefficient électricité défini avant le {premiere.isoformat()} (date : {jour.isoformat()})")
    return applicable


def coefficient_electricite(jour: date | datetime) -> float:
    """Coefficient électricité en vigueur au jour donné."""
    return coefficient_en_vigueur(jour).valeur


# ── Seuils des étiquettes DPE ────────────────────────────────────────────────
# Source : arrêté du 25 mars 2024 modifiant les seuils des étiquettes du DPE pour les
# logements de petites surfaces (NOR TREL2330369A), JORF du 20 avril 2024, texte 15 sur 101,
# annexe 1 (remplace l'annexe 5 de l'arrêté du 31 mars 2021), en vigueur le 1er juillet 2024.
# Légifrance : https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000049446339
# Tableaux recopiés de la copie du Journal officiel (pages 5 à 7), sans reconstitution.
#
# Règle (§ 1.2) : CEP et EGES par m² de surface de référence, arrondis à l'entier inférieur ;
# classe A si CEP < CEP_a et EGES < EGES_a, … ; G si CEP ≥ CEP_f ou EGES ≥ EGES_f
# (inégalités strictes : la classe est la plus mauvaise des deux indicateurs).

SOURCE_SEUILS = (
    "Arrêté du 25 mars 2024 (NOR TREL2330369A), JORF du 20 avril 2024, texte 15, annexe 1 ; "
    "Légifrance JORFARTI000049446339"
)
DATE_SEUILS_PETITES_SURFACES = date(2024, 7, 1)
SURFACE_PETITE_MAX = 40  # m² : tableau spécifique si surface de référence ≤ 40 (§ 1.2.2)
ALTITUDE_SEUIL_M = 800
ZONES_ALTITUDE = ("H1b", "H1c", "H2d")  # § 1.2.1.2 et § 1.2.2.2

# § 1.2.1.1 — surface > 40 m², altitude < 800 m : (CEP_a..CEP_f), (EGES_a..EGES_f)
SEUILS_CEP_STANDARD = (70, 110, 180, 250, 330, 420)
SEUILS_EGES_STANDARD = (6, 11, 30, 50, 70, 100)

# § 1.2.1.2 — surface > 40 m², altitude > 800 m en H1b, H1c, H2d : CEP_e, EGES_e, CEP_f, EGES_f
SEUILS_EF_ALTITUDE_GRANDE_SURFACE = (390, 80, 500, 110)

# § 1.2.2.1 — surface ≤ 40 m², altitude < 800 m. Ligne « 8 » = « ≤ 8 ».
# Colonnes : S_REF, CEP_a, EGES_a, CEP_b, EGES_b, CEP_c, EGES_c, CEP_d, EGES_d, CEP_e, EGES_e, CEP_f, EGES_f
_TABLE_PETITES_SURFACES = """
8 146 11 186 16 386 44 505 68 622 90 739 122
9 134 11 174 16 355 42 464 65 574 87 685 118
10 124 10 164 15 329 40 428 62 533 84 640 115
11 117 10 157 15 311 39 403 61 503 82 607 113
12 112 9 152 14 296 38 381 59 478 81 578 111
13 108 9 148 14 283 37 363 58 456 79 554 110
14 104 9 144 14 273 37 348 58 437 78 532 108
15 100 8 140 13 263 36 333 56 421 76 514 107
16 97 8 137 13 255 35 325 55 412 76 504 106
17 95 8 135 13 248 35 318 55 404 75 496 105
18 92 8 132 13 241 34 311 54 397 75 489 105
19 90 8 130 13 235 34 305 54 390 74 482 105
20 88 8 128 13 230 34 300 54 385 74 476 104
21 87 8 127 13 225 33 295 53 380 74 471 104
22 85 7 125 12 221 33 291 53 375 73 466 103
23 84 7 124 12 217 33 287 53 371 73 462 103
24 82 7 122 12 214 33 284 53 367 73 458 103
25 81 7 121 12 210 32 280 52 363 73 454 103
26 80 7 120 12 207 32 277 52 360 72 451 103
27 79 7 119 12 204 32 274 52 357 72 447 102
28 78 7 118 12 202 32 272 52 354 72 444 102
29 77 7 117 12 199 32 269 52 351 72 442 102
30 76 7 116 12 197 32 267 52 349 72 439 102
31 76 7 116 12 195 31 265 51 346 72 437 102
32 75 7 115 12 193 31 263 51 344 71 434 101
33 74 7 114 12 191 31 261 51 342 71 432 101
34 74 7 114 12 189 31 259 51 340 71 430 101
35 73 7 113 12 188 31 258 51 338 71 428 101
36 72 7 112 12 186 31 256 51 337 71 427 101
37 72 7 112 12 185 31 255 51 335 71 425 101
38 71 7 111 12 183 31 253 51 333 71 423 101
39 71 7 111 12 182 31 252 51 332 71 422 101
40 70 6 110 11 180 30 250 50 330 70 420 100
"""

# § 1.2.2.2 — surface ≤ 40 m², altitude > 800 m en H1b, H1c, H2d. Ligne « 8 » = « ≤ 8 ».
# Colonnes : S_REF, CEP_e, EGES_e, CEP_f, EGES_f
_TABLE_PETITES_SURFACES_ALTITUDE = """
8 682 100 819 132
9 634 97 765 128
10 593 94 720 125
11 563 92 687 123
12 538 91 658 121
13 516 89 634 120
14 497 88 612 118
15 481 86 594 117
16 472 86 584 116
17 464 85 576 115
18 457 85 569 115
19 450 84 562 115
20 445 84 556 114
21 440 84 551 114
22 435 83 546 113
23 431 83 542 113
24 427 83 538 113
25 423 83 534 113
26 420 82 531 113
27 417 82 527 112
28 414 82 524 112
29 411 82 522 112
30 409 82 519 112
31 406 82 517 112
32 404 81 514 111
33 402 81 512 111
34 400 81 510 111
35 398 81 508 111
36 397 81 507 111
37 395 81 505 111
38 393 81 503 111
39 392 81 502 111
40 390 80 500 110
"""


def _lire_table(texte: str) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(v) for v in ligne.split()) for ligne in texte.strip().splitlines())


TABLE_PETITES_SURFACES = _lire_table(_TABLE_PETITES_SURFACES)
TABLE_PETITES_SURFACES_ALTITUDE = _lire_table(_TABLE_PETITES_SURFACES_ALTITUDE)


def _interpoler(table, surface: float) -> list[float]:
    """Valeurs de la table à une surface donnée : ≤ 8 → ligne 8, interpolation linéaire entre lignes."""
    surfaces = [ligne[0] for ligne in table]
    s = min(max(surface, surfaces[0]), surfaces[-1])
    for (s0, *v0), (s1, *v1) in zip(table, table[1:]):
        if s0 <= s <= s1:
            t = (s - s0) / (s1 - s0)
            return [a + t * (b - a) for a, b in zip(v0, v1)]
    raise AssertionError("surface hors table")  # impossible après le bornage


def seuils_etiquette(surface: float, altitude_sup_800: bool = False, zone_climatique: str | None = None,
                     petites_surfaces: bool = True) -> tuple[list[float], list[float]]:
    """Seuils (CEP_a..CEP_f) et (EGES_a..EGES_f) applicables à un logement.

    `petites_surfaces=False` applique les seuils standards quelle que soit la surface
    (règle d'avant le 1er juillet 2024, pour comparaison).
    """
    altitude = altitude_sup_800 and zone_climatique in ZONES_ALTITUDE
    if petites_surfaces and surface <= SURFACE_PETITE_MAX:
        v = _interpoler(TABLE_PETITES_SURFACES, surface)
        cep, eges = v[0::2], v[1::2]
        if altitude:
            cep[4], eges[4], cep[5], eges[5] = _interpoler(TABLE_PETITES_SURFACES_ALTITUDE, surface)
    else:
        cep, eges = list(SEUILS_CEP_STANDARD), list(SEUILS_EGES_STANDARD)
        if altitude:
            cep[4], eges[4], cep[5], eges[5] = SEUILS_EF_ALTITUDE_GRANDE_SURFACE
    return cep, eges
