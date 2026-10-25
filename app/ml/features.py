import pandas as pd

from app.schemas.predict import (
    CHAUFFAGE_LABELS,
    PERIODE_LABELS,
    TYPE_BATIMENT_LABELS,
    Chauffage,
    Periode,
    TypeBatiment,
)

# Préfixes des colonnes One-Hot produites par pd.get_dummies à l'entraînement
CATEGORICAL_PREFIXES = {
    "periode": "periode_construction_",
    "type_batiment": "type_batiment_",
    "chauffage": "type_energie_principale_chauffage_",
    "zone_climatique": "zone_climatique_",
}
SURFACE_COLUMN = "surface_habitable_logement"

# Dernière année incluse de chaque période, dans l'ordre chronologique
_PERIODE_BORNES: list[tuple[int, Periode]] = [
    (1947, Periode.AVANT_1948),
    (1974, Periode.P_1948_1974),
    (1977, Periode.P_1975_1977),
    (1982, Periode.P_1978_1982),
    (1988, Periode.P_1983_1988),
    (2000, Periode.P_1989_2000),
    (2005, Periode.P_2001_2005),
    (2012, Periode.P_2006_2012),
    (2021, Periode.P_2013_2021),
]


class FeatureError(ValueError):
    """Une colonne qu'on veut activer n'existe pas dans le modèle."""


def annee_vers_periode(annee: int) -> Periode:
    """Convertit une année de construction en période ADEME du modèle (fonction unique)."""
    for derniere_annee, periode in _PERIODE_BORNES:
        if annee <= derniere_annee:
            return periode
    return Periode.APRES_2021


def categorical_columns(
    periode: Periode, type_batiment: TypeBatiment, chauffage: Chauffage, zone_climatique: str
) -> dict[str, str]:
    """Nom de la colonne One-Hot à activer pour chaque variable catégorielle."""
    return {
        "periode": CATEGORICAL_PREFIXES["periode"] + PERIODE_LABELS[periode],
        "type_batiment": CATEGORICAL_PREFIXES["type_batiment"] + TYPE_BATIMENT_LABELS[type_batiment],
        "chauffage": CATEGORICAL_PREFIXES["chauffage"] + CHAUFFAGE_LABELS[chauffage],
        "zone_climatique": CATEGORICAL_PREFIXES["zone_climatique"] + zone_climatique,
    }


def build_features(
    surface: float,
    periode: Periode,
    type_batiment: TypeBatiment,
    chauffage: Chauffage,
    zone_climatique: str,
    colonnes_modele: list[str],
) -> pd.DataFrame:
    """Construit le vecteur de features (une ligne, colonnes dans l'ordre du modèle).

    Lève FeatureError si une colonne à activer n'existe pas : aucune valeur
    n'est plus jamais ignorée en silence.
    """
    if SURFACE_COLUMN not in colonnes_modele:
        raise FeatureError(f"Colonne absente du modèle : {SURFACE_COLUMN!r}")

    features = {col: 0 for col in colonnes_modele}
    features[SURFACE_COLUMN] = surface

    for variable, colonne in categorical_columns(periode, type_batiment, chauffage, zone_climatique).items():
        if colonne not in features:
            raise FeatureError(f"Colonne absente du modèle pour {variable} : {colonne!r}")
        features[colonne] = 1

    return pd.DataFrame([features], columns=colonnes_modele)
