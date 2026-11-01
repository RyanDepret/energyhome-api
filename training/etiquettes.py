"""Recalcul de l'étiquette DPE à un coefficient électricité choisi.

L'énergie primaire est corrigée de la part électrique :
    CEP_cible = CEP_dpe − (coef_dpe − coef_cible) × EF_électrique_par_m²
où coef_dpe est le coefficient en vigueur à la date d'établissement du DPE
(app/core/reglementation.py). Les émissions ne changent pas.

Classement (arrêté du 25 mars 2024, annexe 1, § 1.2 — voir app/core/reglementation.py) :
CEP et EGES arrondis à l'entier inférieur, inégalités strictes (classe A si CEP < CEP_a et
EGES < EGES_a…), étiquette = la plus mauvaise des deux classes ; seuils spécifiques
pour les surfaces ≤ 40 m² (interpolation linéaire) et au-dessus de 800 m d'altitude
en zones H1b, H1c, H2d.

Les consommations par énergie (`conso_5_usages_ef_energie_nX`) sont des totaux
annuels en kWh : on les divise par la surface. La surface utilisée est
`surface_habitable_logement` (le jeu ADEME ne publie pas la « surface de référence »).

Cible d'entraînement (`etiquette_cible`) : on garde `etiquette_dpe` et on lui applique
seulement le décalage de classe dû au changement de coefficient, calculé avec ces seuils.
Le coefficient de départ est celui **des données publiées**, mesuré dans les données
(`mesurer_coefficient_publie`) : en novembre 2026, l'ADEME publie tous les DPE en 1,9,
y compris ceux établis avant 2026 (reports/validation_etiquettes.md). La date d'établissement
ne dit donc pas en quel coefficient une ligne est publiée.
"""

import math

import numpy as np
import pandas as pd

from app.core.reglementation import (
    COEFFICIENTS_ELECTRICITE,
    SEUILS_CEP_STANDARD,
    SEUILS_EF_ALTITUDE_GRANDE_SURFACE,
    SEUILS_EGES_STANDARD,
    SURFACE_PETITE_MAX,
    TABLE_PETITES_SURFACES,
    TABLE_PETITES_SURFACES_ALTITUDE,
    ZONES_ALTITUDE,
    coefficient_electricite,
    seuils_etiquette,
)

CLASSES = ["A", "B", "C", "D", "E", "F", "G"]
NIVEAUX = (1, 2, 3)
PREFIXE_ELECTRICITE = "Électricité"
ALTITUDE_SUP_800 = "supérieur à 800m"  # valeur ADEME de `classe_altitude`


def classe_selon_seuils(valeur: float, seuils) -> str:
    """Classe d'un indicateur : arrondi à l'entier inférieur, puis valeur < seuil (strict)."""
    v = math.floor(valeur)
    for classe, seuil in zip(CLASSES, seuils):
        if v < seuil:
            return classe
    return CLASSES[-1]


def pire_classe(*classes: str) -> str:
    return max(classes, key=CLASSES.index)


def _altitude_haute(ligne) -> bool:
    return ligne.get("classe_altitude") == ALTITUDE_SUP_800


def ef_electrique_par_m2(ligne) -> float:
    """Énergie finale électrique (5 usages) par m² d'un DPE."""
    total = 0.0
    for n in NIVEAUX:
        type_energie = ligne.get(f"type_energie_n{n}")
        conso = ligne.get(f"conso_5_usages_ef_energie_n{n}")
        if isinstance(type_energie, str) and type_energie.startswith(PREFIXE_ELECTRICITE) and pd.notna(conso):
            total += float(conso)
    return total / float(ligne["surface_habitable_logement"])


def ep_au_coefficient(ligne, coefficient_cible: float) -> float:
    """Énergie primaire par m² recalculée au coefficient cible."""
    coef_dpe = coefficient_electricite(pd.Timestamp(ligne["date_etablissement_dpe"]).date())
    return float(ligne["conso_5_usages_par_m2_ep"]) - (coef_dpe - coefficient_cible) * ef_electrique_par_m2(ligne)


