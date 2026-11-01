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
