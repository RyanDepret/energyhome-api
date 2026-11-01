from datetime import date

import pytest

from app.api.predict import artefact_v3
from app.core.config import settings

LOGEMENT = {
    "surface": 80,
    "type_batiment": "maison",
    "chauffage": "gaz_naturel",
    "code_postal": "13001",
}


def post_predict(client, **champs):
    return client.post("/predict", json={**LOGEMENT, **champs})


def test_predict_avec_periode(client):
    reponse = post_predict(client, periode="1975_1977")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert list(corps["probabilites"]) == ["A", "B", "C", "D", "E", "F", "G"]
    assert all(isinstance(p, float) for p in corps["probabilites"].values())
    assert sum(corps["probabilites"].values()) == pytest.approx(1.0)
    assert corps["classe"] == max(corps["probabilites"], key=corps["probabilites"].get)
    assert corps["model_version"] == settings.model_version
    assert corps["entree"]["periode"] == "1975_1977"
    assert corps["entree"]["zone_climatique"] == "H3"


def test_predict_v3_renvoie_des_importances(client):
    corps = post_predict(client, periode="1975_1977").json()
    assert corps["model_version"].startswith("v3")
    importances = corps["importances"]
    criteres = {i["critere"] for i in importances}
    assert criteres == {"Surface", "Période de construction", "Type de bâtiment", "Énergie de chauffage", "Département"}
    assert all(0 <= i["poids"] <= 1 for i in importances)
    assert sum(i["poids"] for i in importances) == pytest.approx(1.0)
    assert [i["poids"] for i in importances] == sorted((i["poids"] for i in importances), reverse=True)
    valeurs = {i["critere"]: i["valeur"] for i in importances}
    assert valeurs["Surface"] == 80 and valeurs["Département"] == "13" and valeurs["Énergie de chauffage"] == "gaz_naturel"


@pytest.mark.parametrize("chauffage", ["bois_plaquettes", "gpl", "electricite_renouvelable", "reseau_chaleur"])
def test_predict_v3_tous_les_chauffages_de_l_api(client, chauffage):
    assert post_predict(client, periode="1989_2000", chauffage=chauffage).status_code == 200


def test_retour_au_v2_par_la_config(client, monkeypatch):
    monkeypatch.setattr(settings, "model_version", "v2-rf-2025")
    corps = post_predict(client, periode="1975_1977").json()
    assert corps["model_version"] == "v2-rf-2025"
    assert corps["importances"] == []
    assert sum(corps["probabilites"].values()) == pytest.approx(1.0)


def test_version_incoherente_refusee(client, monkeypatch):
    monkeypatch.setattr(settings, "model_version", "v3-autre")
    with pytest.raises(RuntimeError, match="v3-autre"):
        artefact_v3()
    # Côté client, le gestionnaire global transforme l'erreur en 500 (au lieu de servir le mauvais modèle)
    reponse = post_predict(client, periode="1975_1977")
    assert reponse.status_code == 500
    assert reponse.json()["code"] == "erreur_interne"


def test_predict_avec_annee(client):
    reponse = post_predict(client, annee_construction=1998)
    assert reponse.status_code == 200
    entree = reponse.json()["entree"]
    assert entree["periode"] == "1989_2000"
    assert entree["annee_construction"] == 1998


def test_1976_et_1998_donnent_des_probabilites_differentes(client):
    p1976 = post_predict(client, annee_construction=1976).json()["probabilites"]
    p1998 = post_predict(client, annee_construction=1998).json()["probabilites"]
    assert p1976 != p1998


@pytest.mark.parametrize(
    "champs",
    [
        {"periode": "1975_1977", "chauffage": "charbon"},
        {"periode": "1975_1977", "surface": 8},
        {"periode": "1975_1977", "surface": 1001},
        {"periode": "1975_1977", "code_postal": "75001"},
        {"periode": "1975_1977", "code_postal": "1300"},
        {"periode": "1975_1977", "code_postal": "13A01"},
        {"periode": "1975_1977", "type_batiment": "chateau"},
        {"periode": "1975-2000"},
        {},
        {"periode": "1975_1977", "annee_construction": 1976},
        {"annee_construction": 1799},
        {"annee_construction": date.today().year + 1},
    ],
)
def test_predict_entrees_invalides_422(client, champs):
    assert post_predict(client, **champs).status_code == 422


def test_message_clair_hors_paca(client):
    detail = post_predict(client, periode="1975_1977", code_postal="75001").json()["detail"]
    assert "PACA" in detail[0]["msg"]
