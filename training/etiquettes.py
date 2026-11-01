"""Recalcul de l'étiquette DPE à un coefficient électricité choisi.

L'énergie primaire est corrigée de la part électrique :
    EP_cible = EP_dpe − (coef_dpe − coef_cible) × EF_électrique_par_m²
où coef_dpe est le coefficient en vigueur à la date d'établissement du DPE
(app/core/reglementation.py). Le GES ne change pas. L'étiquette est la plus
mauvaise des deux classes énergie et GES (double seuil).

Les consommations par énergie (`conso_5_usages_ef_energie_nX`) sont des totaux
annuels en kWh : on les divise par la surface habitable.
"""

import numpy as np
import pandas as pd

from app.core.reglementation import COEFFICIENTS_ELECTRICITE, coefficient_electricite

CLASSES = ["A", "B", "C", "D", "E", "F", "G"]
# Bornes supérieures incluses des classes A à F ; G au-delà
SEUILS_ENERGIE = [70, 110, 180, 250, 330, 420]  # kWh/m²·an
SEUILS_GES = [6, 11, 30, 50, 70, 100]  # kgCO2/m²·an

NIVEAUX = (1, 2, 3)
PREFIXE_ELECTRICITE = "Électricité"


def classe_selon_seuils(valeur: float, seuils: list[float]) -> str:
    """Classe correspondant à une valeur (borne supérieure incluse)."""
    for classe, seuil in zip(CLASSES, seuils):
        if valeur <= seuil:
            return classe
    return CLASSES[-1]


def pire_classe(*classes: str) -> str:
    return max(classes, key=CLASSES.index)


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


def recalculer_etiquette(ligne, coefficient_cible: float) -> str:
    """Étiquette DPE (double seuil) d'une ligne recalculée au coefficient cible."""
    ep = ep_au_coefficient(ligne, coefficient_cible)
    classe_energie = classe_selon_seuils(ep, SEUILS_ENERGIE)
    classe_ges = classe_selon_seuils(float(ligne["emission_ges_5_usages_par_m2"]), SEUILS_GES)
    return pire_classe(classe_energie, classe_ges)


# ── Version vectorisée (même formule, pour le million de lignes) ─────────────

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


def _classes_lot(valeurs: np.ndarray, seuils: list[float]) -> np.ndarray:
    """Indice de classe (0 = A … 6 = G), borne supérieure incluse."""
    return np.searchsorted(np.asarray(seuils, dtype=float), valeurs, side="left")


def ep_au_coefficient_lot(df: pd.DataFrame, coefficient_cible: float) -> np.ndarray:
    coef = coefficients_dpe(df["date_etablissement_dpe"])
    return df["conso_5_usages_par_m2_ep"].to_numpy(dtype=float) - (coef - coefficient_cible) * ef_electrique_par_m2_lot(df)


def recalculer_lot(df: pd.DataFrame, coefficient_cible: float) -> pd.Series:
    """Étiquettes recalculées au coefficient cible pour tout un DataFrame."""
    ep = ep_au_coefficient_lot(df, coefficient_cible)
    ges = df["emission_ges_5_usages_par_m2"].to_numpy(dtype=float)
    indice = np.maximum(_classes_lot(ep, SEUILS_ENERGIE), _classes_lot(ges, SEUILS_GES))
    return pd.Series(np.asarray(CLASSES)[indice], index=df.index, name="etiquette_recalculee")