def recalculer_etiquette(ligne, coefficient_cible: float, petites_surfaces: bool = True) -> str:
    """Étiquette DPE (double seuil) d'une ligne recalculée au coefficient cible."""
    cep, eges = seuils_etiquette(float(ligne["surface_habitable_logement"]), _altitude_haute(ligne),
                                 ligne.get("zone_climatique"), petites_surfaces)
    ep = ep_au_coefficient(ligne, coefficient_cible)
    return pire_classe(classe_selon_seuils(ep, cep),
                       classe_selon_seuils(float(ligne["emission_ges_5_usages_par_m2"]), eges))


# ── Version vectorisée (même règle, pour le million de lignes) ───────────────

def coefficients_dpe(dates: pd.Series) -> np.ndarray:
    """Coefficient en vigueur à chaque date (erreur si une date précède la table)."""
    jours = pd.to_datetime(dates)
    premiere = pd.Timestamp(COEFFICIENTS_ELECTRICITE[0].date_effet)
    if (jours < premiere).any():
        raise ValueError(f"DPE établis avant le {premiere.date().isoformat()} : aucun coefficient défini")
    coef = np.full(len(jours), np.nan)
    for ligne in COEFFICIENTS_ELECTRICITE:
        coef[(jours >= pd.Timestamp(ligne.date_effet)).to_numpy()] = ligne.valeur
    return coef


def ef_electrique_par_m2_lot(df: pd.DataFrame) -> np.ndarray:
    total = np.zeros(len(df))
    for n in NIVEAUX:
        est_elec = df[f"type_energie_n{n}"].astype("string").str.startswith(PREFIXE_ELECTRICITE).fillna(False)
        conso = df[f"conso_5_usages_ef_energie_n{n}"].fillna(0).to_numpy(dtype=float)
        total += np.where(est_elec.to_numpy(dtype=bool), conso, 0.0)
    return total / df["surface_habitable_logement"].to_numpy(dtype=float)


def ep_au_coefficient_lot(df: pd.DataFrame, coefficient_cible: float,
                          coefficient_source: float | None = None) -> np.ndarray:
    """CEP par m² au coefficient cible, depuis le coefficient source (par défaut : table datée)."""
    coef = coefficients_dpe(df["date_etablissement_dpe"]) if coefficient_source is None else coefficient_source
    return df["conso_5_usages_par_m2_ep"].to_numpy(dtype=float) - (coef - coefficient_cible) * ef_electrique_par_m2_lot(df)


def _interp_colonnes(table, surface: np.ndarray) -> np.ndarray:
    """Interpolation linéaire de chaque colonne de la table (bornée à 8 et 40 m²)."""
    t = np.asarray(table, dtype=float)
    return np.column_stack([np.interp(surface, t[:, 0], t[:, j]) for j in range(1, t.shape[1])])


