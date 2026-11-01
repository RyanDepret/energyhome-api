"""Variables d'entrée du modèle v3, partagées entre l'entraînement et l'API.

Uniquement ce que l'utilisateur saisit : surface, période de construction, type de
bâtiment, énergie de chauffage, et la localisation dérivée du code postal
(département, et zone climatique déduite du département comme en production).
Les catégories sont figées ici : un même logement donne exactement le même vecteur
à l'entraînement et dans /predict.
"""

import pandas as pd

from app.schemas.predict import Chauffage, Periode, TypeBatiment

# Ordre chronologique des périodes : codé comme un entier (l'ordre a un sens)
PERIODES = [p.value for p in Periode]
TYPES_BATIMENT = [t.value for t in TypeBatiment]
# Chauffages de l'API + « charbon », connu du modèle mais refusé par /predict
CHAUFFAGE_CHARBON = "charbon"
CHAUFFAGES = [c.value for c in Chauffage] + [CHAUFFAGE_CHARBON]
DEPARTEMENTS = ["04", "05", "06", "13", "83", "84"]
ZONES = ["H1c", "H2d", "H3"]

# Libellés ADEME sans équivalent direct dans l'API, et leur regroupement justifié :
# - plaquettes forestières et plaquettes d'industrie sont le même combustible (bois déchiqueté) ;
# - le butane est un gaz de pétrole liquéfié (GPL).
REGROUPEMENTS_CHAUFFAGE_ADEME = {
    "Bois – Plaquettes forestières": Chauffage.BOIS_PLAQUETTES.value,
    "Butane": Chauffage.GPL.value,
    "Charbon": CHAUFFAGE_CHARBON,
}

# Variables possibles ; LOCALISATIONS dit lesquelles décrivent le lieu
VARIABLES_BASE = ["surface", "periode", "type_batiment", "chauffage"]
LOCALISATIONS = {
    "zone": ["zone_climatique"],
    "departement": ["departement"],
    "departement_et_zone": ["departement", "zone_climatique"],
}
CATEGORIELLES = ["type_batiment", "chauffage", "departement", "zone_climatique"]

LIBELLES_CRITERES = {
    "surface": "Surface",
    "periode": "Période de construction",
    "type_batiment": "Type de bâtiment",
    "chauffage": "Énergie de chauffage",
    "departement": "Département",
    "zone_climatique": "Zone climatique",
}


def colonnes(localisation: str) -> list[str]:
    return VARIABLES_BASE + LOCALISATIONS[localisation]


def encoder(entrees: pd.DataFrame, localisation: str) -> pd.DataFrame:
    """Entrées lisibles → matrice du modèle (catégories figées, erreur si valeur inconnue).

    `entrees` contient : surface, periode (valeur de Periode), type_batiment, chauffage,
    departement, zone_climatique.
    """
    X = pd.DataFrame(index=entrees.index)
    X["surface"] = entrees["surface"].astype(float)
    X["periode"] = _codes(entrees["periode"], PERIODES, "periode")
    categories = {"type_batiment": TYPES_BATIMENT, "chauffage": CHAUFFAGES,
                  "departement": DEPARTEMENTS, "zone_climatique": ZONES}
    for col in LOCALISATIONS[localisation] + ["type_batiment", "chauffage"]:
        valeurs = entrees[col].astype(str)
        inconnues = set(valeurs.unique()) - set(categories[col])
        if inconnues:
            raise ValueError(f"Valeurs inconnues pour {col} : {sorted(inconnues)}")
        X[col] = pd.Categorical(valeurs, categories=categories[col])
    return X[colonnes(localisation)]


def _codes(serie: pd.Series, ordre: list[str], nom: str) -> pd.Series:
    rang = {v: i for i, v in enumerate(ordre)}
    codes = serie.astype(str).map(rang)
    if codes.isna().any():
        raise ValueError(f"Valeurs inconnues pour {nom} : {sorted(set(serie[codes.isna()].astype(str)))}")
    return codes.astype(int)
