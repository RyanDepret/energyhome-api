import pandas as pd
import pytest

from app.ml.features_v3 import CHAUFFAGES, PERIODES, encoder
from training.donnees_v3 import entrees_lisibles


def entree(**champs):
    base = {"surface": 50.0, "periode": "1975_1977", "type_batiment": "maison", "chauffage": "gaz_naturel",
            "departement": "13", "zone_climatique": "H3"}
    return pd.DataFrame([{**base, **champs}])


@pytest.mark.parametrize("localisation, attendu", [
    ("zone", ["surface", "periode", "type_batiment", "chauffage", "zone_climatique"]),
    ("departement", ["surface", "periode", "type_batiment", "chauffage", "departement"]),
    ("departement_et_zone", ["surface", "periode", "type_batiment", "chauffage", "departement", "zone_climatique"]),
])
def test_colonnes_selon_localisation(localisation, attendu):
    assert list(encoder(entree(), localisation).columns) == attendu


def test_periode_ordonnee_et_categories_figees():
    X = encoder(entree(periode="apres_2021"), "departement")
    assert X["periode"].iloc[0] == PERIODES.index("apres_2021") == len(PERIODES) - 1
    assert list(X["chauffage"].cat.categories) == CHAUFFAGES
    # Une seule ligne : les catégories restent complètes (même codage qu'à l'entraînement)
    assert X["departement"].cat.codes.iloc[0] == 3


@pytest.mark.parametrize("champ, valeur", [("chauffage", "nucleaire"), ("departement", "75"), ("periode", "1900")])
def test_valeur_inconnue_refusee(champ, valeur):
    with pytest.raises(ValueError):
        encoder(entree(**{champ: valeur}), "departement_et_zone")


def test_regroupements_des_chauffages_inconnus_du_v2():
    df = pd.DataFrame({
        "surface_habitable_logement": [50.0] * 4,
        "periode_construction": ["1948-1974"] * 4,
        "type_batiment": ["maison"] * 4,
        "type_energie_principale_chauffage": ["Bois – Plaquettes forestières", "Butane", "Charbon", "Électricité"],
        "code_departement_ban": ["05", "13", "84", "06"],
    })
    e = entrees_lisibles(df)
    assert e["chauffage"].tolist() == ["bois_plaquettes", "gpl", "charbon", "electricite"]
    assert e["zone_climatique"].tolist() == ["H1c", "H3", "H2d", "H3"]