def seuils_lot(df: pd.DataFrame, petites_surfaces: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Seuils CEP et EGES (n × 6) de chaque ligne, même règle que `seuils_etiquette`."""
    n = len(df)
    surface = df["surface_habitable_logement"].to_numpy(dtype=float)
    cep = np.tile(np.asarray(SEUILS_CEP_STANDARD, dtype=float), (n, 1))
    eges = np.tile(np.asarray(SEUILS_EGES_STANDARD, dtype=float), (n, 1))
    if "classe_altitude" in df:
        altitude = ((df["classe_altitude"] == ALTITUDE_SUP_800).fillna(False).to_numpy(dtype=bool)
                    & df["zone_climatique"].isin(ZONES_ALTITUDE).to_numpy(dtype=bool))
    else:
        altitude = np.zeros(n, dtype=bool)

    cep[altitude, 4], eges[altitude, 4], cep[altitude, 5], eges[altitude, 5] = SEUILS_EF_ALTITUDE_GRANDE_SURFACE

    if petites_surfaces:
        petit = surface <= SURFACE_PETITE_MAX
        v = _interp_colonnes(TABLE_PETITES_SURFACES, surface[petit])
        cep[petit], eges[petit] = v[:, 0::2], v[:, 1::2]
        pa = petit & altitude
        va = _interp_colonnes(TABLE_PETITES_SURFACES_ALTITUDE, surface[pa])
        cep[pa, 4], eges[pa, 4], cep[pa, 5], eges[pa, 5] = va.T
    return cep, eges


def _indice_classe(valeurs: np.ndarray, seuils: np.ndarray) -> np.ndarray:
    """Indice de classe (0 = A … 6 = G) : nombre de seuils ≤ valeur arrondie à l'entier inférieur."""
    return (np.floor(valeurs)[:, None] >= seuils).sum(axis=1)


def indices_lot(df: pd.DataFrame, coefficient_cible: float, petites_surfaces: bool = True,
                coefficient_source: float | None = None) -> np.ndarray:
    cep, eges = seuils_lot(df, petites_surfaces)
    ep = ep_au_coefficient_lot(df, coefficient_cible, coefficient_source)
    ges = df["emission_ges_5_usages_par_m2"].to_numpy(dtype=float)
    return np.maximum(_indice_classe(ep, cep), _indice_classe(ges, eges))


def recalculer_lot(df: pd.DataFrame, coefficient_cible: float, petites_surfaces: bool = True) -> pd.Series:
    """Étiquettes recalculées au coefficient cible pour tout un DataFrame."""
    indice = indices_lot(df, coefficient_cible, petites_surfaces)
    return pd.Series(np.asarray(CLASSES)[indice], index=df.index, name="etiquette_recalculee")


# ── Coefficient des données publiées ─────────────────────────────────────────

# Coefficient des données ADEME publiées, mesuré le 2026-11-01 (reports/validation_etiquettes.md)
COEFFICIENT_PUBLIE = 1.9
TOLERANCE_COEFFICIENT = 0.05


class CoefficientInattendu(RuntimeError):
    """Les données ne sont pas publiées au coefficient attendu (ex. republication ADEME en 1,7)."""


def mesurer_coefficient_publie(df: pd.DataFrame) -> dict:
    """Coefficient électricité contenu dans les données : médiane de CEP / CEF par m²
    sur les DPE dont la seule énergie est l'électricité."""
    seul_elec = (df["type_energie_n1"].astype("string").str.startswith(PREFIXE_ELECTRICITE).fillna(False)
                 & df["type_energie_n2"].isna() & df["type_energie_n3"].isna())
    sous = df[seul_elec]
    ratio = (sous["conso_5_usages_par_m2_ep"] / sous["conso_5_usages_par_m2_ef"]).replace([np.inf, -np.inf], np.nan).dropna()
    return {"n": int(ratio.size), "mediane": float(ratio.median()) if ratio.size else float("nan"),
            "p10": float(ratio.quantile(0.1)) if ratio.size else float("nan"),
            "p90": float(ratio.quantile(0.9)) if ratio.size else float("nan")}


def controler_coefficient_publie(df: pd.DataFrame, attendu: float, tolerance: float = TOLERANCE_COEFFICIENT,
                                 n_min: int = 100) -> dict:
    """Vérifie que les données sont publiées au coefficient attendu ; lève CoefficientInattendu sinon.

    À appeler à chaque préparation des données : le jour où l'ADEME republiera la base
    au coefficient 1,7, le pipeline s'arrêtera au lieu d'appliquer une double correction.
    """
    mesure = mesurer_coefficient_publie(df)
    if mesure["n"] < n_min:
        raise CoefficientInattendu(f"Trop peu de DPE tout électriques pour mesurer le coefficient ({mesure['n']})")
    if abs(mesure["mediane"] - attendu) > tolerance:
        raise CoefficientInattendu(
            f"Coefficient mesuré dans les données : {mesure['mediane']:.3f} (attendu {attendu} ± {tolerance}). "
            "La base a peut-être été republiée : mettez à jour COEFFICIENT_PUBLIE avant d'entraîner.")
    return {**mesure, "attendu": attendu, "tolerance": tolerance}


def etiquette_cible(df: pd.DataFrame, coefficient_cible: float, coefficient_source: float) -> pd.Series:
    """`etiquette_dpe` décalée du seul effet du passage du coefficient source au coefficient cible.

    décalage = classe recalculée au coefficient cible − classe des valeurs publiées (mêmes seuils) ;
    résultat borné à A…G. Si cible = source, `etiquette_dpe` est renvoyée telle quelle.
    """
    officiel = df["etiquette_dpe"].astype(str)
    if math.isclose(coefficient_cible, coefficient_source):
        return officiel.rename("etiquette_cible")
    propre = indices_lot(df, coefficient_source, coefficient_source=coefficient_source)
    cible = indices_lot(df, coefficient_cible, coefficient_source=coefficient_source)
    indice = np.clip(officiel.map(CLASSES.index).to_numpy() + cible - propre, 0, len(CLASSES) - 1)
    return pd.Series(np.asarray(CLASSES)[indice], index=df.index, name="etiquette_cible")
