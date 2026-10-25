from datetime import date

import pytest

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
